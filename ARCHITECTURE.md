# Architecture — Pedagogical AI

> Implementation reference for app version **3.1.2** (`APP_VERSION` in `app/__init__.py`).
> Written in English; user-facing strings are Arabic. For the teacher-facing
> behaviour see [`PRODUCT.md`](PRODUCT.md), for the UI see [`DESIGN.md`](DESIGN.md).

## 1. Scope and non-goals

The application is a single-process, server-rendered Flask workspace for preparing Arabic lesson sheets.

| In scope | Deliberately absent |
|---|---|
| Flask app factory + Blueprints, Jinja templates | Authentication / multi-tenancy (the `User` model is reserved) |
| SQLite via Flask-SQLAlchemy; idempotent additive SQL migrations | Alembic, PostgreSQL-specific code |
| ChromaDB vector index with SQLite chunk text as source of truth | Redis, Celery, background workers |
| Gemini SDK for generation and embeddings | Local LLM, mock vectors in normal operation |
| Server-rendered RTL pages + vanilla JS bound via `data-*` | SPA framework, Bootstrap, jQuery |
| Browser print CSS and python-docx export | PDF rendering service |

Generation is synchronous: a request to `/api/lessons/generate` owns the whole pipeline and returns when persistence is complete.

## 2. Technology map

| Concern | Implementation |
|---|---|
| Web | Flask 2.3.3, Jinja2, Blueprints in `app/routes/` |
| Persistence | Flask-SQLAlchemy 3.0.5, SQLite (`instance/app.db` by default) |
| Schema evolution | `app/migrations.py`: `db.create_all()` + guarded `ALTER TABLE … ADD COLUMN` + `CREATE INDEX IF NOT EXISTS` |
| Vector store | `chromadb` `PersistentClient`, collection `pedagogical_documents`, cosine space |
| Generation | `google-genai` via `GeminiProvider`; JSON via `response_mime_type=application/json` (**no `response_schema`**) |
| Embeddings | `GeminiEmbeddingProvider` (`text-embedding-004` default) behind `EmbeddingService` |
| Validation | Pydantic v2 schemas + `ValidationService` pedagogical rubric |
| Frontend | `static/css/app.css` (hand-written RTL tokens/components), `static/js/*.js`, inline SVG sprite |
| Exports | Browser print stylesheet and `python-docx` (`export_service.build_lesson_docx`) |
| Operations | `/healthz`, `/readyz`, in-process hourly rate limiter, `GenerationRun` telemetry |

## 3. Layout

```text
config.py                  all environment reads (dotenv loaded at import)
run.py                     development entry point: create_app().run(debug=True)
app/
  __init__.py              create_app(), db, template filters, nav globals, versioned static URLs
  migrations.py            idempotent additive SQLite migrations
  errors.py                ApiError, JSON/HTML error handlers, security headers, origin guard
  models/model.py          Document, DocumentChunk, Lesson, Exercise, GenerationRun (+ legacy tables)
  ai/
    schemas.py             21-section LessonPlan, Phase spine, GenerationRequest/Response
    prompts.py             Arabic system prompt, JSON contract, source fencing, repair prompt
    gemini_provider.py     key/model fallback, error classification, Arabic error messages
    embeddings.py          Gemini embedding provider; test-only mock provider
    exercise_schemas.py / exercise_prompts.py
    assessment_schemas.py / assessment_prompts.py
  routes/
    main.py                pages + health/readiness/settings diagnostics
    lessons.py             generation, library APIs, validation, DOCX export
    documents.py           upload/list/delete/reindex/retrieve
    exercises.py           exercise generation + persistence
    assessments.py         assessment generation + persistence
  services/
    lesson_generation_service.py   retrieve → prompt → generate → repair → validate → persist
    retrieval_service.py           vector-first with lexical SQLite fallback
    document_service.py            checksum dedupe → extract → chunk → embed → index
    extraction_service.py          PDF/DOCX/TXT validation and text extraction
    chunking_service.py            sentence-aligned chunks with overlap
    embedding_service.py           provider facade (no mock by default)
    chroma_db.py                   defensive Chroma wrapper; rebuildable index
    validation_service.py          11-check rubric and hard-error/warning split
    lesson_service.py              CRUD, serialization, assessment mirroring
    export_service.py              RTL DOCX builder
    analytics_service.py           dashboard aggregates
    exercise_generation_service.py / assessment_generation_service.py
  utils/text.py            Arabic normalization, JSON extraction, duration scaling
  utils/rate_limit.py      per-process rolling one-hour limiter
templates/                 Jinja pages (base.html sets lang="ar" dir="rtl")
static/css/app.css         design tokens and components; static/css/style.css is legacy/unused
static/js/                 app.js, create.js, lesson.js — CSP-safe data-* hooks
scripts/seed_demo.py       demo lessons; safe to re-run, --reset supported
```

