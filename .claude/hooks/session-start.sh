#!/bin/bash
#
# SessionStart hook for Claude Code on the web.
#
# Installs Python dependencies so tests can run inside the cloud session
# without manual setup. Test env vars are handled by conftest.py, so no
# extra exports are needed here.
#
set -euo pipefail

# Only run inside Claude Code on the web; no-op for local sessions.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# --ignore-installed avoids "Cannot uninstall <pkg>, RECORD file not found"
# errors when a transitive dep was previously installed via the system
# package manager. --root-user-action=ignore silences the root warning
# inside the container.
PIP_FLAGS=(--no-input --disable-pip-version-check --root-user-action=ignore --ignore-installed)

echo "[session-start] Installing project dependencies from requirements.txt..."
pip install "${PIP_FLAGS[@]}" -r requirements.txt

echo "[session-start] Installing pytest (test runner, not in requirements.txt)..."
pip install "${PIP_FLAGS[@]}" pytest

# Sanity check: confirm a few critical imports resolve.
echo "[session-start] Verifying installation..."
python - <<'PY'
import importlib, sys
for mod in ("googleapiclient.discovery", "google.oauth2.service_account",
            "cloudinary", "flask", "PIL", "pytest"):
    importlib.import_module(mod)
print("[session-start] All critical imports OK")
PY

echo "[session-start] Done."
