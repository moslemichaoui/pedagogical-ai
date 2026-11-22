"""Shared pytest fixtures for the Arabic lesson-preparation app."""
from __future__ import annotations

import pytest

from app import create_app, db
from app.models import Exercise, Lesson
from app.utils.rate_limit import reset_limits
from config import TestConfig


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    app.config["SECRET_KEY"] = "test-only-secret"
    reset_limits()
    yield app
    reset_limits()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sample_plan() -> dict:
    """A compact but pedagogically complete Arabic lesson payload."""
    return {
        "title": "دورة الماء في الطبيعة",
        "subject": "الإيقاظ العلمي",
        "educational_level": "السنة الخامسة ابتدائي",
        "duration": 45,
        "competency": "يتمكّن المتعلّم من تفسير حركة الماء في الطبيعة وربطها بالظواهر اليومية.",
        "learning_objectives": [
            "يسمّي المتعلّم مراحل دورة الماء في الطبيعة.",
            "يفسّر تكوّن السحاب والأمطار انطلاقاً من التبخّر والتكاثف.",
        ],
        "prerequisites": ["يعرف حالات المادة الثلاث: الصلبة والسائلة والغازية."],
        "materials": ["إناء معدني", "ماء", "كوب بارد", "لوحة مصوّرة لدورة الماء"],
        "key_concepts": ["التبخّر", "التكاثف", "التساقط", "الجريان"],
        "introduction": "أعرض صورة بحيرة تحت الشمس وأسأل: أين يذهب الماء الذي يختفي كل يوم؟",
        "lesson_phases": [
            {
                "name": "التمهيد",
                "phase_key": "التمهيد",
                "duration": 5,
                "teacher_actions": ["أطرح السؤال المحفّز وأدوّن الفرضيات."],
                "learner_actions": ["يطرحون فرضياتهم حول اختفاء الماء."],
                "guiding_questions": ["أين يذهب الماء الذي يتبخّر؟"],
            },
            {
                "name": "وضعية الانطلاق",
                "phase_key": "وضعية الانطلاق",
                "duration": 8,
                "teacher_actions": ["أعرض مشهد غسيل الملابس تحت الشمس."],
                "learner_actions": ["يلاحظون الصورة ويصفون جفاف الملابس."],
                "guiding_questions": ["لماذا تجفّ الملابس؟"],
            },
            {
                "name": "بناء التعلمات",
                "phase_key": "بناء التعلمات",
                "duration": 20,
                "teacher_actions": ["أنجز التجربة وأرسم مخطط دورة الماء مع التلاميذ."],
                "learner_actions": ["يلاحظون القطرات ويسمّون الظواهر ويرسمون المخطط."],
                "guiding_questions": ["من أين جاءت القطرات على الكوب البارد؟"],
            },
            {
                "name": "التقويم",
                "phase_key": "التقويم",
                "duration": 7,
                "teacher_actions": ["أوزّع بطاقة ناقصة وأصحّح جماعياً."],
                "learner_actions": ["يكملون مراحل الدورة ويعرضون إجاباتهم."],
                "guiding_questions": ["رتّب المراحل: تبخّر، تكاثف، تساقط، جريان."],
            },
            {
                "name": "الخلاصة",
                "phase_key": "الخلاصة",
                "duration": 5,
                "teacher_actions": ["أصوغ الخلاصة مع التلاميذ وأكتبها على السبورة."],
                "learner_actions": ["يقرؤون الخلاصة ويكتبونها في الدفتر."],
                "guiding_questions": ["ما أهم مرحلة في دورة الماء؟"],
            },
        ],
        "experiments": [
            {
                "title": "تبخّر الماء وتكاثفه",
                "materials": ["ماء", "إناء معدني", "كوب بارد"],
                "steps": ["نراقب الماء في الإناء.", "نقرّب الكوب البارد فوق البخار."],
                "safety_notes": ["يُنجز النشاط على طاولة المعلّم بإشرافه المباشر."],
                "expected_observation": "يتكاثف البخار على السطح البارد مكوّناً قطرات ماء.",
            }
        ],
        "examples": ["جفاف الملابس بعد الغسيل تفسيره تبخّر الماء."],
        "formative_assessment": {
            "description": "تقويم مرحلي أثناء بناء التعلمات.",
            "items": [
                {
                    "question": "ما اسم تحوّل الماء السائل إلى بخار؟",
                    "answer": "التبخّر",
                    "explanation": "يحدث التبخّر بتأثير الحرارة.",
                }
            ],
        },
        "summative_assessment": {
            "description": "تقويم ختامي قصير في نهاية الحصة.",
            "items": [
                {
                    "question": "رتّب مراحل دورة الماء في الطبيعة.",
                    "answer": "تبخّر ← تكاثف ← تساقط ← جريان.",
                }
            ],
        },
        "remediation": "أعيد التجربة أمام التلاميذ المتعثّرين باستعمال بطاقة مصوّرة مرقّمة.",
        "summary": "الماء يتبخّر بحرارة الشمس، ثم يتكاثف مكوّناً السحاب، ثم يتساقط ويعود عبر الجريان.",
        "homework": "أرسم دورة الماء في دفتري وأكتب تحت كل مرحلة جملة واحدة.",
        "sources": ["منهاج الإيقاظ العلمي — السنة الخامسة ابتدائي"],
    }


@pytest.fixture()
def lesson(app, sample_plan):
    """Persist one lesson with both exercise and assessment items."""
    with app.app_context():
        record = Lesson(
            title=sample_plan["title"],
            topic="دورة الماء في الطبيعة",
            material=sample_plan["subject"],
            level=sample_plan["educational_level"],
            duration=sample_plan["duration"],
            objectives=sample_plan["learning_objectives"],
            difficulty="متوسط",
            language="ar",
            content=sample_plan,
            status="ready",
            model_used="test-model",
            retrieved_context_count=0,
            duration_coherent=True,
            validation_errors=[],
            validation_warnings=[],
            source_document_ids=[],
        )
        record.exercises.append(
            Exercise(
                kind="exercise",
                type="سؤال قصير",
                question="ما اسم تحوّل الماء السائل إلى بخار؟",
                answer="التبخّر",
                order_index=0,
            )
        )
        record.exercises.append(
            Exercise(
                kind="assessment",
                type="ترتيب",
                question="رتّب مراحل دورة الماء.",
                answer="تبخّر ← تكاثف ← تساقط ← جريان",
                order_index=0,
            )
        )
        db.session.add(record)
        db.session.commit()
        lesson_id = record.id
    return lesson_id
