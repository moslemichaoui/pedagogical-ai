"""Application configuration.

All secrets come from the environment. ``.env`` is loaded once, at import
time, from the project root so both ``flask run`` and ``python run.py`` see
the same values.
"""
from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

PLACEHOLDER_KEYS = {"", "your-gemini-api-key-here", "changeme"}


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(_env(name, str(default)) or default)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _get_gemini_keys() -> List[str]:
    """Collect configured Gemini keys, preserving order and dropping dupes."""
    keys: List[str] = []
    candidates = [os.environ.get("GEMINI_API_KEY")]
    candidates += [os.environ.get(f"GEMINI_API_KEY_{i}") for i in range(1, 6)]
    for raw in candidates:
        key = (raw or "").strip()
        if key and key not in PLACEHOLDER_KEYS and key not in keys:
            keys.append(key)
    return keys


def _get_gemini_models() -> List[str]:
    """Collect configured Gemini models, newest first, without duplicates."""
    models: List[str] = []
    candidates = [os.environ.get("GEMINI_MODEL")]
    candidates += [os.environ.get(f"GEMINI_MODEL_{i}") for i in range(1, 4)]
    for raw in candidates:
        model = (raw or "").strip()
        if model and model not in models:
            models.append(model)
    if not models:
        models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    return models


class Config:
    # --- Core ---------------------------------------------------------
    APP_NAME = "Pedagogical AI"
    APP_NAME_AR = "منصة الإعداد التربوي"
    SECRET_KEY = _env("SECRET_KEY") or "dev-only-change-me"
    DEBUG = _env_bool("FLASK_DEBUG", False)
    TESTING = False

    SQLALCHEMY_DATABASE_URI = _env("DATABASE_URL") or (
        "sqlite:///" + os.path.join(basedir, "instance", "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Only these proxy addresses may supply X-Forwarded-For. Empty = never trust it.
    TRUSTED_PROXIES = _env("TRUSTED_PROXIES", "") or ""

    # --- Gemini -------------------------------------------------------
    GEMINI_API_KEYS = _get_gemini_keys()
    GEMINI_MODELS = _get_gemini_models()
    GEMINI_EMBEDDING_MODEL = _env("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
    GEMINI_TIMEOUT_SECONDS = _env_int("GEMINI_TIMEOUT_SECONDS", 90, 10, 300)
    GEMINI_TEMPERATURE = float(_env("GEMINI_TEMPERATURE", "0.25") or 0.25)
    GEMINI_MAX_OUTPUT_TOKENS = _env_int("GEMINI_MAX_OUTPUT_TOKENS", 8192, 1024, 65536)

    # --- Storage ------------------------------------------------------
    UPLOAD_FOLDER = _env("UPLOAD_FOLDER") or os.path.join(basedir, "uploads")
    EXPORT_FOLDER = _env("EXPORT_FOLDER") or os.path.join(basedir, "exports")
    CHROMA_PERSIST_DIR = _env("CHROMA_PERSIST_DIR") or os.path.join(
        basedir, "chromadb_data"
    )
    MAX_CONTENT_LENGTH = _env_int("MAX_UPLOAD_MB", 25, 1, 100) * 1024 * 1024

    # --- RAG ----------------------------------------------------------
    RAG_TOP_K = _env_int("RAG_TOP_K", 6, 1, 20)
    RAG_MIN_SIMILARITY = float(_env("RAG_MIN_SIMILARITY", "0.15") or 0.15)
    CHUNK_SIZE = _env_int("CHUNK_SIZE", 700, 200, 3000)
    CHUNK_OVERLAP = _env_int("CHUNK_OVERLAP", 80, 0, 500)

    # --- Product limits ----------------------------------------------
    MAX_LESSONS_PER_PAGE = 24
    MAX_EXERCISES = 20
    RATE_LIMIT_GENERATE_PER_HOUR = _env_int("RATE_LIMIT_GENERATE", 20, 1, 500)
    RATE_LIMIT_UPLOAD_PER_HOUR = _env_int("RATE_LIMIT_UPLOAD", 30, 1, 500)

    # --- Subjects / levels (single source of truth) -------------------
    SUBJECTS = [
        "الإيقاظ العلمي",
        "الرياضيات",
        "اللغة العربية",
        "اللغة الفرنسية",
        "التربية الإسلامية",
        "التربية المدنية",
    ]
    LEVELS = [
        "السنة الأولى ابتدائي",
        "السنة الثانية ابتدائي",
        "السنة الثالثة ابتدائي",
        "السنة الرابعة ابتدائي",
        "السنة الخامسة ابتدائي",
        "السنة السادسة ابتدائي",
    ]
    SOURCE_TYPES = {
        "official": "وثيقة رسمية",
        "teacher_upload": "وثيقة المعلّم",
        "web": "مرجع ويب موثوق",
    }

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.GEMINI_API_KEYS)


class TestConfig(Config):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    GEMINI_API_KEYS: List[str] = []
    RATE_LIMIT_GENERATE_PER_HOUR = 1000
    RATE_LIMIT_UPLOAD_PER_HOUR = 1000
