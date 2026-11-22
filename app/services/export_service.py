"""Export a lesson sheet as a printable, right-to-left DOCX file."""
from __future__ import annotations

import io
from typing import Iterable, List

from app.ai.schemas import LessonPlan

FONT = "Arial"


def _rtl(paragraph) -> None:
    """Force right-to-left paragraph direction for Word."""
    from docx.oxml.ns import qn
    from docx.shared import Pt

    paragraph.alignment = 2  # WD_ALIGN_PARAGRAPH.RIGHT
    ppr = paragraph._p.get_or_add_pPr()
    bidi = ppr.find(qn("w:bidi"))
    if bidi is None:
        bidi = ppr.makeelement(qn("w:bidi"), {})
        ppr.append(bidi)
    for run in paragraph.runs:
        run.font.name = FONT
        run.font.size = Pt(11)
        rpr = run._element.get_or_add_rPr()
        rtl = rpr.find(qn("w:rtl"))
        if rtl is None:
            rtl = rpr.makeelement(qn("w:rtl"), {})
            rpr.append(rtl)


def _heading(document, text: str, level: int = 2):
    paragraph = document.add_heading(text, level=level)
    _rtl(paragraph)
    return paragraph


def _paragraph(document, text: str, *, bold: bool = False):
    paragraph = document.add_paragraph()
    run = paragraph.add_run(text or "")
    run.bold = bold
    _rtl(paragraph)
    return paragraph


def _bullets(document, items: Iterable[str]) -> None:
    for item in items:
        if str(item).strip():
            paragraph = document.add_paragraph(style="List Bullet")
            paragraph.add_run(str(item).strip())
            _rtl(paragraph)


def build_lesson_docx(plan: LessonPlan) -> bytes:
    from docx import Document
    from docx.shared import Cm, Pt

    document = Document()
    section = document.sections[0]
    section.top_margin = Cm(1.6)
    section.bottom_margin = Cm(1.6)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)

    style = document.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(11)

    title = document.add_heading(plan.title, level=0)
    _rtl(title)
    _paragraph(
        document,
        f"{plan.subject} · {plan.educational_level} · {plan.duration} دقيقة",
    )

    if plan.competency:
        _heading(document, "الكفاءة المستهدفة")
        _paragraph(document, plan.competency)

    _heading(document, "الأهداف التعليمية")
    _bullets(document, plan.learning_objectives)

    _heading(document, "المكتسبات السابقة")
    _bullets(document, plan.prerequisites)

    _heading(document, "الوسائل التعليمية")
    _bullets(document, plan.materials)

    _heading(document, "المفاهيم والمصطلحات")
    _bullets(document, plan.key_concepts)

    if plan.introduction:
        _heading(document, "وضعية الانطلاق")
        _paragraph(document, plan.introduction)

    _heading(document, "مراحل بناء التعلمات")
    for phase in plan.lesson_phases:
        _paragraph(document, f"{phase.name} — {phase.duration} دقيقة", bold=True)
        if phase.teacher_actions:
            _paragraph(document, "أنشطة المعلّم:", bold=True)
            _bullets(document, phase.teacher_actions)
        if phase.learner_actions:
            _paragraph(document, "أنشطة المتعلّم:", bold=True)
            _bullets(document, phase.learner_actions)
        if phase.guiding_questions:
            _paragraph(document, "أسئلة توجيهية:", bold=True)
            _bullets(document, phase.guiding_questions)

    if plan.experiments:
        _heading(document, "التجارب والأنشطة العلمية")
        for experiment in plan.experiments:
            _paragraph(document, experiment.title or "تجربة", bold=True)
            if experiment.materials:
                _paragraph(document, "المواد:", bold=True)
                _bullets(document, experiment.materials)
            if experiment.steps:
                _paragraph(document, "الخطوات:", bold=True)
                _bullets(document, experiment.steps)
            if experiment.safety_notes:
                _paragraph(document, "ملاحظات السلامة:", bold=True)
                _bullets(document, experiment.safety_notes)
            if experiment.expected_observation:
                _paragraph(document, f"الملاحظة المتوقعة: {experiment.expected_observation}")

    if plan.examples:
        _heading(document, "الأمثلة")
        _bullets(document, plan.examples)

    for label, block in (
        ("التقويم التكويني", plan.formative_assessment),
        ("التقويم النهائي", plan.summative_assessment),
    ):
        if block.is_empty():
            continue
        _heading(document, label)
        if block.description:
            _paragraph(document, block.description)
        for index, item in enumerate(block.items, 1):
            _paragraph(document, f"{index}. {item.question}", bold=True)
            _paragraph(document, f"الإجابة: {item.answer}")
            if item.explanation:
                _paragraph(document, f"الشرح: {item.explanation}")

    if plan.remediation:
        _heading(document, "الدعم والعلاج")
        _paragraph(document, plan.remediation)

    if plan.summary:
        _heading(document, "خلاصة الدرس")
        _paragraph(document, plan.summary)

    if plan.homework:
        _heading(document, "النشاط المنزلي")
        _paragraph(document, plan.homework)

    if plan.sources:
        _heading(document, "المصادر")
        _bullets(document, plan.sources)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def build_lesson_text(plan: LessonPlan) -> str:
    """Plain-text fallback used for clipboard and print views."""
    lines: List[str] = [plan.title, f"{plan.subject} · {plan.educational_level} · {plan.duration} دقيقة", ""]
    if plan.competency:
        lines += ["الكفاءة المستهدفة:", plan.competency, ""]
    if plan.learning_objectives:
        lines.append("الأهداف التعليمية:")
        lines += [f"- {item}" for item in plan.learning_objectives]
        lines.append("")
    for phase in plan.lesson_phases:
        lines.append(f"{phase.name} ({phase.duration} د):")
        lines += [f"  • {item}" for item in phase.teacher_actions]
        lines.append("")
    if plan.summary:
        lines += ["خلاصة الدرس:", plan.summary]
    return "\n".join(lines)


def docx_filename(plan: LessonPlan) -> str:
    from app.utils.text import safe_filename

    return f"{safe_filename(plan.title, 'lesson')}.docx"
