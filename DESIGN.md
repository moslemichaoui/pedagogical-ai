# Design — منصة الإعداد التربوي (Pedagogical AI)

> The visual system for the Arabic-first lesson-preparation app. Source of truth:
> `static/css/app.css` and `templates/base.html`. Product behaviour is in
> [`PRODUCT.md`](PRODUCT.md); implementation is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## 1. Design idea: «الدفتر الرسمي»

The interface borrows from a Tunisian teacher's official school notebook and classroom chalkboard: warm ruled paper, a dark green board, saffron action marks, and blue stamp accents. It should feel like a prepared, stamped document — not a generic SaaS dashboard.

Principles:

- **Arabic first.** Every page is `lang="ar" dir="rtl"`. Arabic typography and logical CSS properties come before LTR considerations.
- **Paper, not plastic.** Flat surfaces, hairline rules, and restrained low-lift shadows evoke ink and stamped paper; no glossy gradients or floating cards.
- **One accent for action.** Saffron marks the primary action and section markers; green is reserved for the board, success states, and data bars; stamp blue is for links and identity.
- **Content before chrome.** Headers, controls, and toasts get out of the way of the lesson sheet, which is the actual deliverable.
- **No framework.** `app.css` is hand-written; there is no Bootstrap/jQuery and no component library. JavaScript is vanilla and CSP-safe.

## 2. Tokens

Defined in `:root` in `static/css/app.css`. Use the variables, not raw hex values, when extending the UI.

| Group | Token | Value | Use |
|---|---|---|---|
| Surfaces | `--paper` | `#f7f2e6` | Page background (with subtle ruled/saffron/board gradients) |
| | `--paper-raised` | `#fdfaf2` | Cards, sheets, form surfaces |
| | `--paper-sunk` | `#efe7d6` | Headers of phases, inset areas |
| | `--paper-deep` | `#e6dcc7` | Tracks, skeletons, empty bars |
| Ink | `--ink` | `#17150f` | Primary text |
| | `--ink-soft` | `#4d4739` | Body/prose text |
| | `--ink-mute` | `#6b6353` | Hints, metadata |
| | `--ink-faint` | `#6f6656` | Decorative text only |
| Chalkboard | `--board` | `#10382b` | Header, hero, sheet head, primary data |
| | `--board-deep` | `#0a281e` | Borders, overlays |
| | `--board-light` | `#1c513d` | Hover/data gradient end |
| | `--board-ink` | `#eaf2e6` | Text on board |
| | `--board-mute` | `#cfe3d5` | Muted text on board |
| Accents | `--stamp` | `#1d4e89` | Links, focus ring, section numbers |
| | `--stamp-soft` | `#dde7f3` | Soft stamp tint |
| | `--saffron` | `#d9a13b` | Primary buttons, markers, active states, header rule |
| | `--saffron-deep` | `#a97722` | Button borders, bullet outlines |
| | `--saffron-soft` | `#f6e7c6` | Hover tint for dropzone |
| Status | `--red` / `--red-soft` | `#9c2f2f` / `#f3dddd` | Destructive actions, fail dots |
| | `--green-ok` / `--green-soft` | `#2c6b47` / `#dcecdd` | Success, answer keys, pass dots |
| Lines | `--line` / `--line-strong` | `#d8cdb8` / `#b9ab90` | Rules and borders |
| Typography | `--font-display` | Alexandria → IBM Plex Sans Arabic → system-ui | Headings, brand, phase names |
| | `--font-body` | IBM Plex Sans Arabic → Alexandria → system-ui | Body, buttons, form controls |
| | `--font-num` | Readex Pro → IBM Plex Sans Arabic → system-ui | Numbers, labels, badges |
| Metrics | `--radius` / `--radius-sm` / `--radius-lg` | `10px` / `6px` / `18px` | Cards / small controls / hero |
| | `--shell` | `1240px` | Max content width |
| | `--gutter` | `clamp(1rem, 3vw, 2.5rem)` | Page side space |
| | `--header-h` | `68px` | Sticky header height |
| Depth | `--shadow-stamp` | `0 8px 20px -14px rgba(23,21,15,.45)` | Cards |
| | `--shadow-lift` | `0 14px 34px -18px rgba(23,21,15,.55)` | Sheets, overlays, modals |
| | `--ring` | `0 0 0 3px rgba(29,78,137,.28)` | Focus halo |

Google Fonts are loaded in `base.html` with `preconnect`. The three Arabic families are intentional: display for headings, body for reading, Readex Pro for tabular numerals.

## 3. Component vocabulary

