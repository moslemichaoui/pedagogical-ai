"""Seed the local database with demonstration lessons.

The script is safe to re-run: it only inserts a demo lesson when no lesson with
the same title exists. Use it to explore the interface without a Gemini key.

    python scripts/seed_demo.py
    python scripts/seed_demo.py --reset   # delete previous demo lessons first
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import timedelta

try:  # Windows consoles default to a legacy code page.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):  # pragma: no cover
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db  # noqa: E402
from app.ai.schemas import LessonPlan  # noqa: E402
from app.models import Exercise, GenerationRun, Lesson, utcnow  # noqa: E402

DEMO_TAG = "[demo]"


def phase(name, key, minutes, teacher, learner, questions):
    return {
        "name": name,
        "phase_key": key,
        "duration": minutes,
        "teacher_actions": teacher,
        "learner_actions": learner,
        "guiding_questions": questions,
    }


WATER_PLAN = {
    "title": "دورة الماء في الطبيعة",
    "subject": "الإيقاظ العلمي",
    "educational_level": "السنة الخامسة ابتدائي",
    "duration": 45,
    "competency": "يتمكّن المتعلّم من تفسير حركة الماء في الطبيعة وربطها بالظواهر المناخية اليومية.",
    "learning_objectives": [
        "يسمّي المتعلّم مراحل دورة الماء في الطبيعة.",
        "يفسّر تكوّن السحاب والأمطار انطلاقاً من التبخّر والتكاثف.",
        "يربط بين دورة الماء وأهمية المحافظة على الموارد المائية.",
    ],
    "prerequisites": [
        "يعرف حالات المادة الثلاث: الصلبة والسائلة والغازية.",
        "لاحظ تبخّر الماء عند الغسيل أو تحت أشعة الشمس.",
    ],
    "materials": ["إناء معدني", "ماء", "مصدر حرارة آمن", "لوحة مصوّرة لدورة الماء", "أكواب شفافة"],
    "key_concepts": ["التبخّر", "التكاثف", "التساقط", "الجريان", "الدورة المائية"],
    "introduction": (
        "أعرض على التلاميذ صورة بحيرة تحت شمس حارقة وأسألهم: أين يذهب الماء الذي يختفي كلّ يوم؟ "
        "أستمع إلى فرضياتهم دون تصحيح، وأدوّنها على السبورة لتكون موضوع التحقّق خلال الدرس."
    ),
    "lesson_phases": [
        phase(
            "التمهيد",
            "التمهيد",
            5,
            ["أستقبل التلاميذ وأطرح السؤال المحفّز.", "أدوّن الفرضيات على السبورة."],
            ["يستمعون ويطرحون فرضياتهم حول اختفاء الماء."],
            ["أين يذهب الماء الذي يتبخّر من البحيرة؟", "هل يختفي الماء فعلاً أم يتحوّل؟"],
        ),
        phase(
            "وضعية الانطلاق",
            "وضعية الانطلاق",
            8,
            ["أعرض مشهد غسيل ملابس تحت الشمس.", "أوجّه الملاحظة نحو جفاف الملابس."],
            ["يلاحظون الصورة ويصفون ما يحدث للماء."],
            ["لماذا تجفّ الملابس؟", "إلى أين ذهب الماء؟"],
        ),
        phase(
            "بناء التعلمات",
            "بناء التعلمات",
            18,
            [
                "أنجز التجربة أمام التلاميذ: تسخين الماء في إناء وتقريب كوب بارد فوق البخار.",
                "أرسم مخطط دورة الماء تدريجياً مع التلاميذ.",
                "أثبّت المصطلحات العلمية على السبورة.",
            ],
            [
                "يلاحظون البخار ثم قطرات الماء على الكوب البارد.",
                "يسمّون الظواهر: تبخّر، تكاثف، تساقط.",
                "يرسمون المخطط في الدفاتر.",
            ],
            ["ماذا نلاحظ فوق الإناء؟", "من أين جاءت القطرات على الكوب البارد؟", "ماذا يحدث للبخار في السماء؟"],
        ),
        phase(
            "التقويم",
            "التقويم",
            9,
            ["أوزّع بطاقة مصوّرة ناقصة ويطلب إكمالها.", "أصحّح جماعياً وأعالج الأخطاء."],
            ["يكملون مراحل الدورة على البطاقة.", "يعرضون إجاباتهم على أقرانهم."],
            ["رتّب المراحل: تبخّر، تكاثف، تساقط، جريان.", "أين تحدث كل مرحلة؟"],
        ),
        phase(
            "الخلاصة",
            "الخلاصة",
            5,
            ["أصوغ الخلاصة مع التلاميذ وأكتبها على السبورة."],
            ["يقرؤون الخلاصة ويكتبونها في الدفتر."],
            ["ما أهم مرحلة في دورة الماء؟ ولماذا؟"],
        ),
    ],
    "experiments": [
        {
            "title": "تبخّر الماء وتكاثفه",
            "materials": ["إناء معدني", "ماء", "مصدر حرارة", "كوب زجاجي بارد"],
            "steps": [
                "نسخّن كمية قليلة من الماء في الإناء.",
                "نقرّب الكوب البارد فوق البخار المتصاعد.",
                "نلاحظ القطرات المتكوّنة على جدار الكوب.",
            ],
            "safety_notes": [
                "لا يلمس التلاميذ الإناء الساخن.",
                "يُنجز النشاط على طاولة المعلّم بإشرافه المباشر.",
            ],
            "expected_observation": "يتصاعد البخار ثم يتكاثف على السطح البارد مكوّناً قطرات ماء.",
            "risk_level": "متوسط",
        }
    ],
    "examples": [
        "جفاف الملابس بعد الغسيل تفسيره تبخّر الماء.",
        "الضباب في الصباح البارد مثال على التكاثف.",
        "المطر والثلج صورتان للتساقط.",
    ],
    "formative_assessment": {
        "description": "تقويم مرحلي أثناء بناء التعلمات للتحقّق من فهم المراحل.",
        "items": [
            {
                "question": "ما اسم تحوّل الماء السائل إلى بخار؟",
                "answer": "التبخّر",
                "explanation": "يحدث التبخّر بتأثير الحرارة.",
                "type": "سؤال قصير",
            },
            {
                "question": "كيف يتكوّن السحاب؟",
                "answer": "بتكاثف بخار الماء في طبقات الجوّ الباردة.",
                "explanation": "البخار يبرد فيتحوّل إلى قطرات دقيقة.",
                "type": "سؤال قصير",
            },
        ],
    },
    "summative_assessment": {
        "description": "تقويم ختامي قصير في نهاية الحصة.",
        "items": [
            {
                "question": "رتّب مراحل دورة الماء في الطبيعة.",
                "answer": "تبخّر ← تكاثف ← تساقط ← جريان.",
                "explanation": "الدورة متواصلة ولا تتوقّف.",
                "type": "ترتيب",
            },
            {
                "question": "اقترح سلوكين للمحافظة على الماء.",
                "answer": "إصلاح التسرّبات وعدم تبذير الماء عند الاستعمال.",
                "explanation": "الماء مورد محدود وثمين.",
                "type": "سؤال مفتوح",
            },
        ],
    },
    "remediation": (
        "أعيد التجربة أمام التلاميذ المتعثّرين باستعمال كوب بارد جداً، وأستعمل بطاقة مصوّرة "
        "بمراحل مرقّمة، ثم أطلب منهم شرح الدورة لزميل."
    ),
    "summary": (
        "الماء يتبخّر بحرارة الشمس، ويتكاثف في السماء مكوّناً السحاب، ثم يتساقط مطراً أو ثلجاً، "
        "ويعود إلى البحار والأنهار عبر الجريان. دورة الماء متواصلة وتحفظ توازن الطبيعة."
    ),
    "homework": "أرسم دورة الماء في دفتري وأكتب تحت كل مرحلة جملة واحدة، ثم أبحث عن صورتين للضباب والمطر.",
    "sources": ["منهاج الإيقاظ العلمي — السنة الخامسة ابتدائي", "دليل المعلّم: الأنشطة التجريبية"],
    "insufficient_sources": False,
}

PLANT_PLAN = {
    "title": "حاجات النبات الأخضر للنمو",
    "subject": "الإيقاظ العلمي",
    "educational_level": "السنة الثالثة ابتدائي",
    "duration": 40,
    "competency": "يتعرّف المتعلّم على الشروط الضرورية لنمو النبات الأخضر ويختبرها بنفسه.",
    "learning_objectives": [
        "يذكر المتعلّم حاجات النبات للنمو: الماء، الضوء، التربة، الحرارة.",
        "يصمّم تجربة بسيطة للمقارنة بين نبات مسقي وآخر غير مسقي.",
        "يستنتج أن غياب أحد الشروط يعطّل النمو.",
    ],
    "prerequisites": ["يميّز بين النبات والحيوان.", "لاحظ نباتات في محيطه المدرسي."],
    "materials": ["نبتتان متماثلتان في أصيصين", "ماء", "مكان مضيء", "مكان مظلم", "جدول ملاحظة"],
    "key_concepts": ["النمو", "التربة", "الضوء", "الريّ", "الملاحظة العلمية"],
    "introduction": (
        "أعرض نبتتين: واحدة خضراء قوية وأخرى ذابلة، وأسأل التلاميذ عن السبب المحتمل. "
        "أسجّل الفرضيات وأقودهم إلى صياغة سؤال بحث: ماذا يحتاج النبات لينمو؟"
    ),
    "lesson_phases": [
        phase("التمهيد", "التمهيد", 4, ["أعرض النبتتين وأطرح الملاحظة."], ["يلاحظون الفرق ويقترحون أسباباً."], ["لماذا ذبلت هذه النبتة؟"]),
        phase(
            "وضعية الانطلاق",
            "وضعية الانطلاق",
            6,
            ["أكتب سؤال البحث على السبورة.", "أقسّم التلاميذ إلى مجموعات."],
            ["يصوغون الفرضيات داخل مجموعاتهم."],
            ["ما الذي يحتاجه النبات لينمو؟"],
        ),
        phase(
            "بناء التعلمات",
            "بناء التعلمات",
            18,
            ["أوزّع الأصص وأدلّ المجموعات على خطوات التجربة.", "أمرّ بين المجموعات وأسأل عن الملاحظات."],
            ["يضعون نبتة في الضوء وأخرى في الظل، ويسقون واحدة فقط.", "يدوّنون الملاحظات في الجدول."],
            ["ما الفرق بين النبتتين بعد أسبوع؟", "أيّ شرط غيّرناه؟"],
        ),
        phase("التقويم", "التقويم", 7, ["أطلب استنتاجاً جماعياً."], ["يعبّرون عن الاستنتاج بجملة علمية."], ["هل يكفي الماء وحده؟"]),
        phase("الخلاصة", "الخلاصة", 5, ["أثبّت الخلاصة على السبورة."], ["ينسخون الخلاصة ويرسمون التجربة."], ["كيف نعتني بنبات القسم؟"]),
    ],
    "experiments": [
        {
            "title": "نبات في الضوء ونبات في الظل",
            "materials": ["أصيصان", "نبتتان متماثلتان", "ماء"],
            "steps": ["نضع الأولى قرب النافذة والثانية في خزانة.", "نسقي الاثنتين بالكمية نفسها.", "نلاحظ بعد أسبوع."],
            "safety_notes": ["غسل الأيدي بعد التعامل مع التربة."],
            "expected_observation": "تنمو نبتة الضوء بينما تصفرّ نبتة الظل وتضعف.",
            "risk_level": "منعدم",
        }
    ],
    "examples": ["نباتات الحديقة تنمو جيداً في الشمس.", "نبات الظل المنزلي لا يحتاج شمساً مباشرة."],
    "formative_assessment": {
        "description": "ملاحظة أداء المجموعات أثناء التجربة.",
        "items": [
            {"question": "ماذا يحدث للنبات إذا لم نسقه؟", "answer": "يذبل ثم يجفّ.", "type": "سؤال قصير"},
        ],
    },
    "summative_assessment": {
        "description": "تقويم ختامي.",
        "items": [
            {"question": "اذكر ثلاث حاجات لنمو النبات.", "answer": "الماء، الضوء، التربة.", "type": "سؤال قصير"},
            {"question": "لماذا نضع نبتة في الظل في التجربة؟", "answer": "للمقارنة ومعرفة أثر الضوء.", "type": "سؤال تفسيري"},
        ],
    },
    "remediation": "أعيد التجربة مع مجموعة صغيرة وأستعمل صوراً متتابعة لنمو نبتة أسبوعاً بأسبوع.",
    "summary": "يحتاج النبات الأخضر إلى الماء والضوء والتربة والحرارة لينمو؛ وغياب أحدها يضعفه.",
    "homework": "ألاحظ نبتة في المنزل وأدوّن طولها كل يومين في جدول.",
    "sources": ["منهاج الإيقاظ العلمي — السنة الثالثة ابتدائي"],
    "insufficient_sources": True,
}

EXERCISES = [
    ("exercise", "اختيار من متعدد", "أيّ العوامل التالية ليس من حاجات النبات؟", ["الماء", "الضوء", "الضجيج", "التربة"], "الضجيج", "النبات لا يتأثّر بالضجيج لنموّه.", "سهل"),
    ("exercise", "صح أو خطأ", "يتكوّن السحاب من تكاثف بخار الماء.", ["صح", "خطأ"], "صح", "البخار يبرد فيتحوّل إلى قطرات دقيقة.", "سهل"),
    ("exercise", "إكمال", "تتحوّل قطرات الماء في السحاب إلى مطر أو ثلج وتسمّى هذه المرحلة ........", [], "التساقط", "التساقط يعيد الماء إلى سطح الأرض.", "متوسط"),
    ("assessment", "سؤال تفسيري", "فسّر لماذا تجفّ البركة الصغيرة في الصيف.", [], "لأنّ الماء يتبخّر بفعل الحرارة المرتفعة.", "التبخّر يزداد بارتفاع الحرارة.", "متوسط"),
    ("assessment", "سؤال مفتوح", "اقترح تجربة لإثبات أن الضوء ضروري لنمو النبات.", [], "نضع نبتتين متماثلتين، واحدة في الضوء وأخرى في الظل، ونسقيهما بالتساوي.", "المقارنة تُظهر أثر العامل المدروس.", "صعب"),
]


def build_lesson(plan_dict, *, days_ago, model="demo-seed"):
    plan = LessonPlan(**plan_dict).normalize_durations()
    lesson = Lesson(
        title=plan.title,
        topic=plan.title,
        material=plan.subject,
        level=plan.educational_level,
        duration=plan.duration,
        objectives=plan.learning_objectives,
        difficulty="متوسط",
        language="ar",
        reference_documents=DEMO_TAG,
        content=plan.model_dump(),
        status="ready",
        model_used=model,
        retrieved_context_count=0,
        duration_coherent=plan.validate_duration_coherence(),
        validation_errors=[],
        validation_warnings=[] if not plan.insufficient_sources else ["لم تُرفق مصادر كافية."],
        source_document_ids=[],
        created_at=utcnow() - timedelta(days=days_ago),
    )
    db.session.add(lesson)
    db.session.flush()
    for index, (kind, type_, question, options, answer, explanation, difficulty) in enumerate(EXERCISES):
        db.session.add(
            Exercise(
                lesson_id=lesson.id,
                kind=kind,
                type=type_,
                question=question,
                options=options,
                answer=answer,
                explanation=explanation,
                difficulty=difficulty,
                order_index=index,
                payload={"label": type_},
            )
        )
    db.session.add(
        GenerationRun(
            lesson_id=lesson.id,
            kind="lesson",
            status="ok",
            model_used=model,
            latency_ms=18400,
            retrieved_context_count=0,
            created_at=lesson.created_at,
        )
    )
    return lesson


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo lessons.")
    parser.add_argument("--reset", action="store_true", help="delete previous demo lessons first")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.reset:
            removed = 0
            for lesson in Lesson.query.filter_by(reference_documents=DEMO_TAG).all():
                db.session.delete(lesson)
                removed += 1
            db.session.commit()
            print(f"removed {removed} demo lesson(s)")

        created = 0
        for plan_dict, days_ago in ((WATER_PLAN, 1), (PLANT_PLAN, 4)):
            if Lesson.query.filter_by(title=plan_dict["title"], reference_documents=DEMO_TAG).first():
                print(f"skip  {plan_dict['title']}")
                continue
            lesson = build_lesson(plan_dict, days_ago=days_ago)
            created += 1
            print(f"added {lesson.title} (id={lesson.id})")

        db.session.commit()
        print(f"done: {created} lesson(s) created, {Lesson.query.count()} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
