"""Application-level smoke tests and API contract checks."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from flask import Flask

from app import create_app, db
from config import TestConfig


@pytest.mark.parametrize(
    "path",
    ["/", "/create", "/library", "/documents", "/settings", "/about"],
)
def test_public_pages_render_arabic_rtl(client, path):
    response = client.get(path)
    assert response.status_code == 200, path
    html = response.get_data(as_text=True)
    assert '<html lang="ar" dir="rtl">' in html
    assert 'id="main"' in html
    assert 'tabindex="-1"' in html
    assert "تجاوز إلى المحتوى" in html


def test_hidden_overlay_cannot_cover_create_page(client):
    """Regression: `display: grid` on .gen-overlay used to override [hidden]."""
    css = (
        Path(__file__).resolve().parents[1] / "static" / "css" / "app.css"
    ).read_text(encoding="utf-8")
    assert "[hidden] { display: none !important; }" in css
    html = client.get("/create").get_data(as_text=True)
    assert 'id="gen-overlay" hidden' in html


def test_healthz_has_expected_shape_and_security_headers(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json["status"] == "ok"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]


def test_readyz_degrades_without_gemini_and_hides_db_detail(client):
    response = client.get("/readyz")
    assert response.status_code == 503
    payload = response.json
    assert payload["status"] == "degraded"
    assert payload["checks"]["gemini"]["status"] == "not_configured"
    assert "detail" not in payload["checks"]["database"]


def test_readyz_never_leaks_database_exception(client, monkeypatch):
    secret = "/srv/private/db/password.txt"

    def boom(*_args, **_kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(db.session, "execute", boom)
    response = client.get("/readyz")
    payload = response.json
    assert response.status_code == 503
    assert payload["checks"]["database"] == {"status": "error"}
    assert secret not in json.dumps(payload, ensure_ascii=False)


def test_generate_endpoint_keeps_legacy_error_contract(client):
    response = client.post("/api/lessons/generate", json={"topic": "دورة الماء"})
    assert response.status_code == 400
    payload = response.json
    assert payload["success"] is False
    assert payload["error"]
    assert isinstance(payload["validation_errors"], list)
    assert payload["validation_errors"]


def test_missing_api_resource_returns_compatible_not_found(client):
    response = client.get("/api/lessons/999999")
    assert response.status_code == 404
    assert response.json["success"] is False
    assert response.json["error"]
    assert response.json["code"] == "not_found"


def test_placeholder_secret_is_rejected_outside_testing(tmp_path):
    class BadConfig(TestConfig):
        TESTING = False
        DEBUG = False
        SECRET_KEY = "dev-only-change-me"
        UPLOAD_FOLDER = str(tmp_path / "uploads")
        EXPORT_FOLDER = str(tmp_path / "exports")
        CHROMA_PERSIST_DIR = str(tmp_path / "chroma")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(BadConfig)


def test_rate_limit_ignores_untrusted_forwarded_header():
    from app.utils.rate_limit import rate_limit, reset_limits

    reset_limits()
    app = Flask(__name__)
    app.config["LIMIT"] = 1
    app.config["TRUSTED_PROXIES"] = ""

    @app.get("/limited")
    @rate_limit("test", "LIMIT")
    def limited():
        return {"ok": True}

    client = app.test_client()
    first = client.get(
        "/limited",
        environ_base={"REMOTE_ADDR": "203.0.113.10"},
        headers={"X-Forwarded-For": "1.1.1.1"},
    )
    second = client.get(
        "/limited",
        environ_base={"REMOTE_ADDR": "203.0.113.10"},
        headers={"X-Forwarded-For": "2.2.2.2"},
    )
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["Retry-After"]
    reset_limits()


def test_rate_limit_honours_forwarded_header_only_from_trusted_proxy():
    from app.utils.rate_limit import rate_limit, reset_limits

    reset_limits()
    app = Flask(__name__)
    app.config["LIMIT"] = 1
    app.config["TRUSTED_PROXIES"] = "127.0.0.1"

    @app.get("/limited")
    @rate_limit("test", "LIMIT")
    def limited():
        return {"ok": True}

    client = app.test_client()
    first = client.get(
        "/limited",
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
        headers={"X-Forwarded-For": "1.1.1.1"},
    )
    second = client.get(
        "/limited",
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
        headers={"X-Forwarded-For": "2.2.2.2"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    reset_limits()