## 4. Boot sequence

`create_app()` (`app/__init__.py`) does the following, in order:

1. Load config from `Config` (or `TestConfig`), set `APP_VERSION`, create upload/export/Chroma/instance directories.
2. Initialise SQLAlchemy, import models.
3. Run `run_migrations()` inside the app context — `db.create_all()`, then SQLite-only additive columns/indexes and `PRAGMA user_version = 1`.
4. Register the five blueprints: main, documents, lessons, exercises, assessments.
5. Register template filters (`ar_date`, `minutes`, `short`), context globals (nav, subjects, levels, `ai_configured`, version) and the cache-busting `static_url()` helper.
6. Register error handlers and security middleware (`app/errors.py`).
7. Fail fast in non-testing mode when `SECRET_KEY` is missing or a placeholder; log a warning when no Gemini key is configured.

`run.py` calls `app.run(debug=True)` for local development; behind Gunicorn, use `gunicorn "app:create_app()"`, where `FLASK_DEBUG` from config applies.

## 5. Data model

Stored in `app/models/model.py`; scalar columns on lessons/documents exist for list, filter and analytics queries, while the full 21-section sheet lives in one JSON document (`Lesson.content`).

| Table | Role / key columns |
|---|---|
| `documents` | source file metadata, SHA-256 `checksum` (dedupe), `status` (`processing`/`ready`/`failed`), `chunk_count`, `error_message` |
| `document_chunks` | `chunk_id` (unique hash), `chunk_index`, text, page/subject/level/language metadata; SQLite is the source of truth for chunk text |
| `lessons` | list fields plus `content` (JSON `LessonPlan`), `status` (`ready`/`review`), `model_used`, `retrieved_context_count`, `duration_coherent`, validation arrays, `source_document_ids` |
| `exercises` | one row per exercise or assessment item; `kind` separates them, `payload` holds block/points metadata |
| `generation_runs` | telemetry: `kind`, `request`, `status` (`running`/`ok`/`error`), `error_code`, `model_used`, `latency_ms`, `retrieved_context_count` |
| `users`, `assessments`, `generation_requests` | legacy/reserved tables kept so older databases keep opening; not used by the current UI |

Migrations never drop columns. Additive changes belong in `COLUMNS`/`INDEXES` in `app/migrations.py`; there is no Alembic history.

## 6. Routes and response conventions

Pages are rendered with Jinja; API errors are JSON. `ApiError` produces:

```json
{"success": false, "error": "الجذاذة غير موجودة.", "code": "not_found"}
```

Generation/validation endpoints also always expose `success`, `error` (on failure) and `validation_errors`, plus `validation_warnings`, `quality`, and `redirect_url` where relevant — this keeps the root-level manual scripts working. Error handlers for 400/404/413/429/500 return JSON for `/api/*` and HTML templates for pages.

`GET /readyz` returns 503 if the database check fails or Gemini is not configured; the Chroma health result is reported but does not alone make the service unready. `GET /healthz` is always 200 with a UTC timestamp.

## 7. Lesson generation pipeline

`LessonGenerationService.generate()` (`app/services/lesson_generation_service.py`):

1. **Telemetry start** — insert a `GenerationRun(kind="lesson", status="running")`.
2. **Capability check** — if no keys are configured, fail with `not_configured` and the Arabic setup message; `/api/lessons/generate` maps this to **503**.
3. **Retrieve** — `RetrievalService.retrieve(topic, subject, level, language, n_results=6, document_ids=…)`. Retrieval failures are logged and treated as "no sources" rather than aborting generation. `use_documents=false` skips this step.
4. **Prompt** — `build_lesson_generation_prompt()` injects the subject/level/topic/duration/difficulty/objectives, the JSON contract, and fenced `<sources>…</sources>` blocks (`S1`, `S2`, … with filename, page, source type). The prompt explicitly says the fenced content is data, not instructions.
5. **Generate** — `GeminiProvider.generate(..., json_mode=True)` uses `response_mime_type=application/json`, tries every configured key/model combination in order, skips invalid models, and classifies failures (`quota_exceeded`, `invalid_api_key`, `invalid_model`, `network_error`, `server_error`, …). API failures map to **502**.
6. **Parse** — `extract_json()` accepts plain JSON, fenced JSON, or the first balanced object from surrounding prose. If parsing fails, exactly **one repair call** is made via `build_repair_prompt()`.
7. **Validate schema** — `LessonPlan(**payload)` (Pydantic, `extra="ignore"`). If this fails, one repair call is attempted; a second failure raises `invalid_json`.
8. **Normalize durations** — `LessonPlan.normalize_durations()` rescales phase minutes with largest-remainder rounding so their sum equals the requested `duration` exactly, keeping every phase ≥ 1 minute. Coherence is then recomputed with a 2% tolerance.
9. **Validate pedagogy** — `ValidationService.validate_lesson_plan()` runs the 11-check rubric (hard errors vs warnings) and produces a 0–100 score.
10. **Persist** — `LessonService.create_from_plan()` writes the lesson, mirrors formative/summative items into `exercises` (`kind="assessment"`), and sets `status = "ready"` only when there are no hard errors, otherwise `"review"`.
11. **Finish telemetry** — update the run with `status`, `model_used`, `lesson_id`, `latency_ms`, and context count; return `GenerationResponse` with the plan, errors, warnings, quality rubric and `redirect_url`.

