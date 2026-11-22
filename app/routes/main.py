"""Server-rendered pages: dashboard, creation form, library, detail, settings."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
)
from sqlalchemy import text

from app import db
from app.ai.gemini_provider import GeminiProvider
from app.ai.schemas import SECTION_LABELS
from app.models import Document, Lesson
from app.services.analytics_service import AnalyticsService
from app.services.lesson_service import LessonService
from app.services.retrieval_service import RetrievalService
from app.utils.text import parse_int

bp = Blueprint("main", __name__)


@bp.get("/")
def dashboard():
    analytics = AnalyticsService()
    return render_template(
        "dashboard.html",
        page_title="لوحة المعلّم",
        overview=analytics.overview(),
        subjects=analytics.subject_breakdown(),
        recent_lessons=analytics.recent_lessons(4),
        recent_documents=analytics.recent_documents(4),
        activity=analytics.activity_by_day(10),
    )


@bp.get("/create")
def create_lesson():
    return render_template(
        "create_lesson.html",
        page_title="تحضير درس جديد",
        draft={
            "subject": request.args.get("subject", "الإيقاظ العلمي"),
            "educational_level": request.args.get("level", "السنة الرابعة ابتدائي"),
            "duration": parse_int(request.args.get("duration"), 45, 5, 180),
            "topic": request.args.get("topic", ""),
        },
        documents=Document.query.filter_by(status="ready")
        .order_by(Document.created_at.desc())
        .limit(50)
        .all(),
    )


@bp.get("/library")
def lessons_library():
    page = parse_int(request.args.get("page"), 1, 1, 9999)
    result = LessonService.list_lessons(
        subject=request.args.get("subject") or None,
        educational_level=request.args.get("level") or None,
        query=request.args.get("q") or None,
        page=page,
        per_page=9,
    )
    return render_template(
        "lessons.html",
        page_title="جذاذاتي",
        result=result,
        filters={
            "subject": request.args.get("subject", ""),
            "level": request.args.get("level", ""),
            "q": request.args.get("q", ""),
        },
    )


@bp.get("/lessons/<int:lesson_id>")
def lesson_detail(lesson_id: int):
    lesson = LessonService.get(lesson_id)
    if lesson is None:
        abort(404)
    plan = LessonService.plan_of(lesson)
    return render_template(
        "lesson_detail.html",
        page_title=lesson.title,
        lesson=lesson,
        plan=plan,
        sections=SECTION_LABELS,
        exercises=[item for item in lesson.exercises if item.kind == "exercise"],
        assessments=[item for item in lesson.exercises if item.kind == "assessment"],
    )


@bp.get("/lessons/<int:lesson_id>/print")
def lesson_print(lesson_id: int):
    lesson = LessonService.get(lesson_id)
    if lesson is None:
        abort(404)
    plan = LessonService.plan_of(lesson)
    return render_template(
        "lesson_print.html",
        lesson=lesson,
        plan=plan,
        sections=SECTION_LABELS,
    )


@bp.get("/settings")
def settings():
    provider = GeminiProvider()
    retrieval = RetrievalService()
    return render_template(
        "settings.html",
        page_title="الإعدادات",
        diagnostics=_diagnostics(provider, retrieval),
        provider=provider.health_check(),
        stats=retrieval.stats(),
    )


@bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})


@bp.get("/readyz")
def readyz():
    checks: Dict[str, Any] = {}
    healthy = True

    try:
        db.session.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        checks["database"] = {"status": "error"}
        if current_app.debug:
            checks["database"]["detail"] = str(exc)[:160]
        healthy = False

    provider = GeminiProvider().health_check()
    checks["gemini"] = provider
    if provider["status"] == "not_configured":
        healthy = False

    vector = RetrievalService().chroma_service.health()
    checks["vector_index"] = vector

    return jsonify({"status": "ready" if healthy else "degraded", "checks": checks}), (
        200 if healthy else 503
    )


@bp.get("/about")
def about():
    return render_template("about.html", page_title="عن المنصة")


def _diagnostics(provider: GeminiProvider, retrieval: RetrievalService) -> Dict[str, Any]:
    config = current_app.config
    database_url = config.get("SQLALCHEMY_DATABASE_URI", "")
    return {
        "version": config.get("APP_VERSION"),
        "python": os.sys.version.split()[0],
        "database": "SQLite" if database_url.startswith("sqlite") else "قاعدة بيانات خارجية",
        "database_path": database_url.replace("sqlite:///", "") if database_url.startswith("sqlite") else "—",
        "models": config.get("GEMINI_MODELS", []),
        "keys": len(config.get("GEMINI_API_KEYS", [])),
        "embedding_model": config.get("GEMINI_EMBEDDING_MODEL"),
        "timeout": config.get("GEMINI_TIMEOUT_SECONDS"),
        "temperature": config.get("GEMINI_TEMPERATURE"),
        "top_k": config.get("RAG_TOP_K"),
        "min_similarity": config.get("RAG_MIN_SIMILARITY"),
        "chunk_size": config.get("CHUNK_SIZE"),
        "chunk_overlap": config.get("CHUNK_OVERLAP"),
        "upload_limit_mb": config.get("MAX_CONTENT_LENGTH", 0) // (1024 * 1024),
        "rate_limit_generate": config.get("RATE_LIMIT_GENERATE_PER_HOUR"),
        "upload_folder": config.get("UPLOAD_FOLDER"),
        "chroma_folder": config.get("CHROMA_PERSIST_DIR"),
        "lessons": Lesson.query.count(),
        "documents": Document.query.count(),
        "vector": retrieval.chroma_service.health(),
    }
