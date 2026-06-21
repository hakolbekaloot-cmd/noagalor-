"""Smoke tests for the public /privacy page."""

import pytest


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("WEB_PANEL_SECRET", "test-secret")
    # Force re-import so the auth secret is picked up.
    import importlib
    import web_app
    importlib.reload(web_app)
    web_app.app.config["TESTING"] = True
    return web_app.app.test_client()


def test_privacy_is_public(client):
    """Privacy page must be reachable without auth — Meta crawler needs it."""
    resp = client.get("/privacy")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("Content-Type", "")


def test_privacy_contains_required_sections(client):
    body = client.get("/privacy").data.decode("utf-8")
    # Hebrew section
    assert "מדיניות פרטיות" in body
    assert "Social Publisher" in body
    assert "shiraagd@gmail.com" in body
    # English section (Meta reviewers usually read English)
    assert "Privacy Policy" in body
    assert "Third parties" in body or "Third Parties" in body
    # Must mention the platforms our app uses
    assert "Facebook" in body
    assert "Instagram" in body
    assert "Google" in body
    assert "LinkedIn" in body


def test_other_paths_still_require_auth(client):
    """Sanity check: adding /privacy didn't accidentally open up the panel."""
    resp = client.get("/api/posts")
    assert resp.status_code == 401
