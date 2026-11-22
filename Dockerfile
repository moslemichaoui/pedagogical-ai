# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Secrets and runtime settings are injected at `docker run` time via
# `--env-file` / `-e`; nothing credential-like is baked into this image.
#
# Required in production:
#   SECRET_KEY            Flask session-signing key (set a strong random value)
#   GEMINI_API_KEY        Primary Gemini key (fallbacks: GEMINI_API_KEY_1.._5)
#
# Optional (defaults shown in config.py):
#   GEMINI_MODEL, GEMINI_MODEL_1.._3, GEMINI_EMBEDDING_MODEL
#   DATABASE_URL          default: sqlite:////app/instance/app.db
#   UPLOAD_FOLDER         default: /app/uploads
#   EXPORT_FOLDER         default: /app/exports
#   CHROMA_PERSIST_DIR    default: /app/chromadb_data
#   FLASK_DEBUG, MAX_UPLOAD_MB, RAG_TOP_K, RAG_MIN_SIMILARITY,
#   CHUNK_SIZE, CHUNK_OVERLAP, GEMINI_TIMEOUT_SECONDS,
#   GEMINI_TEMPERATURE, GEMINI_MAX_OUTPUT_TOKENS,
#   RATE_LIMIT_GENERATE, RATE_LIMIT_UPLOAD
#
# Example:
#   docker run --env-file .env -p 5000:5000 pedagogical-ai

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
 && python -m pip install -r /app/requirements.txt

COPY . /app

# Keep all writable state under /app owned by the unprivileged runtime user.
RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 appuser \
 && mkdir -p /app/instance /app/uploads /app/exports /app/chromadb_data \
 && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

# urllib is part of the stdlib; curl is not installed in slim images.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=3).status == 200 else 1)"]

# Railway/Render inject PORT; shell form allows ${PORT} expansion.
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers ${WEB_CONCURRENCY:-1} --timeout 120 --access-logfile - --error-logfile - run:app