| Component | Classes / markup | Usage rule |
|---|---|---|
| Page shell | `.container`, `.page-head`, `.lede`, `.split`, `.stack`, `.row`, `.section-gap` | Every page starts with a page head; use `.split` for a primary column plus a supporting sidebar. |
| Header/nav | `.site-header`, `.brand`, `.main-nav`, `.nav-link`, `.ai-badge`, `.header-actions`, `.mobile-nav` | Sticky board-green header; the badge shows whether Gemini is configured. |
| Buttons | `.btn` + `--primary` / `--ink` / `--ghost` / `--danger`; `--sm` / `--lg` / `--block` / `--icon` | One `.btn--primary` per view. Destructive actions always use `--danger`. |
| Cards | `.card`, `.card--flush`, `.card--ink`, `.card--stamp`, `.card-head` | `.card--stamp` marks the main form/upload card; `.card--ink` is for tips and board-styled panels. |
| Section marker | `.marker` | Plain Arabic card headings; numbers are reserved for meaningful data, not decoration. |
| Hero (dashboard) | `.hero`, `.hero-grid`, `.hero-actions`, `.sheet-preview`, `.sheet-stamp` | Decorative preview is `aria-hidden`; hidden below 1000px. |
| Stats | `.stat-grid`, `.stat`, `.stat-label`, `.stat-value`, `.stat--accent` | Short counts and weekly generation summary. |
| Forms | `.form-grid`, `.field`, `.field--full`, `.field-label`, `.hint`, `.range-row`, `.segmented`, `.chip-check`, `.chip-set` | Labels always visible; segmented control is a `role="radiogroup"`; hints sit below the input. |
| Chips/badges | `.chip`, `.chip--stamp`, `.chip--ghost`, `.chip--ok`, `.chip--warn` | Compact metadata (subject, level, status, chunk count). |
| Lists/tables | `.list`, `.lesson-row`, `.bullets`, `.table-wrap`, `.filter-bar`, `.pagination` | `.bullets` uses a rotated saffron diamond instead of a default bullet. |
| Empty states | `.empty` | Explain what is missing and offer the next action. |
| Lesson cards | `.lesson-grid`, `.lesson-card` | Library entries with title, metadata, and row actions. |
| Lesson sheet | `.sheet`, `.sheet-head`, `.sheet-meta`, `.sheet-body`, `.section`, `.section-head`, `.prose` | The 21-section جذاذة. Section order follows `SECTION_LABELS`. |
| Phase timeline | `.phases`, `.phase`, `.phase-head`, `.phase-body`, `.phase-grid`, `.phase-col` | One block per five-phase spine item; teacher/learner columns side by side on wide screens. |
| Assessment | `.assess-item`, `.assess-q`, `.assess-a`, `.assess-e` | Question, green answer chip, muted explanation. |
| Quality | `.quality`, `.gauge`, `.rubric`, `.dot.pass/.warn/.fail` | 0–100 score gauge plus the 11 rubric checks. |
| Alerts/toasts | `.alert`, `.alert--info/--warn/--danger`, `.toast`, `.toast-region` | Toasts are announced via a polite live region; alerts stay in the page flow. |
| Loading | `.spinner`, `.progress`, `.skeleton`, `.gen-overlay`, `.gen-panel`, `.gen-steps` | Generation overlay shows four Arabic steps; it is a modal dialog and must never trap the page invisibly. |
| Modal | `.modal`, `.modal-card`, `.modal-actions` | Confirmation dialog for deletions; `[hidden]` is respected. |
| Upload | `.dropzone`, `[data-dropzone]`, `[data-file-name]` | The file input covers the whole dropzone with `opacity: 0`; the label is the visible target. |
| Tabs | `.tabs`, `.tab`, `.tab-panel` | Horizontal tabs scroll on narrow screens. |
| Footer | `.site-footer`, `.print-only` | `.print-only` content appears only in the printed sheet. |

## 4. RTL and typographic behavior

- `templates/base.html` sets `<html lang="ar" dir="rtl">`; all pages inherit it. The DOCX export applies `w:bidi`/`w:rtl` paragraph properties for the same reason.
- The stylesheet uses logical properties throughout: `margin-inline`, `padding-block`, `inset-inline-start`, `border-inline-start`, `text-align: start`, `border-block-end`. Do not introduce `left`/`right` for layout.
- Directional icons are inline SVG symbols (`<svg class="icon"><use href="#i-…"></use></svg>`) with `aria-hidden="true"`; chevrons are mirrored by meaning in markup, not by CSS hacks.
- Numbers use `.num` with Readex Pro and `font-variant-numeric: tabular-nums`, so Arabic text and Latin/digit counts align cleanly.
- Body text is 16px / line-height 1.75; headings use `clamp()` and `text-wrap: balance` for Arabic line breaking.

## 5. Motion and interaction rules

Motion is short, purpose-driven, and entirely optional.

| Effect | Rule |
|---|---|
| Button press | `transform` + shadow over `120ms`; disabled buttons do not move. |
| Data bars | `.bar-fill` width `700ms`, `.activity` bars `600ms`, `.progress` span `400ms` — easing `cubic-bezier(.22,1,.36,1)` for bars. |
| Toast entrance | `toast-in` `220ms ease`. |
| Spinner | `spin` `700ms linear infinite`. |
| Skeleton | `shimmer` `1.4s ease infinite`. |
| Overlay | `fade-in` `180ms ease`. |
| Page reveal | `.reveal` uses `reveal-in` `560ms cubic-bezier(.22,1,.36,1)`. It is pure CSS: no observer or script, so nothing can remain invisible if JavaScript fails. |
| Reduction | `@media (prefers-reduced-motion: reduce)` forces all animation/transition durations to `0.01ms`, one iteration, and disables `.reveal`. |

