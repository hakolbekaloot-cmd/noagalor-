"""
rss_probe.py — memory probing & release utilities.

Used by the web panel to surface a memory-usage banner and offer a manual
restart when usage approaches Render's 512MB limit. Also exposes
release_memory() so request handlers that allocate large buffers (Pillow,
googleapiclient response bodies) can return memory to the OS instead of
letting it sit in glibc's heap until the worker is recycled.
"""

import gc
import logging
import os

logger = logging.getLogger("rss-probe")

# Cache libc lookup so we don't repeat ctypes.CDLL on every release_memory()
# call. If loading fails once it will always fail in this process; remembering
# that lets us short-circuit cheaply.
_libc_cache: "object | bool | None" = None


def get_rss_mb() -> float | None:
    """Return current RSS in MB from /proc/self/status, or None on failure."""
    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    # Format: "VmRSS:    12345 kB"
                    parts = line.split()
                    if len(parts) >= 2:
                        return int(parts[1]) / 1024.0
    except (OSError, ValueError):
        return None
    return None


def get_cgroup_memory() -> tuple[int, int] | None:
    """
    Return (used_bytes, limit_bytes) from cgroup, or None when no usable
    limit is configured.

    Tries cgroup v2 first (/sys/fs/cgroup/memory.{current,max}), falling back
    to v1 (memory.usage_in_bytes / memory.limit_in_bytes). When the limit is
    "max" or an unrealistically large sentinel value we return None so the
    caller can fall back to RSS + an env-configured limit.
    """
    # Render uses cgroup v2 — try that first.
    try:
        with open("/sys/fs/cgroup/memory.current", "r") as f:
            used = int(f.read().strip())
        with open("/sys/fs/cgroup/memory.max", "r") as f:
            raw_limit = f.read().strip()
        if raw_limit == "max":
            return None
        limit = int(raw_limit)
        # Some hosts report a sentinel like 9223372036854771712; treat huge
        # values as "no real limit" so we fall back to MEMORY_LIMIT_MB.
        if limit <= 0 or limit > (1 << 50):
            return None
        return used, limit
    except (OSError, ValueError):
        pass

    # cgroup v1 fallback.
    try:
        with open("/sys/fs/cgroup/memory/memory.usage_in_bytes", "r") as f:
            used = int(f.read().strip())
        with open("/sys/fs/cgroup/memory/memory.limit_in_bytes", "r") as f:
            limit = int(f.read().strip())
        if limit <= 0 or limit > (1 << 50):
            return None
        return used, limit
    except (OSError, ValueError):
        return None


def release_memory() -> None:
    """
    Run gc.collect() + libc.malloc_trim(0) to return freed memory to the OS.

    Glibc holds onto freed allocations in its heap by default, which causes
    RSS to drift upward even after Python objects are collected. malloc_trim
    forces glibc to release those back to the kernel; combined with
    MALLOC_TRIM_THRESHOLD_ in the Dockerfile this keeps the worker comfortably
    under Render's 512MB limit between max-requests recycles.
    """
    global _libc_cache

    try:
        gc.collect()
    except Exception as e:
        logger.debug(f"gc.collect failed: {e}")

    if _libc_cache is False:
        return

    if _libc_cache is None:
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim.argtypes = [ctypes.c_size_t]
            libc.malloc_trim.restype = ctypes.c_int
            _libc_cache = libc
        except Exception as e:
            # Broad catch on purpose: this runs in a finally block from Flask
            # handlers, so any propagated error would mask the original response
            # with a 500. Narrower catches also miss ImportError on minimal
            # images and would re-attempt loading on every call.
            logger.debug(f"libc.malloc_trim unavailable: {e}")
            _libc_cache = False
            return

    try:
        _libc_cache.malloc_trim(0)
    except Exception as e:
        logger.debug(f"malloc_trim failed: {e}")
