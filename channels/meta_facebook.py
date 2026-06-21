"""
meta_facebook.py — Facebook Page channel adapter.

Wraps the existing meta_publish.py functions behind the BaseChannel interface.
"""

from __future__ import annotations

import logging

from channels.base import BaseChannel, PublishResult
from config_constants import COL_CAPTION_FB, COL_HASHTAGS

logger = logging.getLogger(__name__)


class FacebookChannel(BaseChannel):
    CHANNEL_ID = "FB"
    CHANNEL_NAME = "Facebook"
    SUPPORTED_POST_TYPES = ("FEED", "REELS")
    SUPPORTED_MEDIA_TYPES = ("image", "video", "none")
    CAPTION_COLUMN = COL_CAPTION_FB

    def validate(self, post_data: dict) -> list[str]:
        errors = []
        caption = self.get_caption(post_data)
        # Text-only posts require a caption; media posts also require a caption
        if not caption:
            errors.append("Missing caption for Facebook")
        return errors

    def publish(self, post_data: dict) -> PublishResult:
        from config import FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN

        if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
            return self._make_result(
                success=False, error_code="missing_credentials",
                error_message="Facebook credentials not configured (FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN)",
            )

        from meta_publish import fb_publish_feed, fb_publish_text_only

        caption = self.get_caption(post_data)
        # For FB, hashtags are appended to the caption
        hashtags = (post_data.get(COL_HASHTAGS) or "").strip()
        if hashtags:
            caption = f"{caption}\n\n{hashtags}" if caption else hashtags
        cloud_urls: list[str] = post_data.get("cloud_urls", [])
        mime_types: list[str] = post_data.get("mime_types", [])
        post_type: str = post_data.get("post_type", "FEED")

        try:
            if not cloud_urls:
                # Text-only post
                platform_id = fb_publish_text_only(caption)
            else:
                # FB carousel not fully supported — always publish first item
                platform_id = fb_publish_feed(
                    cloud_urls[0], caption, mime_types[0], post_type,
                )
            return self._make_result(success=True, platform_post_id=platform_id)
        except Exception as exc:
            raw = None
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    raw = {"status": exc.response.status_code, "body": exc.response.text[:1000]}
                except Exception:
                    pass
            return self._make_result(
                success=False,
                error_code=self.classify_error(exc),
                error_message=str(exc)[:500],
                raw_response=raw,
            )
