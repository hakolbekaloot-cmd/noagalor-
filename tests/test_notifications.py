"""
test_notifications.py — בדיקות יחידה ל-notifications.py
"""

from unittest.mock import patch, MagicMock

from notifications import (
    send_telegram,
    notify_publish_error,
    notify_partial_success,
    notify_health_issue,
    notify_gbp_error,
    notify_processing_timeout,
    is_telegram_configured,
    _truncate,
    _row_link,
    _client_line,
)


class TestIsTelegramConfigured:
    @patch("notifications.TELEGRAM_BOT_TOKEN", "tok")
    @patch("notifications.TELEGRAM_CHAT_IDS", ["123"])
    def test_configured(self):
        assert is_telegram_configured() is True

    @patch("notifications.TELEGRAM_BOT_TOKEN", "tok")
    @patch("notifications.TELEGRAM_CHAT_IDS", ["123", "456"])
    def test_configured_multiple(self):
        assert is_telegram_configured() is True

    @patch("notifications.TELEGRAM_BOT_TOKEN", "")
    @patch("notifications.TELEGRAM_CHAT_IDS", ["123"])
    def test_missing_token(self):
        assert is_telegram_configured() is False

    @patch("notifications.TELEGRAM_BOT_TOKEN", "tok")
    @patch("notifications.TELEGRAM_CHAT_IDS", [])
    def test_missing_chat_id(self):
        assert is_telegram_configured() is False


class TestSendTelegram:
    @patch("notifications.TELEGRAM_BOT_TOKEN", "")
    @patch("notifications.TELEGRAM_CHAT_IDS", [])
    def test_not_configured_returns_false(self):
        assert send_telegram("hello") is False

    @patch("notifications.TELEGRAM_BOT_TOKEN", "tok123")
    @patch("notifications.TELEGRAM_CHAT_IDS", ["999"])
    @patch("notifications.requests.post")
    def test_success(self, mock_post):
        mock_post.return_value = MagicMock(ok=True)
        assert send_telegram("test msg") is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["chat_id"] == "999"
        assert call_kwargs[1]["json"]["text"] == "test msg"

    @patch("notifications.TELEGRAM_BOT_TOKEN", "tok123")
    @patch("notifications.TELEGRAM_CHAT_IDS", ["111", "222"])
    @patch("notifications.requests.post")
    def test_success_multiple_ids(self, mock_post):
        mock_post.return_value = MagicMock(ok=True)
        assert send_telegram("test msg") is True
        assert mock_post.call_count == 2
        chat_ids = [c[1]["json"]["chat_id"] for c in mock_post.call_args_list]
        assert chat_ids == ["111", "222"]

    @patch("notifications.TELEGRAM_BOT_TOKEN", "tok123")
    @patch("notifications.TELEGRAM_CHAT_IDS", ["999"])
    @patch("notifications.requests.post")
    def test_api_failure_returns_false(self, mock_post):
        mock_post.return_value = MagicMock(ok=False, status_code=400, text="Bad Request")
        assert send_telegram("test") is False

    @patch("notifications.TELEGRAM_BOT_TOKEN", "tok123")
    @patch("notifications.TELEGRAM_CHAT_IDS", ["111", "222"])
    @patch("notifications.requests.post")
    def test_partial_failure_returns_true(self, mock_post):
        """אם ID אחד נכשל והשני מצליח — מחזיר True."""
        mock_post.side_effect = [
            MagicMock(ok=False, status_code=400, text="Bad"),
            MagicMock(ok=True),
        ]
        assert send_telegram("test") is True

    @patch("notifications.TELEGRAM_BOT_TOKEN", "tok123")
    @patch("notifications.TELEGRAM_CHAT_IDS", ["999"])
    @patch("notifications.requests.post", side_effect=Exception("network error"))
    def test_exception_returns_false(self, mock_post):
        assert send_telegram("test") is False


