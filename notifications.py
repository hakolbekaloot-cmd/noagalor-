"""
notifications.py — שליחת התראות לטלגרם

שולח הודעות למפתח כשפוסט נכשל או כשיש בעיות מערכתיות.
דורש הגדרת TELEGRAM_BOT_TOKEN ו-TELEGRAM_CHAT_ID.
אם לא מוגדרים — ההתראות מושתקות (לא זורק שגיאה).
"""

import html
import logging
import os
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = [
    cid.strip() for cid in os.environ.get("TELEGRAM_CHAT_ID", "").split(",") if cid.strip()
]
CLIENT_NAME = os.environ.get("CLIENT_NAME", "")
REPO_URL = os.environ.get("REPO_URL", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "").rstrip("/")

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TIMEOUT = 10  # seconds


def is_telegram_configured() -> bool:
    """בודק אם התראות טלגרם מוגדרות."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS)


def send_telegram(message: str) -> bool:
    """
    שולח הודעת טקסט לטלגרם (לכל ה-chat IDs שהוגדרו).
    מחזיר True אם נשלח בהצלחה לפחות לאחד, False אחרת.
    לעולם לא זורק exception — שגיאת התראה לא צריכה לשבור את הפרסום.
    """
    if not is_telegram_configured():
        logger.debug("Telegram not configured — skipping notification")
        return False

    any_ok = False
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            resp = requests.post(
                TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN),
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
                timeout=TIMEOUT,
            )
            if resp.ok:
                logger.info(f"Telegram notification sent to {chat_id}")
                any_ok = True
            else:
                logger.warning(f"Telegram send to {chat_id} failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.warning(f"Telegram send to {chat_id} error: {e}")
    return any_ok


def _client_line() -> str:
    """שורת זיהוי לקוח/סביבה (ריק אם CLIENT_NAME לא מוגדר)."""
    if not CLIENT_NAME:
        return ""
    return f"<b>לקוח:</b> {html.escape(CLIENT_NAME)}"


def _row_link(row_id) -> str:
    """קישור עמוק לפוסט ב-UI (לפי עמודת id), או מחרוזת ריקה אם APP_BASE_URL לא מוגדר."""
    if not APP_BASE_URL or row_id in (None, ""):
        return ""
    # URL-encode for the query string; then HTML-escape for safe embedding in <a href="...">.
    id_q = html.escape(quote(str(row_id), safe=""), quote=True)
    return f'<a href="{APP_BASE_URL}/?id={id_q}">🔗 פתח בדפדפן</a>'


def notify_publish_error(row_id: str, error_msg: str, *, correlation_id: str = ""):
    """התראה על כשל בפרסום פוסט."""
    lines = ["<b>❌ שגיאת פרסום</b>"]
    if client := _client_line():
        lines.append(client)
    lines.append(f"<b>פוסט:</b> #{html.escape(str(row_id))}")
    if correlation_id:
        lines.append(f"<b>Job:</b> <code>{html.escape(correlation_id)}</code>")
    lines.append(f"<b>שגיאה:</b> {html.escape(_truncate(error_msg, 500))}")
    if link := _row_link(row_id):
        lines.append(link)
    send_telegram("\n".join(lines))


def notify_partial_success(row_id: str, result: str, error_msg: str, *, correlation_id: str = ""):
    """התראה על הצלחה חלקית (רשת אחת הצליחה, אחרת נכשלה)."""
    lines = ["<b>⚠️ הצלחה חלקית</b>"]
    if client := _client_line():
        lines.append(client)
    lines.append(f"<b>פוסט:</b> #{html.escape(str(row_id))}")
    if correlation_id:
        lines.append(f"<b>Job:</b> <code>{html.escape(correlation_id)}</code>")
    lines.append(f"<b>הצליח:</b> {html.escape(result)}")
    lines.append(f"<b>נכשל:</b> {html.escape(_truncate(error_msg, 400))}")
    if link := _row_link(row_id):
        lines.append(link)
    send_telegram("\n".join(lines))


def notify_gbp_error(row_id: str, error_code: str, error_msg: str, *, correlation_id: str = ""):
    """התראה ייעודית על כשל בפרסום ל-Google Business Profile."""
    lines = ["<b>📍 שגיאת GBP</b>"]
    if client := _client_line():
        lines.append(client)
    lines.append(f"<b>פוסט:</b> #{html.escape(str(row_id))}")
    if correlation_id:
        lines.append(f"<b>Job:</b> <code>{html.escape(correlation_id)}</code>")
    if error_code:
        lines.append(f"<b>קוד:</b> {html.escape(error_code)}")
    lines.append(f"<b>שגיאה:</b> {html.escape(_truncate(error_msg, 500))}")
    if link := _row_link(row_id):
        lines.append(link)
    send_telegram("\n".join(lines))


def notify_processing_timeout(row_id: str, timeout_minutes: int):
    """התראה על שורה שתקועה ב-PROCESSING מעבר ל-timeout."""
    lines = ["<b>⏰ Timeout — שורה תקועה</b>"]
    if client := _client_line():
        lines.append(client)
    lines.append(f"<b>פוסט:</b> #{html.escape(str(row_id))}")
    lines.append(f"<b>זמן:</b> תקועה ב-PROCESSING יותר מ-{timeout_minutes} דקות")
    lines.append("<b>פעולה:</b> השורה שוחררה ותנסה שוב")
    if link := _row_link(row_id):
        lines.append(link)
    send_telegram("\n".join(lines))


def notify_health_issue(service: str, error_msg: str):
    """התראה על בעיה בשירות חיצוני."""
    lines = ["<b>🔴 בעיית חיבור</b>"]
    if client := _client_line():
        lines.append(client)
    lines.append(f"<b>שירות:</b> {html.escape(service)}")
    lines.append(f"<b>שגיאה:</b> {html.escape(_truncate(error_msg, 500))}")
    send_telegram("\n".join(lines))


def notify_meta_api_version_expiry(version: str, expiry_date: str, days_left: int):
    """התראה על גרסת Meta API שעומדת לפוג."""
    if days_left <= 7:
        emoji = "🔴"
    elif days_left <= 30:
        emoji = "🟡"
    else:
        emoji = "🟢"
    lines = [f"<b>{emoji} גרסת Meta API עומדת לפוג</b>"]
    if client := _client_line():
        lines.append(client)
    lines.append(f"<b>גרסה:</b> {html.escape(version)}")
    lines.append(f"<b>תפוגה:</b> {html.escape(expiry_date)}")
    lines.append(f"<b>נותרו:</b> {days_left} ימים")
    if REPO_URL:
        lines.append(f"<b>ריפו:</b> {html.escape(REPO_URL)}")
    send_telegram("\n".join(lines))


def notify_meta_api_version_unknown(version: str):
    """התראה שלא ניתן לבדוק תפוגת גרסת Meta API."""
    lines = ["<b>ℹ️ לא ניתן לבדוק תפוגת גרסת Meta API</b>"]
    if client := _client_line():
        lines.append(client)
    lines.append(f"<b>גרסה:</b> {html.escape(version)}")
    lines.append("יש לבדוק ידנית ב: https://developers.facebook.com/docs/graph-api/changelog/")
    if REPO_URL:
        lines.append(f"<b>ריפו:</b> {html.escape(REPO_URL)}")
    send_telegram("\n".join(lines))


def _truncate(text: str, max_len: int) -> str:
    """קיצור טקסט ארוך."""
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text
