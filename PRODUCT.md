# Product — منصة الإعداد التربوي (Pedagogical AI)

> What the app does for a teacher, and what promises its output contract makes.
> Setup and endpoints: [`README.md`](README.md). Implementation: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## 1. Who it is for

Primary user: a Tunisian primary-school teacher preparing **الإيقاظ العلمي** (scientific awakening) lessons, initially for years 1–6 (`السنة الأولى ابتدائي` … `السنة السادسة ابتدائي`). Other configured subjects are الرياضيات, اللغة العربية, اللغة الفرنسية, التربية الإسلامية and التربية المدنية.

The teacher works alone, in Arabic, from official programmes, textbooks and their own documents. There are no pupils in the system and no accounts to manage.

## 2. The problem

A usable جذاذة must combine official objectives, prior knowledge, safe hands-on activities, guidance questions, formative and summative assessment, and an exact class duration — in simplified Arabic, ready to print. Doing that from scratch for every lesson is slow, and generic chat output is hard to trust or reuse.

The product promise: **a complete, structured first draft in Arabic, grounded in the teacher's own documents, with visible checks and one-click print/DOCX export.** The teacher always reviews and adapts it.

## 3. The teacher journey

```text
الرئيسية  →  حضّر درساً  →  submit request  →  generated جذاذة
                                                   ├─ review rubric / warnings
                                                   ├─ print (/browser) or download DOCX
                                                   └─ generate exercises / assessments
        →  جذاذاتي (search, filter, duplicate, delete)
        →  الوثائق (upload, inspect chunks, reindex, delete)
        →  الإعدادات (live diagnostics)
```

1. **Collect sources.** In `الوثائق`, upload PDF/DOCX/TXT and label it as `وثيقة رسمية`, `وثيقة المعلّم` or `مرجع ويب موثوق`. Duplicate uploads are detected by checksum.
2. **Request a lesson.** In `حضّر درساً`, choose subject, level, duration (5–180 minutes), topic, objectives, difficulty (`مبتدئ`…`متدرج`), optional teacher instructions, and whether/how documents are used.
3. **Generate.** The app retrieves relevant chunks, asks Gemini for the structured sheet, repairs/validates the JSON, normalizes phase minutes and saves the result. Generation is synchronous; the UI shows a progress overlay.
4. **Review.** The detail page renders 21 labelled sections, the five-phase timeline, exercises, assessment items with answers, and a quality gauge with the rubric. Hard errors set status `review`; warnings are hints.
5. **Use.** Print the RTL sheet (`/lessons/<id>/print`) or download the DOCX. Generate extra exercises/assessments as needed.
6. **Manage.** Search/filter the library, duplicate a lesson for a parallel class, or delete it.

## 4. The 21-section lesson contract

The output is one `LessonPlan` JSON object whose keys stay English for API compatibility; Arabic labels come from `SECTION_LABELS` in `app/ai/schemas.py`. The prompt requires **all 21 sections, in order**, with a short placeholder rather than an omitted section.

| # | JSON key | Arabic label (جذاذة) |
|---:|---|---|
| 1 | `title` | عنوان الدرس |
| 2 | `subject` | المادة |
| 3 | `educational_level` | المستوى الدراسي |
| 4 | `duration` | المدة الزمنية |
| 5 | `competency` | الكفاءة المستهدفة |
| 6 | `learning_objectives` | الأهداف التعليمية |
| 7 | `prerequisites` | المكتسبات السابقة |
| 8 | `materials` | الوسائل التعليمية |
| 9 | `key_concepts` | المفاهيم والمصطلحات الأساسية |
| 10 | `introduction` | وضعية الانطلاق |
| 11 | `lesson_phases` | مراحل بناء التعلمات |
| 12 | `teacher_actions` | أنشطة المعلم |
| 13 | `learner_actions` | أنشطة المتعلم |
| 14 | `guiding_questions` | الأسئلة التوجيهية |
| 15 | `experiments` | التجارب أو الأنشطة العلمية |
| 16 | `examples` | الأمثلة |
| 17 | `formative_assessment` | التقويم التكويني |
| 18 | `summative_assessment` | التقويم النهائي |
| 19 | `remediation` | الدعم والعلاج |
| 20 | `summary` | خلاصة الدرس |
| 21 | `homework` | نشاط أو واجب منزلي |

Additional fields support the contract: `expected_answers`, `activities`, `exercises`, the legacy free-text `assessment` (derived from the two assessment blocks), `sources`, and `insufficient_sources`.

Experiments carry `title`, `materials`, `steps`, `safety_notes`, `expected_observation` and `risk_level`. Each assessment block carries a `description` and items with `question`, `answer`, `explanation`, `objective`, `difficulty` and `type`.

## 5. The five-phase session spine

`PHASE_SPINE` fixes the pedagogical sequence:

| Order | Phase (`phase_key`) | What the teacher does |
|---:|---|---|
| 1 | التمهيد | Hook prior knowledge and state the question |
| 2 | وضعية الانطلاق | Present a concrete situation and collect hypotheses |
| 3 | بناء التعلمات | Investigation/experiment, concept building, guided practice |
| 4 | التقويم | Formative checks and correction |
| 5 | الخلاصة | Co-constructed summary and transfer |