class TestNotifyFunctions:
    @patch("notifications.send_telegram")
    def test_notify_publish_error(self, mock_send):
        notify_publish_error("42", "Something broke")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][0]
        assert "#42" in msg
        assert "Something broke" in msg

    @patch("notifications.send_telegram")
    def test_notify_publish_error_escapes_html(self, mock_send):
        notify_publish_error("5", 'Error: <script>alert("xss")</script> & more')
        msg = mock_send.call_args[0][0]
        assert "<script>" not in msg
        assert "&lt;script&gt;" in msg
        assert "&amp; more" in msg

    @patch("notifications.send_telegram")
    def test_notify_partial_success(self, mock_send):
        notify_partial_success("7", "IG:123", "FB: timeout")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][0]
        assert "#7" in msg
        assert "IG:123" in msg

    @patch("notifications.send_telegram")
    def test_notify_partial_success_escapes_html(self, mock_send):
        notify_partial_success("3", "IG:<ok>", "FB: <error>")
        msg = mock_send.call_args[0][0]
        assert "&lt;ok&gt;" in msg
        assert "&lt;error&gt;" in msg

    @patch("notifications.send_telegram")
    def test_notify_health_issue(self, mock_send):
        notify_health_issue("Cloudinary", "connection refused")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][0]
        assert "Cloudinary" in msg

    @patch("notifications.send_telegram")
    def test_notify_health_issue_escapes_html(self, mock_send):
        notify_health_issue("Meta", "Token <expired> & invalid")
        msg = mock_send.call_args[0][0]
        assert "&lt;expired&gt;" in msg
        assert "&amp; invalid" in msg


class TestNotifyWithCorrelationId:
    @patch("notifications.send_telegram")
    def test_notify_publish_error_with_correlation_id(self, mock_send):
        notify_publish_error("42", "Something broke", correlation_id="job_20260327_180005_abc")
        msg = mock_send.call_args[0][0]
        assert "job_20260327_180005_abc" in msg
        assert "#42" in msg

    @patch("notifications.send_telegram")
    def test_notify_publish_error_without_correlation_id(self, mock_send):
        notify_publish_error("42", "Something broke")
        msg = mock_send.call_args[0][0]
        assert "Job:" not in msg

    @patch("notifications.send_telegram")
    def test_notify_partial_success_with_correlation_id(self, mock_send):
        notify_partial_success("7", "IG:123", "FB: timeout", correlation_id="job_abc")
        msg = mock_send.call_args[0][0]
        assert "job_abc" in msg

    @patch("notifications.send_telegram")
    def test_notify_gbp_error(self, mock_send):
        notify_gbp_error("10", "http_403", "Forbidden", correlation_id="job_gbp_123")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][0]
        assert "GBP" in msg
        assert "#10" in msg
        assert "http_403" in msg
        assert "Forbidden" in msg
        assert "job_gbp_123" in msg

    @patch("notifications.send_telegram")
    def test_notify_gbp_error_escapes_html(self, mock_send):
        notify_gbp_error("5", "err", '<script>alert("x")</script>')
        msg = mock_send.call_args[0][0]
        assert "<script>" not in msg
        assert "&lt;script&gt;" in msg

    @patch("notifications.send_telegram")
    def test_notify_processing_timeout(self, mock_send):
        notify_processing_timeout("15", 10)
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][0]
        assert "#15" in msg
        assert "10" in msg
        assert "PROCESSING" in msg


class TestTruncate:
    def test_short_text(self):
        assert _truncate("hello", 100) == "hello"

    def test_long_text(self):
        result = _truncate("a" * 200, 50)
        assert len(result) == 50
        assert result.endswith("...")


class TestRowLink:
    @patch("notifications.APP_BASE_URL", "")
    def test_empty_when_base_url_missing(self):
        assert _row_link("42") == ""

    @patch("notifications.APP_BASE_URL", "https://app.example.com")
    def test_empty_when_row_id_missing(self):
        assert _row_link("") == ""
        assert _row_link(None) == ""

    @patch("notifications.APP_BASE_URL", "https://app.example.com")
    def test_link_built(self):
        link = _row_link("42")
        assert 'href="https://app.example.com/?id=42"' in link
        assert "פתח בדפדפן" in link

    @patch("notifications.APP_BASE_URL", "https://app.example.com")
    def test_link_url_encodes_special_chars(self):
        # post ids may contain spaces, slashes, or other URL-reserved chars.
        link = _row_link("a b/c?d")
        assert 'href="https://app.example.com/?id=a%20b%2Fc%3Fd"' in link


