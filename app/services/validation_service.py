"""Pedagogical validation and a transparent quality rubric.

Validation answers one question: *would a Tunisian primary teacher be able to
teach this lesson tomorrow?* Hard errors block saving; warnings are surfaced in
the UI as improvement hints.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.ai.schemas import PHASE_SPINE, LessonPlan
from app.utils.text import arabic_ratio, normalize_arabic

ACTION_VERBS = {
    "يتعرف", "يتعرّف", "يشرح", "يميز", "يميّز", "يصنف", "يصنّف", "يطبق",
    "يطبّق", "يستنتج", "يقارن", "يصف", "يحدد", "يحدّد", "يرتب", "يعرف",
    "يعرّف", "يستعمل", "يستخدم", "يحلل", "يحلّل", "يقيس", "يرسم", "يلاحظ",
    "يستخرج", "يجيب", "ينجز", "يبرهن", "يقيّم", "يقيم", "يتحقق", "يتحقّق",
}

DANGEROUS = {
    "انفجار", "متفجر", "تسمم", "سم", "حارق", "تحريق", "حمض قوي", "صودا كاوية",
    "كهرباء عارية", "لهب مباشر", "explosive", "poison", "toxic",
}

MAX_SCORE = 100


class ValidationService:
    """Score a lesson sheet against the national sheet conventions."""

    def validate_lesson_plan(self, lesson_plan: LessonPlan) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []
        rubric: List[Dict[str, str]] = []

        def check(key: str, label: str, passed: bool, detail: str, hard: bool = False) -> None:
            if not passed:
                (errors if hard else warnings).append(detail)
            rubric.append(
                {
                    "key": key,
                    "label": label,
                    "status": "pass" if passed else ("fail" if hard else "warn"),
                    "detail": "" if passed else detail,
                }
            )

        # 1. Identity -------------------------------------------------
        identity = bool(lesson_plan.title.strip()) and bool(lesson_plan.subject.strip()) and bool(
            lesson_plan.educational_level.strip()
        )
        check("identity", "هوية الدرس", identity, "عنوان الدرس أو المادة أو المستوى ناقص.", hard=True)

        # 2. Arabic ---------------------------------------------------
        sample = " ".join(
            [
                lesson_plan.title,
                lesson_plan.competency,
                lesson_plan.introduction,
                lesson_plan.summary,
                " ".join(lesson_plan.learning_objectives),
            ]
        )
        ratio = arabic_ratio(sample)
        check(
            "arabic",
            "سلامة اللغة العربية",
            ratio >= 0.6,
            "المحتوى لا يبدو مكتوباً بالعربية الفصحى.",
            hard=True,
        )

        # 3. Objectives ----------------------------------------------
        objectives = [item for item in lesson_plan.learning_objectives if item.strip()]
        action_objectives = [
            item for item in objectives if normalize_arabic(item.split(" ")[0]) in {normalize_arabic(v) for v in ACTION_VERBS}
        ]
        check(
            "objectives",
            "صياغة الأهداف",
            len(objectives) >= 2 and len(action_objectives) >= max(1, len(objectives) // 2),
            "الأهداف قليلة أو غير مصاغة بأفعال إجرائية.",
        )

        # 4. Prerequisites & materials --------------------------------
        check(
            "preparation",
            "المكتسبات والوسائل",
            bool(lesson_plan.prerequisites) and bool(lesson_plan.materials),
            "لم تُذكر المكتسبات السابقة أو الوسائل التعليمية.",
        )

        # 5. Phase spine ----------------------------------------------
        phase_keys = {normalize_arabic(phase.phase_key or phase.name) for phase in lesson_plan.lesson_phases}
        missing = [
            name for name in PHASE_SPINE if normalize_arabic(name) not in phase_keys
        ]
        check(
            "phases",
            "سلم المراحل الخمس",
            len(lesson_plan.lesson_phases) >= 4 and len(missing) <= 1,
            "المراحل لا تتبع السلم البيداغوجي: " + ("، ".join(missing) if missing else "غير مكتملة"),
        )

        # 6. Actor actions -------------------------------------------
        phases_ok = all(
            phase.teacher_actions and phase.learner_actions
            for phase in lesson_plan.lesson_phases
        )
        check(
            "actors",
            "أنشطة المعلّم والمتعلّم",
            phases_ok,
            "بعض المراحل تفتقد أنشطة المعلّم أو المتعلّم.",
        )

        # 7. Duration -------------------------------------------------
        if lesson_plan.lesson_phases:
            total = lesson_plan.get_total_phase_duration()
            coherent = abs(total - lesson_plan.duration) <= 2
            check(
                "duration",
                "تماسك المدة الزمنية",
                coherent,
                f"مجموع المراحل {total} دقيقة مقابل {lesson_plan.duration} دقيقة مطلوبة.",
            )
        else:
            check("duration", "تماسك المدة الزمنية", False, "لا توجد مراحل موقوتة.", hard=True)

        # 8. Assessment ------------------------------------------------
        has_formative = not lesson_plan.formative_assessment.is_empty()
        has_summative = not lesson_plan.summative_assessment.is_empty()
        check(
            "assessment",
            "التقويم التكويني والنهائي",
            has_formative and has_summative,
            "ينقص الدرس تقويم تكويني أو تقويم نهائي.",
        )

        # 9. Safety ----------------------------------------------------
        unsafe = []
        for experiment in lesson_plan.experiments:
            blob = normalize_arabic(
                " ".join(
                    [
                        experiment.title,
                        " ".join(experiment.materials),
                        " ".join(experiment.steps),
                    ]
                )
            )
            unsafe.extend(word for word in DANGEROUS if normalize_arabic(word) in blob)
        check(
            "safety",
            "سلامة الأنشطة",
            not unsafe,
            "تم رصد مواد أو إجراءات غير آمنة: " + "، ".join(sorted(set(unsafe))),
            hard=True,
        )

        # 10. Closure --------------------------------------------------
        check(
            "closure",
            "الخلاصة والدعم",
            bool(lesson_plan.summary.strip()) and bool(lesson_plan.remediation.strip()),
            "لم تُذكر خلاصة الدرس أو أنشطة الدعم.",
        )

        # 11. Sources --------------------------------------------------
        if lesson_plan.insufficient_sources:
            warnings.append(
                "أشار النموذج إلى نقص المصادر؛ راجع المحتوى العلمي قبل الاستعمال."
            )
        check(
            "sources",
            "الإسناد إلى المصادر",
            not lesson_plan.insufficient_sources,
            "المحتوى غير مسند بالكامل إلى وثائق مرجعية.",
        )

        passed = sum(1 for item in rubric if item["status"] == "pass")
        score = round(passed / max(1, len(rubric)) * MAX_SCORE)

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "rubric": rubric,
            "score": score,
            "error_count": len(errors),
            "warning_count": len(warnings),
        }

    def validate_generation_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[str] = []
        for field, label in (
            ("subject", "المادة"),
            ("educational_level", "المستوى"),
            ("topic", "الموضوع"),
            ("duration", "المدة"),
        ):
            if not payload.get(field):
                errors.append(f"الحقل «{label}» مطلوب.")
        duration = payload.get("duration")
        try:
            duration_int = int(duration)
            if not 5 <= duration_int <= 180:
                errors.append("المدة يجب أن تكون بين 5 و180 دقيقة.")
        except (TypeError, ValueError):
            errors.append("المدة يجب أن تكون عدداً صحيحاً.")
        topic = str(payload.get("topic") or "").strip()
        if topic and len(topic) < 2:
            errors.append("الموضوع قصير جداً.")
        return {"valid": not errors, "errors": errors}

    def rubric_summary(self, result: Dict[str, Any]) -> str:
        score = result.get("score", 0)
        if score >= 90:
            return "جذاذة مكتملة وجاهزة للاستعمال."
        if score >= 70:
            return "جذاذة جيدة مع بعض النقاط القابلة للتحسين."
        return "تحتاج الجذاذة إلى مراجعة قبل الاستعمال."
