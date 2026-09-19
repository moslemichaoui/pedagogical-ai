"""Prompts for structured exercise generation."""
import json
from typing import Any, Dict, List


EXERCISE_SYSTEM_PROMPT = """You are a pedagogical exercise designer for primary-school teachers.

Your task is to create exercises strictly from a validated lesson plan.

Rules:
1. Use Modern Standard Arabic when language is ar.
2. Adapt vocabulary and cognitive level to the educational level.
3. Align every exercise with the lesson objectives and key concepts.
4. Do not introduce facts unrelated to the lesson.
5. Keep scientific content accurate.
6. Provide a clear correction and a short pedagogical explanation.
7. Respect the requested exercise types, count, and difficulty.
8. For multiple-choice questions, provide at least 3 options and make exactly one option correct.
9. For true/false, answer only with "صح" or "خطأ".
10. For practical/scientific activities, use safe, age-appropriate materials and procedures.
11. Do not invent sources or citations.
12. Return valid JSON only.

Required JSON structure:
{
  "lesson_title": "...",
  "subject": "...",
  "educational_level": "...",
  "total_exercises": 10,
  "language": "ar",
  "exercises": [
    {
      "id": 1,
      "type": "اختيار من متعدد",
      "question": "...",
      "instructions": "...",
      "options": ["...", "...", "..."],
      "answer": "...",
      "explanation": "...",
      "objective": "...",
      "difficulty": "متوسط",
      "estimated_time": 3,
      "lesson_reference": "..."
    }
  ]
}
"""


def build_exercise_generation_prompt(
    lesson_plan: Dict[str, Any],
    exercise_types: List[str],
    count: int,
    difficulty: str,
    language: str = "ar",
) -> str:
    selected = "\n".join(f"- {item}" for item in exercise_types)
    lesson_json = json.dumps(lesson_plan, ensure_ascii=False, indent=2)

    return f"""Generate exactly {count} exercises from the following validated lesson plan.

LANGUAGE: {language}
REQUESTED DIFFICULTY: {difficulty}

ALLOWED EXERCISE TYPES:
{selected}

LESSON PLAN:
{lesson_json}

Requirements:
- Generate exactly {count} exercises.
- Use only the allowed exercise types.
- Distribute types reasonably when several types are selected.
- Keep all exercises directly connected to the lesson.
- Align each exercise with one or more learning objectives.
- Use age-appropriate wording.
- Include answers, explanations, objectives, difficulty and estimated time.
- For "اختيار من متعدد", include options and make the answer exactly one option.
- For "صح / خطأ", answer with "صح" or "خطأ".
- For "أكمل الفراغ", place a clear blank in the question and provide the expected answer.
- For "صل" and "صنّف", describe the matching/classification task clearly in the question or instructions.
- For "أنشطة علمية", keep the activity safe and feasible in a primary classroom.

Return JSON only using the required structure."""