class TestClientLine:
    @patch("notifications.CLIENT_NAME", "")
    def test_empty_when_unset(self):
        assert _client_line() == ""

    @patch("notifications.CLIENT_NAME", "Acme")
    def test_included_when_set(self):
        assert "Acme" in _client_line()
        assert "לקוח" in _client_line()

    @patch("notifications.CLIENT_NAME", "<Acme & Co>")
    def test_escapes_html(self):
        line = _client_line()
        assert "<Acme" not in line
        assert "&lt;Acme" in line
        assert "&amp;" in line


class TestNotifyWithDeepLink:
    @patch("notifications.APP_BASE_URL", "https://app.example.com")
    @patch("notifications.send_telegram")
    def test_publish_error_includes_link(self, mock_send):
        notify_publish_error("42", "oops")
        msg = mock_send.call_args[0][0]
        assert 'href="https://app.example.com/?id=42"' in msg

    @patch("notifications.APP_BASE_URL", "")
    @patch("notifications.send_telegram")
    def test_publish_error_no_link_when_unset(self, mock_send):
        notify_publish_error("42", "oops")
        msg = mock_send.call_args[0][0]
        assert "href=" not in msg

    @patch("notifications.APP_BASE_URL", "https://app.example.com")
    @patch("notifications.send_telegram")
    def test_partial_success_includes_link(self, mock_send):
        notify_partial_success("7", "IG:ok", "FB: fail")
        msg = mock_send.call_args[0][0]
        assert 'href="https://app.example.com/?id=7"' in msg

    @patch("notifications.APP_BASE_URL", "https://app.example.com")
    @patch("notifications.send_telegram")
    def test_gbp_error_includes_link(self, mock_send):
        notify_gbp_error("10", "http_403", "Forbidden")
        msg = mock_send.call_args[0][0]
        assert 'href="https://app.example.com/?id=10"' in msg

    @patch("notifications.APP_BASE_URL", "https://app.example.com")
    @patch("notifications.send_telegram")
    def test_processing_timeout_includes_link(self, mock_send):
        notify_processing_timeout("15", 10)
        msg = mock_send.call_args[0][0]
        assert 'href="https://app.example.com/?id=15"' in msg

    @patch("notifications.APP_BASE_URL", "https://app.example.com")
    @patch("notifications.send_telegram")
    def test_health_issue_has_no_link(self, mock_send):
        # health alerts are not tied to a specific row
        notify_health_issue("Cloudinary", "down")
        msg = mock_send.call_args[0][0]
        assert "href=" not in msg


class TestNotifyWithClientName:
    @patch("notifications.CLIENT_NAME", "Acme")
    @patch("notifications.send_telegram")
    def test_publish_error_includes_client(self, mock_send):
        notify_publish_error("42", "oops")
        msg = mock_send.call_args[0][0]
        assert "Acme" in msg

    @patch("notifications.CLIENT_NAME", "")
    @patch("notifications.send_telegram")
    def test_publish_error_no_client_when_unset(self, mock_send):
        notify_publish_error("42", "oops")
        msg = mock_send.call_args[0][0]
        assert "לקוח:" not in msg

    @patch("notifications.CLIENT_NAME", "Acme")
    @patch("notifications.send_telegram")
    def test_health_issue_includes_client(self, mock_send):
        notify_health_issue("Cloudinary", "down")
        msg = mock_send.call_args[0][0]
        assert "Acme" in msg

    @patch("notifications.CLIENT_NAME", "Acme")
    @patch("notifications.send_telegram")
    def test_partial_success_includes_client(self, mock_send):
        notify_partial_success("7", "IG:ok", "FB: fail")
        msg = mock_send.call_args[0][0]
        assert "Acme" in msg

    @patch("notifications.CLIENT_NAME", "Acme")
    @patch("notifications.send_telegram")
    def test_gbp_error_includes_client(self, mock_send):
        notify_gbp_error("10", "http_403", "Forbidden")
        msg = mock_send.call_args[0][0]
        assert "Acme" in msg

    @patch("notifications.CLIENT_NAME", "Acme")
    @patch("notifications.send_telegram")
    def test_processing_timeout_includes_client(self, mock_send):
        notify_processing_timeout("15", 10)
        msg = mock_send.call_args[0][0]
        assert "Acme" in msg
