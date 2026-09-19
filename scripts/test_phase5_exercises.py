"""Focused tests for Phase 5 exercise generation."""
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


LESSON_PLAN = {
    "title": "دورة الماء",
    "subject": "الإيقاظ العلمي",
    "educational_level": "السنة الرابعة ابتدائي",
    "duration": 45,
    "competency": "فهم مراحل دورة الماء",
    "learning_objectives": ["أن يتعرف المتعلم على مراحل دورة الماء"],
    "prerequisites": ["معرفة الماء وحالاته"],
    "materials": ["صور"],
    "key_concepts": ["التبخر", "التكاثف"],
    "introduction": "ملاحظة صورة لدورة الماء",
    "lesson_phases": [],
    "teacher_actions": [],
    "learner_actions": [],
    "guiding_questions": [],
    "expected_answers": [],
    "activities": [],
    "experiments": [],
    "exercises": [],
    "assessment": "أسئلة قصيرة",
    "remediation": "إعادة شرح المفاهيم الأساسية",
    "summary": "الماء يمر بمراحل متتابعة",
    "homework": "ارسم دورة الماء",
    "sources": [],
}


def main():
    results = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    try:
        from app import create_app
        from app.ai.exercise_schemas import (
            Exercise,
            ExerciseSet,
            ExerciseGenerationRequest,
        )
        from app.services.exercise_generation_service import ExerciseGenerationService
        import app.routes.exercises as exercises_routes
        check("Python imports", True)
    except Exception as exc:
        check("Python imports", False, str(exc))
        return 1

    try:
        app = create_app()
        check("Flask app creation", True)
    except Exception as exc:
        check("Flask app creation", False, str(exc))
        return 1

    # Schema validation
    try:
        mcq = Exercise(
            id=1,
            type="اختيار من متعدد",
            question="ما العملية التي تحول الماء السائل إلى بخار؟",
            options=["التبخر", "التكاثف", "التجمد"],
            answer="التبخر",
            explanation="التبخر يحول الماء السائل إلى بخار.",
            objective="التعرف على التبخر",
            difficulty="متوسط",
            estimated_time=3,
            lesson_reference="دورة الماء",
        )
        tf = Exercise(
            id=2,
            type="صح / خطأ",
            question="يتحول بخار الماء إلى قطرات عند التكاثف.",
            answer="صح",
            explanation="التكاثف يحول بخار الماء إلى ماء سائل.",
            objective="فهم التكاثف",
            difficulty="سهل",
            estimated_time=2,
            lesson_reference="دورة الماء",
        )
        fill = Exercise(
            id=3,
            type="أكمل الفراغ",
            question="تتحول مياه البحار إلى بخار بواسطة عملية ______.",
            answer="التبخر",
            explanation="الحرارة تساعد الماء على التبخر.",
            objective="توظيف مفهوم التبخر",
            difficulty="سهل",
            estimated_time=2,
            lesson_reference="دورة الماء",
        )
        check("Exercise schema validation", True)
        try:
            Exercise(
                id=4, type="اختيار من متعدد", question="سؤال",
                options=["أ", "ب"], answer="ج",
                explanation="تفسير", objective="هدف",
                difficulty="متوسط", lesson_reference="دورة الماء"
            )
            check("Invalid MCQ rejected", False, "Invalid answer was accepted")
        except Exception:
            check("Invalid MCQ rejected", True)

        exercise_set = ExerciseSet(
            lesson_title="دورة الماء",
            subject="الإيقاظ العلمي",
            educational_level="السنة الرابعة ابتدائي",
            total_exercises=3,
            exercises=[mcq, tf, fill],
            language="ar",
        )
        check("ExerciseSet count validation", len(exercise_set.exercises) == 3)

        try:
            ExerciseGenerationRequest(
                lesson_plan=LESSON_PLAN,
                exercise_types=["نوع غير صالح"],
                count=10,
                difficulty="متدرج",
                language="ar",
            )
            check("Invalid exercise type rejected", False)
        except Exception:
            check("Invalid exercise type rejected", True)
    except Exception as exc:
        check("Schema tests", False, str(exc))

    # Mock provider for successful generation.
    try:
        class FakeGemini:
            def generate(self, prompt):
                return json.dumps({
                    "lesson_title": "دورة الماء",
                    "subject": "الإيقاظ العلمي",
                    "educational_level": "السنة الرابعة ابتدائي",
                    "total_exercises": 5,
                    "language": "ar",
                    "exercises": [
                        {
                            "id": i,
                            "type": "أسئلة مباشرة",
                            "question": f"اذكر مرحلة من مراحل دورة الماء رقم {i}.",
                            "instructions": "أجب باختصار.",
                            "options": [],
                            "answer": "إجابة نموذجية",
                            "explanation": "يرتبط السؤال بمراحل دورة الماء.",
                            "objective": "التعرف على مراحل دورة الماء",
                            "difficulty": "متوسط",
                            "estimated_time": 2,
                            "lesson_reference": "دورة الماء",
                        }
                        for i in range(1, 6)
                    ],
                }, ensure_ascii=False)

        service = ExerciseGenerationService(gemini_provider=FakeGemini())
        request = ExerciseGenerationRequest(
            lesson_plan=LESSON_PLAN,
            exercise_types=["أسئلة مباشرة"],
            count=5,
            difficulty="متوسط",
            language="ar",
        )
        response = service.generate_exercises(request)
        check("Mocked exercise generation", response.success, str(response.error_message))
        check(
            "Generated exercise count",
            bool(response.exercise_set and len(response.exercise_set.exercises) == 5),
        )
    except Exception as exc:
        check("Mocked service generation", False, str(exc))

    # API with monkeypatched service.
    try:
        original_service = exercises_routes.ExerciseGenerationService
        exercises_routes.ExerciseGenerationService = lambda: ExerciseGenerationService(
            gemini_provider=FakeGemini()
        )
        try:
            with app.test_client() as client:
                response = client.post(
                    "/api/exercises/generate",
                    json={
                        "lesson_plan": LESSON_PLAN,
                        "exercise_types": ["أسئلة مباشرة"],
                        "count": 5,
                        "difficulty": "متوسط",
                        "language": "ar",
                    },
                )
                data = response.get_json()
                check("POST /api/exercises/generate", response.status_code == 200, str(data))
                check("API success payload", data.get("success") is True)
        finally:
            exercises_routes.ExerciseGenerationService = original_service
    except Exception as exc:
        check("Exercise API", False, str(exc))

    # Malformed AI response
    try:
        class BadGemini:
            def generate(self, prompt):
                return '{"lesson_title":"x","total_exercises":1,"exercises":[]}'

        response = ExerciseGenerationService(gemini_provider=BadGemini()).generate_exercises(
            ExerciseGenerationRequest(
                lesson_plan=LESSON_PLAN,
                exercise_types=["أسئلة مباشرة"],
                count=5,
                difficulty="متوسط",
            )
        )
        check("Malformed AI response rejected", not response.success)
    except Exception as exc:
        check("Malformed AI response handling", False, str(exc))

    # API request validation
    try:
        with app.test_client() as client:
            response = client.post("/api/exercises/generate", json={})
            check("Invalid API request rejected", response.status_code == 400)
    except Exception as exc:
        check("API request validation", False, str(exc))

    failed = [name for name, ok, _ in results if not ok]
    print("=== summary ===")
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("Failed tests:")
        for name in failed:
            print(f"  - {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