The five-phase spine is `التمهيد → وضعية الانطلاق → بناء التعلمات → التقويم → الخلاصة` (`PHASE_SPINE`). Every phase is an object with a name, `phase_key`, integer `duration`, teacher/learner actions, guiding questions, expected responses and activities. The rubric warns when the spine is incomplete and hard-fails when no timed phases exist. See [`PRODUCT.md`](PRODUCT.md#the-five-phase-session-spine) for the teacher-facing contract.

## 8. Gemini provider details

- Keys: `GEMINI_API_KEY`, then `GEMINI_API_KEY_1`…`_5`; models: `GEMINI_MODEL`, then `GEMINI_MODEL_1`…`_3`, defaulting to `gemini-2.5-flash`, `gemini-2.0-flash`. The Cartesian product of keys × models is the fallback chain.
- `HttpOptions` timeout is applied when supported by the installed SDK; `GenerateContentConfig` carries temperature, max output tokens, the system instruction, and JSON mime type. No schema is passed to Gemini — structure is enforced locally by Pydantic.
- All failures carry an Arabic message suitable for direct display (see `ARABIC_ERRORS`). Empty responses are retried with the next configuration; malformed requests abort immediately.
- Embeddings rotate keys independently (`GeminiEmbeddingProvider`) and use `RETRIEVAL_DOCUMENT` for chunks, `RETRIEVAL_QUERY` for queries.

## 9. Retrieval and document lifecycle

**Ingestion** (`POST /api/documents/upload` → `DocumentService.ingest`):

1. Validate extension (`.pdf`, `.docx`, `.txt`) and size; save under a sanitized name with a UUID suffix.
2. Compute SHA-256; an existing checksum returns `duplicate: true` (200) and the saved file is removed.
3. Extract text per page (PyMuPDF / python-docx / TXT with UTF-8, CP1256, Latin-1 fallbacks). No OCR.
4. Create `Document(status="processing")`, chunk per page (`CHUNK_SIZE`, `CHUNK_OVERLAP`, sentence boundaries), embed the batch with Gemini, add `DocumentChunk` rows, upsert vectors into Chroma, then set `status="ready"`. Failures roll back the DB and set `status="failed"` with an Arabic `error_message`.
5. Metadata recorded on each chunk: `document_id`, `filename`, `source_type`, `subject`, `educational_level`, `language`, `chapter`, `page_number`.

Embeddings are mandatory for ingestion: without a key, `EmbeddingService.require()` raises the Arabic message `لا يمكن فهرسة الوثائق دون مفتاح Gemini…`. `MockEmbeddingProvider` exists only for tests and is never selected by default.

**Deletion order:** Chroma (`delete_document`) → DB row (cascading chunks) → file on disk. **Reindex** (`POST /api/documents/<id>/reindex`) re-embeds the stored chunks, deletes the old vector entries, upserts the new ones and marks the document ready.

**Retrieval** (`RetrievalService.retrieve`): vector search first with metadata filters (`subject`, `educational_level`, `language`, `document_id IN …`), threshold `RAG_MIN_SIMILARITY`; results are tagged `retriever: "vector"` and similarity = 1 − cosine distance. When embeddings are unavailable, embedding fails, vector search fails, or fewer than `limit` hits are found, a **transparent lexical fallback** scores normalized Arabic token overlap over `DocumentChunk` rows in SQLite, tags results `retriever: "lexical"`, and merges/de-duplicates them up to the limit. There is no fake vector fallback. The UI and `/api/documents/retrieve` expose which retriever was used.

## 10. Validation, exercises and assessments

`ValidationService` checks identity, Arabic ratio (≥ 0.6), operational-verb objectives, prerequisites/materials, five-phase spine, both actor perspectives, duration coherence (±2 min), formative + summative blocks, experiment safety keyword scan, closure, and source attribution. Hard errors (identity, Arabic, no timed phases, unsafe activity) set `valid = false`; other failures become warnings. `/api/lessons/validate` exposes the rubric without persisting.

Exercise and assessment generation reuse `GeminiProvider` with their own Arabic prompts/Pydantic schemas. `/api/lessons/<id>/exercises` **replaces** the lesson's existing `kind="exercise"` rows; `/api/lessons/<id>/assessments` and lesson generation replace `kind="assessment"` rows. Exercise content is constrained by prompt to concepts from the saved lesson plan. Standalone `/api/exercises/generate` and `/api/assessments/generate` return data without persistence. All generation endpoints are rate-limited with the `generate` bucket.

## 11. Exports

- **Print**: `/lessons/<id>/print` renders `templates/lesson_print.html`; `@media print` in `static/css/app.css` switches to A4, hides navigation/controls, forces black-on-white, avoids breaking phases/assessment items, and disables reveal animation.
- **DOCX**: `GET /api/lessons/<id>/export.docx` → `build_lesson_docx(plan)` using python-docx with RTL paragraph properties (`w:bidi`, `w:rtl`), Arial 11pt, bullet lists and Arabic section headings. Missing `python-docx` surfaces as `export_unavailable` (503).

## 12. Security and operational limits

- `register_security()` sets `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, a strict CSP (`script-src 'self'`, no inline scripts), HSTS outside debug, and a same-origin check for writes based on `Origin`/`Referer`.
- No authentication or CSRF tokens: the origin guard is the only write protection. Deploy on localhost/trusted network only.
- `rate_limit()` is an in-process deque per `(bucket, client address)` with a rolling one-hour window; no Redis, resets on restart, and effectively per worker. The client address is `request.remote_addr` unless the peer proxy is listed in `TRUSTED_PROXIES`. `TESTING` bypasses it.
- `MAX_CONTENT_LENGTH` comes from `MAX_UPLOAD_MB`; the extraction service repeats the 25 MB check independently.
- Uploaded filenames are sanitized; stored filenames get a UUID suffix; uploads are never executed or served as HTML.

### Security & deployment assumptions

- Single-teacher, no-auth, no-session local/private use; do not expose to an untrusted public network without adding authentication and a reverse proxy.
- The origin check runs only when the browser sends `Origin`/`Referer`; non-browser clients are not CSRF-protected. This is acceptable only because there are no accounts, cookies, or sessions.
- `SECRET_KEY` is required outside tests; set a long random value in `.env`. Missing or placeholder values fail fast at startup.
- `X-Forwarded-For` is honoured for rate limiting only when the client IP is in `TRUSTED_PROXIES` (comma-separated); otherwise the limiter uses `request.remote_addr`. Behind a proxy, set `TRUSTED_PROXIES` to the proxy address.
- `/settings` intentionally shows local filesystem paths for support; keep it private.
- Generated pedagogical content must be reviewed by the teacher before classroom use; no pupil data is stored.

## 13. Telemetry and dashboard

Every lesson generation attempt writes a `GenerationRun` row. `AnalyticsService` aggregates lesson/document/chunk/exercise/assessment counts, weekly run count, success rate and mean latency, subject/level breakdowns, recent items and a daily activity series for `/`. `/settings` shows current config, key/model counts, retrieval stats and Chroma health. No telemetry leaves the machine.

## 14. Extension points

| To change… | Start here |
|---|---|
| Prompt wording, source fencing, JSON contract | `app/ai/prompts.py` |
| Output structure / section labels | `app/ai/schemas.py` (`SECTION_LABELS`, `LessonPlan`) |
| Pedagogical checks or scoring | `app/services/validation_service.py` |
| Provider or embedding vendor | `app/ai/gemini_provider.py`, `app/ai/embeddings.py`, `EmbeddingService` |
| Ranking strategy | `app/services/retrieval_service.py`, `app/services/chroma_db.py` |
| Storage schema | `app/models/model.py` + an additive entry in `app/migrations.py` |
| Visual language | `static/css/app.css` tokens (see `DESIGN.md`) |

## 15. Known implementation notes

- `PROJECT_SPEC.md` and parts of the old docs describe a v2 plan (French UI, Bootstrap, `rag/` folder); the shipped app is Arabic-first, framework-free, and uses `app/ai/` + `app/services/`.
- `pyproject.toml` declares version `0.1.0` while the app reports `3.1.2`; packaging metadata has not caught up.
- `MAX_UPLOAD_MB` can be raised above 25, but `ExtractionService.MAX_FILE_SIZE` still rejects files over 25 MB.
- Root-level `test_*.py` files are manual scripts, not pytest tests; they hit APIs at import time.
- `static/css/style.css` is a leftover sidebar stylesheet; active pages load only `static/css/app.css`.