Never use motion to convey a state that is not also available as text (status chips, labels, rubric dots). The generation overlay is deliberately optimistic step animation; the response text remains authoritative.

## 6. Responsive behavior

| Breakpoint | Change |
|---|---|
| ≤ 1180px | Hide the Gemini status badge in the header. |
| ≤ 1000px | Collapse `.hero-grid`; hide the decorative sheet preview. |
| ≤ 980px | Hide `.main-nav`, show `.mobile-nav`, collapse header button labels, reserve bottom space for mobile navigation/toasts. |
| ≤ 900px | Collapse `.split` / `.split--even` to one column. |
| ≤ 560px | Reduce gutter and base font to 15px; two-column stats; one-column lesson grid and quality panel; fluid button rows. |

## 7. Print behavior

`/lessons/<id>/print` reuses `app.css`, whose `@media print` block switches to an official-document look:

- `@page { size: A4; margin: 14mm; }`; body becomes white, black, 11pt, with no paper texture.
- Hide `.site-header`, `.site-footer`, `.mobile-nav`, `.no-print`, `.toast-region`, and `.gen-overlay`; reset `main`/`.container` padding and width.
- `.sheet` loses border and shadow; `.sheet-head` becomes white with a black bottom rule and 18pt title; chips become neutral outlines.
- `break-inside: avoid` on `.section`, `.phase`, and `.assess-item` keeps logical blocks intact across pages.
- `.print-only` becomes visible; `.reveal` animations are disabled and opacity forced to 1.
- Links print as plain black text — no underlines or URL clutter.

Browser print is the primary export path. DOCX export preserves RTL text direction and the same section order for teachers who need to edit the sheet in Word.

## 8. Accessibility

- Skip link (`تجاوز إلى المحتوى`) targets `<main id="main" tabindex="-1">`.
- Semantic landmarks: header, nav with `aria-label`, main, footer; Arabic headings (`h1`–`h4`) follow document order.
- `:focus-visible` draws a 3px `--stamp` outline with 2px offset on all interactive elements.
- `.sr-only` hides text visually without hiding it from assistive technology.
- Toasts use `role="status"` inside an `aria-live="polite"` region; the confirm modal and generation overlay use `role="dialog"`, `aria-modal="true"`, and `aria-labelledby`.
- Form controls have labels or `aria-label` (including the segmented difficulty group and the file input); hint and error text are rendered in the DOM, not only as colour.
- The activity sparkline has `role="img"` with an Arabic `aria-label`; decorative icons and the dashboard sheet preview are `aria-hidden`.
- Status is never colour-only: chips and rubric dots are accompanied by text (`chip--ok`, `chip--warn`, `جاهز`, etc.).
- Reduced-motion and print modes are handled in CSS. Contrast follows the ink/paper and board/board-ink pairs; verify any new token combination with a contrast checker before shipping.
- No audio, autoplay, timed content, or keyboard shortcuts are required.

## 9. JavaScript contract

`static/js/app.js`, `create.js`, and `lesson.js` are plain ES5/2015-style scripts loaded from `static`. There are no inline scripts, and the CSP uses `script-src 'self'` (inline `style` attributes are allowed by the current `style-src` policy). Hooks are declarative `data-*` attributes so markup controls behaviour:

`data-confirm-yes/no`, `data-tabs` / `data-tab` / `data-panel`, `data-range`, `data-copy`, `data-dropzone` / `data-file-name`, `data-delete-url` / `data-row`, `data-fetch` / `data-form-error`, `data-print`, `data-generate-exercises`, `data-generate-assessments`.

Rules when adding interactions:

1. Prefer a `data-*` hook over an ID or generated class selector.
2. Update the visible text and ARIA state together (for example, active tab and panel visibility).
3. Keep the page usable without JavaScript: forms post to real Flask routes and links point to real pages.
4. Do not inject model-generated HTML; render Arabic content as text to avoid script injection.

## 10. Maintenance checklist

- Change colours/type only in the `:root` token block; keep print overrides in section 26.
- Add new components to this vocabulary table and use logical CSS properties.
- Test at 560px, 980px, and desktop widths, once with `prefers-reduced-motion: reduce`, and once with the browser print preview.
- Check keyboard focus order and the Arabic screen-reader reading order on every form and sheet view.
- Static URLs are versioned with `APP_VERSION`; bump the app version after visual changes so browsers refresh cached CSS/JS.

## 11. Detector waivers

The warm `--paper` surface and its faint ruled-line field are the core "official notebook" metaphor, not a generic beige default, so `cream-palette` is ignored in `.impeccable/config.json`. The repeating rule and dot-grid gradients are the paper texture itself; the detector's `repeating-stripes-gradient` and `codex-grid-background` advisories are acknowledged but retained deliberately. All other detector findings (kickers, section numbers, nested cards, contrast, heading order, and mobile text size) are treated as defects and fixed.
