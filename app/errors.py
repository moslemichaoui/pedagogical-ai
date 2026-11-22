"""Typed API errors and application-wide error handling."""
from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request


class ApiError(Exception):
    """An error with a stable machine code and an Arabic user message."""

    def __init__(
        self,
        message: str,
        *,
        status: int = 400,
        code: str = "bad_request",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.details = details

    def to_response(self):
        payload = {
            "success": False,
            "error": self.message,
            "code": self.code,
        }
        if self.details is not None:
            payload["details"] = self.details
        response = jsonify(payload)
        response.status_code = self.status
        return response


def wants_json() -> bool:
    return request.path.startswith("/api/") or request.path.endswith("/healthz")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return error.to_response()

    @app.errorhandler(400)
    def bad_request(error):
        if wants_json():
            return jsonify(
                {
                    "success": False,
                    "error": "الطلب غير صالح.",
                    "code": "bad_request",
                }
            ), 400
        return render_template("errors/400.html"), 400

    @app.errorhandler(404)
    def not_found(error):
        if wants_json():
            return jsonify(
                {
                    "success": False,
                    "error": "العنصر المطلوب غير موجود.",
                    "code": "not_found",
                }
            ), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(error):
        limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        message = f"حجم الملف يتجاوز الحد المسموح ({limit_mb} ميغابايت)."
        if wants_json():
            return jsonify({"success": False, "error": message, "code": "file_too_large"}), 413
        return render_template("errors/413.html", message=message), 413

    @app.errorhandler(429)
    def rate_limited(error):
        if wants_json():
            return jsonify(
                {
                    "success": False,
                    "error": "تم بلوغ الحد الأقصى للطلبات. أعد المحاولة لاحقاً.",
                    "code": "rate_limited",
                }
            ), 429
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Unhandled server error")
        try:
            from app import db

            db.session.rollback()
        except Exception:
            pass
        if wants_json():
            return jsonify(
                {
                    "success": False,
                    "error": "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.",
                    "code": "internal_error",
                }
            ), 500
        return render_template("errors/500.html"), 500


def register_security(app: Flask) -> None:
    """Same-origin guard for writes plus defensive response headers."""

    @app.before_request
    def verify_origin():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        if app.config.get("TESTING"):
            return None
        source = request.headers.get("Origin") or request.headers.get("Referer")
        if not source:
            return None
        host = urlparse(source).netloc
        if host and host != request.host:
            raise ApiError(
                "طلب من مصدر غير موثوق.",
                status=403,
                code="origin_rejected",
            )
        return None

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'",
        )
        if not app.debug:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