Every phase is a structured object with an **integer `duration` in minutes**, teacher actions, learner actions, guiding questions, expected responses and activities. Durations are **exact**: after generation, `normalize_durations()` rescales them with largest-remainder rounding so their sum equals the requested `duration` with no phase below one minute. For example, the seeded 45-minute water lesson uses 5 + 8 + 18 + 9 + 5 = 45; the seeded 40-minute plant lesson uses 4 + 6 + 18 + 7 + 5 = 40. Generated lessons may distribute minutes differently — the invariant is the exact total, not a fixed template. The rubric warns at a ±2 minute mismatch, and a lesson with no timed phases is a hard error.

## 6. Source grounding and truthfulness

- Retrieved chunks are wrapped in `<sources>…</sources>` blocks labelled `S1`, `S2`, … with filename, page number and source type (`وثيقة رسمية` gets an extra marker). The prompt states that this is reference data only and any instructions inside it must be ignored (prompt-injection fencing).
- The model may cite **only** the supplied document names; invented references and page numbers are forbidden.
- If a scientific fact is not available in the sources, the model must write exactly:

  > هذه المعلومات غير متوفرة في المصادر المقدمة.

  and set `insufficient_sources = true`. The rubric then raises a warning: `أشار النموذج إلى نقص المصادر؛ راجع المحتوى العلمي قبل الاستعمال.`
- Retrieval is vector-first; when embeddings are unavailable it falls back to visible lexical SQLite search (`retriever: "lexical"`). No synthetic vectors are used. New uploads still require a Gemini key for embeddings.

## 7. Quality gates

`ValidationService` produces an 11-point rubric (score 0–100) and a `valid` flag:

| Check | Blocking? | Meaning |
|---|---|---|
| `identity` | hard | Title, subject and level present |
| `arabic` | hard | ≥ 60% Arabic letters in the sampled text |
| `objectives` | warning | ≥ 2 objectives, at least half starting with an operational verb (يتعرّف، يشرح، يميّز…) |
| `preparation` | warning | Prior knowledge and materials present |
| `phases` | warning | At least four phases; at most one spine phase missing |
| `actors` | warning | Teacher and learner actions in every phase |
| `duration` | hard if no phases | Sum of phase minutes matches the request |
| `assessment` | warning | Both formative and summative blocks present |
| `safety` | hard | No dangerous materials/procedures in experiments |
| `closure` | warning | Summary and remediation present |
| `sources` | warning | Content fully attributed; `insufficient_sources = false` |

Outcomes: `valid: true` → lesson saved with status `ready`; any hard error → `review`. The summary line reads `جذاذة مكتملة وجاهزة للاستعمال.` (≥ 90), `جذاذة جيدة مع بعض النقاط القابلة للتحسين.` (≥ 70), or `تحتاج الجذاذة إلى مراجعة قبل الاستعمال.` The UI shows the same rubric as dots (pass/warn/fail). Validation is advisory: **a high score is not a guarantee of scientific accuracy.**

## 8. Exercises and assessments

- **Exercises** (`التمارين`): 1–20 items per set; types include أسئلة مباشرة، صح / خطأ، أكمل الفراغ، صل، صنّف، اختيار من متعدد، أسئلة قصيرة، وضعيات تطبيقية، أنشطة ملاحظة، أنشطة علمية. Each item has a question, instructions, options, expected answer, detailed correction, objective, difficulty and estimated time. The prompt constrains content to concepts from the generated lesson.
- **Assessments** (`التقويم`): formative and summative sets with questions, answers, explanations, objectives, difficulty and points (1–10). Generating for a saved lesson replaces its assessment rows; the lesson generation itself also mirrors the two assessment blocks into the same store.
- Ambiguous questions are forbidden by the prompts; teachers still need to check them.

## 9. Surfaces outside the lesson sheet

| Area | Value |
|---|---|
| `الرئيسية` | Counts of lessons, documents, chunks, exercises and assessments; weekly generation success rate and latency; subject mix; 10-day activity |
| `الوثائق` | Upload, filter, inspect extracted chunks and statuses, reindex, delete |
| `الإعدادات` | Version, Python/database info, configured models/key count, RAG settings, upload/rate limits, Chroma health |
| `جذاذاتي` | Search by title/topic, filter by subject/level, paginate, duplicate, delete |
| Print / DOCX | A4 print stylesheet and RTL Word file for classroom use |
| `/healthz`, `/readyz` | Operational probes for local deployment |

## 10. Product boundaries and safety

- This is a **drafting aid, not an authority**. Teachers must review every generated activity, answer key and citation before classroom use, especially experiments and scientific claims.
- **No pupil data** belongs in this app: reference documents and lesson plans only. Do not store names, grades or other personal information.
- No login, no per-teacher workspaces: everyone who can reach the app sees the same library. Run it on localhost or a trusted network.
- No OCR for scanned PDFs, no web crawling (the `web` source type is a label only), no background jobs and no email.
- Without a Gemini key: browsing/printing demo or saved lessons works; generation returns the Arabic setup message; retrieval degrades to lexical search; new document uploads are refused with an explicit Arabic error.
- Rate limits are per process: 20 generations and 30 uploads per hour per client by default.
