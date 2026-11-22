"""Application factory for Pedagogical AI."""
from __future__ import annotations

import logging
import os
from datetime import datetime

from flask import Flask, request, url_for
from flask_sqlalchemy import SQLAlchemy

from config import Config

APP_VERSION = "3.1.2"

db = SQLAlchemy()

ARABIC_MONTHS = [
    "جانفي",
    "فيفري",
    "مارس",
    "أفريل",
    "ماي",
    "جوان",
    "جويلية",
    "أوت",
    "سبتمبر",
    "أكتوبر",
    "نوفمبر",
    "ديسمبر",
]


def create_app(config_class=Config) -> Flask:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(base, "templates"),
        static_folder=os.path.join(base, "static"),
    )
    app.config.from_object(config_class)
    app.config.setdefault("APP_VERSION", APP_VERSION)

    _configure_logging(app)
    for key in ("UPLOAD_FOLDER", "EXPORT_FOLDER", "CHROMA_PERSIST_DIR"):
        path = app.config.get(key)
        if path:
            os.makedirs(path, exist_ok=True)
    instance_dir = os.path.join(base, "instance")
    os.makedirs(instance_dir, exist_ok=True)

    db.init_app(app)

    from app.models import (  # noqa: F401
        Assessment,
        Document,
        DocumentChunk,
        Exercise,
        GenerationRequest,
        GenerationRun,
        Lesson,
        User,
    )

    with app.app_context():
        from app.migrations import run_migrations

        run_migrations()

    _register_blueprints(app)
    _register_template_helpers(app)

    from app.errors import register_error_handlers, register_security

    register_error_handlers(app)
    register_security(app)

    if not app.config.get("GEMINI_API_KEYS") and not app.testing:
        app.logger.warning(
            "No GEMINI_API_KEY configured: generation will return a guided setup error."
        )
    secret = str(app.config.get("SECRET_KEY") or "").strip()
    if secret in {"", "dev-only-change-me", "changeme"} and not app.testing:
        raise RuntimeError(
            "SECRET_KEY must be set to a long random value in .env before starting the app."
        )

    return app


def _configure_logging(app: Flask) -> None:
    if app.testing:
        return
    level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _register_blueprints(app: Flask) -> None:
    from app.routes.assessments import bp as assessments_bp
    from app.routes.documents import bp as documents_bp
    from app.routes.exercises import bp as exercises_bp
    from app.routes.lessons import bp as lessons_bp
    from app.routes.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(lessons_bp)
    app.register_blueprint(exercises_bp)
    app.register_blueprint(assessments_bp)


def _register_template_helpers(app: Flask) -> None:
    @app.template_filter("ar_date")
    def ar_date(value, with_time: bool = False):
        if not value:
            return "—"
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        text = f"{value.day} {ARABIC_MONTHS[value.month - 1]} {value.year}"
        if with_time:
            text += f" · {value.strftime('%H:%M')}"
        return text

    @app.template_filter("minutes")
    def minutes(value):
        return f"{value} د" if value else "—"

    @app.template_filter("short")
    def short(value, limit: int = 90):
        text = (value or "").strip()
        return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

    @app.context_processor
    def inject_globals():
        nav = [
            ("main.dashboard", "الرئيسية", "home"),
            ("main.create_lesson", "حضّر درساً", "plus"),
            ("main.lessons_library", "جذاذاتي", "book"),
            ("documents.documents_page", "الوثائق", "folder"),
            ("main.settings", "الإعدادات", "settings"),
        ]
        endpoint = request.endpoint or ""
        return {
            "nav_items": nav,
            "current_endpoint": endpoint,
            "app_name": app.config["APP_NAME"],
            "app_name_ar": app.config["APP_NAME_AR"],
            "app_version": app.config["APP_VERSION"],
            "subjects": app.config["SUBJECTS"],
            "levels": app.config["LEVELS"],
            "source_types": app.config["SOURCE_TYPES"],
            "ai_configured": bool(app.config["GEMINI_API_KEYS"]),
            "year": datetime.now().year,
        }

    @app.template_global()
    def static_url(filename: str) -> str:
        return url_for("static", filename=filename, v=APP_VERSION)
