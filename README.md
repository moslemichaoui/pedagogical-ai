# Pedagogical AI — منصة الإعداد التربوي

> An Arabic-first Flask application that turns a teacher's lesson request into a complete, printable 21-section **جذاذة درس** (lesson sheet), grounded in the teacher's own reference documents.

Built for Tunisian primary-school teachers, initially **الإيقاظ العلمي** (scientific awakening). This is not a chatbot: it is a lesson-preparation workspace with a knowledge base, structured generation, validation, and print/DOCX export.

- [Why this exists](#why-this-exists)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Security & deployment assumptions](#security--deployment-assumptions)
- [Pages and API](#pages-and-api)
- [Testing and code quality](#testing-and-code-quality)
- [Troubleshooting](#troubleshooting)
- [Limitations and safety](#limitations-and-safety)
- [Documentation map](#documentation-map)

## Why this exists

Preparing a usable جذاذة takes time: you reconcile the official objectives, a five-phase session rhythm, the exact class duration, safe experiments, and assessment items — in Arabic, from several sources. This app does the first draft from your documents and your inputs, shows you the quality checks it ran, and lets you print or export the result. You stay the final reviewer.

The stack is deliberately small: **Flask + Jinja + SQLite/SQLAlchemy + ChromaDB + the Gemini SDK**, server-rendered pages, and vanilla JavaScript. There is **no authentication, no Redis/Celery, no SPA, and no Alembic**.

## Quick start

**Prerequisites**

- Python **3.12+** (see `pyproject.toml`)
- A Google Gemini API key for generation and document indexing (optional for browsing the UI)

```bash
# 1. Clone / open the project
cd pedagogical_ai

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# POSIX:    source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
copy .env.example .env        # Windows
# cp .env.example .env        # POSIX
# Edit .env: set SECRET_KEY and GEMINI_API_KEY

# 5. Start (the database and folders are created automatically on boot)
python run.py
```

Open <http://localhost:5000>. Health checks: `/healthz` (liveness) and `/readyz` (readiness; returns **503** when Gemini is not configured or the database is unavailable).

**Try it without an API key**

```bash
python scripts/seed_demo.py           # safe to re-run; inserts demo lessons only if absent
python scripts/seed_demo.py --reset   # delete previous demo lessons, then re-seed
```

You can now browse `/`, `/library` and a lesson detail page. Generation will show the guided Arabic setup message until a key is configured:

> لم يتم إعداد مفتاح Gemini بعد. أضف GEMINI_API_KEY في ملف .env ثم أعد تشغيل التطبيق.

For a production-like server, run `gunicorn "app:create_app()"` behind a reverse proxy. Set `FLASK_DEBUG=false` and a real `SECRET_KEY` first.

## Configuration

All values are read from the environment by `config.py` (loaded from `.env` at import time). Full, annotated list: [`.env.example`](.env.example). Placeholder Gemini keys are ignored.

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | required in non-testing mode | Flask signing key; set a long random value in `.env` (missing/placeholder values fail fast) |
| `FLASK_DEBUG` | `false` | Flask debug mode (`1/true/yes/on`) |
| `DATABASE_URL` | `sqlite:///<project>/instance/app.db` | SQLAlchemy database URL; relative SQLite paths resolve under `instance/` |
| `GEMINI_API_KEY`, `GEMINI_API_KEY_1`…`_5` | none | Generation/embedding credentials, tried in order as fallback |
| `GEMINI_MODEL`, `GEMINI_MODEL_1`…`_3` | `gemini-2.5-flash`, `gemini-2.0-flash` | Model fallback chain |
| `GEMINI_EMBEDDING_MODEL` | `text-embedding-004` | Embedding model for indexing and queries |
| `GEMINI_TIMEOUT_SECONDS` | `90` | Per-request timeout (10–300) |
| `GEMINI_TEMPERATURE` | `0.25` | Generation temperature |
| `GEMINI_MAX_OUTPUT_TOKENS` | `8192` | Output cap (1024–65536) |
| `UPLOAD_FOLDER` | `<project>/uploads` | Directory for uploaded source files (PDF/DOCX/TXT) |
| `EXPORT_FOLDER` | `<project>/exports` | DOCX export staging |
| `CHROMA_PERSIST_DIR` | `<project>/chromadb_data` | Persistent vector index |
| `MAX_UPLOAD_MB` | `25` | Request size cap (1–100; extraction also has a 25 MB hard cap) |
| `RAG_TOP_K` | `6` | Chunks per retrieval (1–20) |
| `RAG_MIN_SIMILARITY` | `0.15` | Vector similarity threshold |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `700` / `80` | Sentence-aware chunking |
| `RATE_LIMIT_GENERATE` / `RATE_LIMIT_UPLOAD` | `20` / `30` | Per-hour, per-client, per-process limits |
| `TRUSTED_PROXIES` | empty | Comma-separated proxy IPs allowed to set `X-Forwarded-For` for rate limiting; otherwise `request.remote_addr` is used |

Subjects, levels and source-type labels are defined in `Config` (`SUBJECTS`, `LEVELS`, `SOURCE_TYPES`) — not in the environment.

## Pages and API

Server-rendered pages (Arabic UI, `dir="rtl"`):

| Path | Purpose |
|---|---|
| `/` | Teacher dashboard: counts, subject mix, activity, recent lessons/documents |
| `/create` | Lesson request form and document selection |
| `/library` | Saved lesson sheets with search/filters/pagination |
| `/lessons/<id>`, `/lessons/<id>/print` | Lesson detail; print-optimized sheet |
| `/documents`, `/documents/<id>` | Knowledge base and document/chunk detail |
| `/settings` | Live diagnostics (models, keys, index, limits) |
| `/about`, `/healthz`, `/readyz` | About page, liveness, readiness |

JSON APIs:

| Endpoint | Method | Notes |
|---|---|---|
| `/api/lessons/generate` | POST | Full pipeline; rate-limited |
| `/api/lessons`, `/api/lessons/<id>` | GET | List / read (with `content`) |
| `/api/lessons/<id>` | DELETE | Delete lesson |
| `/api/lessons/<id>/duplicate` | POST | Clone lesson and its exercises |
| `/api/lessons/<id>/export.docx` | GET | RTL DOCX download |
| `/api/lessons/validate`, `/api/lessons/health` | POST, GET | Rubric check / service health |
| `/api/documents/upload` | POST | Multipart `file` + metadata; dedupe by SHA-256 |
| `/api/documents`, `/api/documents/<id>` | GET, DELETE | List / read / delete |
| `/api/documents/<id>/reindex` | POST | Rebuild the document's vectors |
| `/api/documents/retrieve` | GET | Inspect retrieval results (`retriever: vector\|lexical`) |
| `/api/lessons/<id>/exercises`, `/api/exercises/generate`, `/api/exercises/<id>` | POST/GET/DELETE | Exercise generation and management |
| `/api/lessons/<id>/assessments`, `/api/assessments/generate` | POST/GET | Assessment generation |

Examples (no auth; curl requests without an `Origin`/`Referer` header pass the same-origin guard):

```bash
# Generate a lesson (returns lesson_id, lesson_plan, quality, validation_errors)
curl -s http://localhost:5000/api/lessons/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "subject": "الإيقاظ العلمي",
    "educational_level": "السنة الخامسة ابتدائي",
    "topic": "دورة الماء في الطبيعة",
    "duration": 45,
    "difficulty": "متوسط",
    "language": "ar",
    "objectives": ["يتعرّف المتعلّم على مراحل دورة الماء", "يفسّر التكاثف"],
    "use_documents": true
  }'
```

```bash
# Add a reference document (PDF/DOCX/TXT; requires a Gemini key for embeddings)
curl -s -F 'file=@manual.pdf' \
  -F 'source_type=official' \
  -F 'subject=الإيقاظ العلمي' \
  -F 'educational_level=السنة الخامسة ابتدائي' \
  http://localhost:5000/api/documents/upload

# Inspect what retrieval would pass to the model
curl -s 'http://localhost:5000/api/documents/retrieve?topic=دورة%20الماء&n_results=5'

# Generate exercises for a saved lesson
curl -s -X POST http://localhost:5000/api/lessons/1/exercises \
  -H 'Content-Type: application/json' -d '{"count": 8, "difficulty": "متدرج"}'
```

Generation and validation responses keep `success`, `error` (on failure) and `validation_errors` for compatibility with the root-level manual scripts. Typed errors add `code` (and sometimes `details`), for example:

```json
{"success": false, "error": "الجذاذة غير موجودة.", "code": "not_found"}
```

Semantic details — including one-pass JSON repair on parse/schema failure, source fencing, duration normalization, and generation telemetry — are in [`ARCHITECTURE.md`](ARCHITECTURE.md). User-facing behavior is in [`PRODUCT.md`](PRODUCT.md); the visual system is in [`DESIGN.md`](DESIGN.md).

## Testing and code quality

`pytest` and `ruff` are development tools and are **not** in `requirements.txt`:

```bash
pip install -r requirements-dev.txt   # or: pip install pytest ruff
ruff check .
pytest
```

> **Note:** the root-level `test_*.py` files are standalone manual scripts (they execute API calls at import time), not pytest test functions. `pytest` will collect/import them, so treat them as manual probes (for example `python test_api.py` with the server configured) until a real pytest suite is added. Additional probes live in `scripts/test_*.py`. `python scripts/verify_truth.py` checks that documentation claims match the code.

Quick smoke checks that need no AI key:

```bash
curl http://localhost:5000/healthz
curl -i http://localhost:5000/readyz      # 503 until GEMINI_API_KEY is set
python scripts/seed_demo.py
```

## Troubleshooting

| Symptom / message | What to do |
|---|---|
| `لم يتم إعداد مفتاح Gemini بعد...` / `not_configured`, `/readyz` = 503 | Add a real `GEMINI_API_KEY` to `.env` and restart. Placeholder values are ignored. |
| `مفتاح Gemini غير صالح` (`invalid_api_key`) | Check the key, then try `GEMINI_API_KEY_1` for rotation. |
| `النموذج المطلوب غير متاح لهذا المفتاح` (`invalid_model`) | Set `GEMINI_MODEL=gemini-2.5-flash` (or `gemini-2.0-flash`); unavailable models are skipped automatically. |
| `تم بلوغ الحد الأقصى لاستخدام Gemini مؤقتاً` (`quota_exceeded`) | Wait, or add another key; generation and uploads are also rate-limited per hour. |
| Retrieval returns `retriever: lexical` | No embedding key or no vector hits. This is the intended transparent fallback; check `GEMINI_EMBEDDING_MODEL` in `/settings`. |
| `لا يمكن فهرسة الوثائق دون مفتاح Gemini` on upload | New documents need real embeddings; the mock provider is for tests only. Existing chunks can still be searched lexically. |
| `صيغة غير مدعومة` / `حجم الملف يتجاوز الحد المسموح` | Use PDF, DOCX or TXT up to 25 MB (also enforced independently by extraction). |
| Scanned PDF yields `لا يحتوي نصاً قابل للاستخراج` | The app extracts text layers only; OCR is not implemented. |
| Empty library after a fresh install | Run `python scripts/seed_demo.py` for sample lessons. |
| Stale static assets after an upgrade | Static URLs are versioned with `APP_VERSION`; hard-refresh the browser. |

## Security & deployment assumptions

- This is a single-teacher, no-auth, no-session application for local/private use. Do not expose it to an untrusted public network without adding authentication and a reverse proxy.
- The write-request origin check runs only when the browser sends `Origin`/`Referer`; non-browser clients are not CSRF-protected. This is acceptable only because there are no accounts, cookies, or sessions.
- `SECRET_KEY` is required outside tests. Set a long random value in `.env` (for example, `SECRET_KEY=<random>`; generate one with `python -c "import secrets; print(secrets.token_hex(32))"`). Missing or placeholder values fail fast at startup.
- `X-Forwarded-For` is honoured for rate limiting only when the client IP is listed in `TRUSTED_PROXIES` (comma-separated). Otherwise the limiter keys on `request.remote_addr`. If deploying behind a proxy, set `TRUSTED_PROXIES` to the proxy address.
- `/settings` intentionally shows local filesystem paths for support; keep it private.
- Generated pedagogical content must be reviewed by the teacher before classroom use; no pupil data is stored.

## Limitations and safety

- **Teachers must review every generated lesson.** Gemini can produce inaccurate science, wrong page numbers, or unsuitable activities. The rubric and `validation_errors` are aids, not guarantees. Content with hard validation errors is saved with status `review`.
- **No pupil data.** The app stores teacher-uploaded reference documents and generated lesson content only. Do not enter pupil names, results, or identifying information. There is no user account system, so anyone who can reach the server can read and delete all records.
- **No OCR, no web crawling, no background jobs.** Extraction supports PDF/DOCX/TXT text layers; `web` source type is metadata only. Generation is synchronous.
- **No mock vectors in normal operation.** Without an embedding key, retrieval degrades to lexical SQLite search, and uploads are refused with an explicit Arabic error.
- **Local, in-process rate limiting** resets on restart and is per worker; put the app behind a proxy if exposure beyond localhost is needed.
- **SQLite is the source of truth; Chroma is rebuildable.** Deletion order is Chroma → DB → file. Use `/api/documents/<id>/reindex` if the vector index drifts.
- No authentication, multi-tenancy, Alembic migrations, or SPA frontend. The `User` and legacy `Assessment`/`GenerationRequest` tables exist for compatibility and are not wired into the UI.

## Documentation map

| File | What it covers |
|---|---|
| `README.md` | Setup, configuration, endpoints, operations |
| `ARCHITECTURE.md` | Components, pipelines, data model, security, extension points |
| `PRODUCT.md` | Teacher workflow, 21-section contract, five-phase spine, quality gates |
| `DESIGN.md` | Design tokens, components, RTL/print, motion, accessibility |
| `PROJECT_SPEC.md` | Original French product specification (historical; partially stale) |
