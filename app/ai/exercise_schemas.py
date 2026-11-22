"""Schemas for exercise generation from a saved lesson sheet."""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EXERCISE_TYPES = [
    "أسئلة مباشرة",
    "صح / خطأ",
    "أكمل الفراغ",
    "صل",
    "صنّف",
    "اختيار من متعدد",
    "أسئلة قصيرة",
    "وضعيات تطبيقية",
    "أنشطة ملاحظة",
    "أنشطة علمية",
]

DIFFICULTIES = ["سهل", "متوسط", "صعب", "متدرج"]
_DIFFICULTY_ALIASES = {
    "سهلة": "سهل",
    "متوسطة": "متوسط",
    "صعبة": "صعب",
    "متدرجة": "متدرج",
}


class Exercise(BaseModel):
    """One teacher-facing exercise with its correction."""

    model_config = ConfigDict(extra="ignore")

    id: int = 0
    type: str = "أسئلة قصيرة"
    question: str = Field(..., min_length=2)
    instructions: str = ""
    options: List[str] = Field(default_factory=list)
    answer: str = Field(..., min_length=1)
    explanation: str = ""
    objective: str = ""
    difficulty: str = "متوسط"
    estimated_time: int = Field(default=3, ge=1, le=60)
    lesson_reference: str = ""

    @field_validator("difficulty")
    @classmethod
    def normalize_difficulty(cls, value: str) -> str:
        value = (value or "متوسط").strip()
        value = _DIFFICULTY_ALIASES.get(value, value)
        return value if value in DIFFICULTIES else "متوسط"

    @field_validator("options", mode="before")
    @classmethod
    def normalize_options(cls, value: Any):
        if not value:
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("answer", mode="before")
    @classmethod
    def normalize_true_false(cls, value: Any, info):
        text = str(value or "").strip()
        if text.lower() in {"true", "صحيح", "صح"}:
            return "صح"
        if text.lower() in {"false", "خاطئ", "خطأ"}:
            return "خطأ"
        return text

    @model_validator(mode="after")
    def fill_defaults(self):
        if not self.instructions:
            self.instructions = ""
        if not self.explanation:
            self.explanation = "راجع الهدف المرتبط بالتمرين."
        if self.type == "اختيار من متعدد" and self.options and self.answer not in self.options:
            # Keep the generated answer but make it selectable.
            self.options = [self.answer, *[opt for opt in self.options if opt != self.answer]]
        return self


class ExerciseSet(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lesson_title: str = ""
    subject: str = ""
    educational_level: str = ""
    total_exercises: int = 0
    exercises: List[Exercise] = Field(default_factory=list)
    language: str = "ar"

    @model_validator(mode="after")
    def reconcile_count(self):
        self.total_exercises = len(self.exercises)
        for index, exercise in enumerate(self.exercises, 1):
            if not exercise.id:
                exercise.id = index
            if not exercise.lesson_reference:
                exercise.lesson_reference = self.lesson_title
        return self


class ExerciseGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lesson_plan: dict
    exercise_types: List[str] = Field(default_factory=lambda: EXERCISE_TYPES.copy())
    count: int = Field(default=8, ge=1, le=20)
    difficulty: str = "متدرج"
    language: str = "ar"

    @field_validator("exercise_types", mode="before")
    @classmethod
    def normalize_types(cls, value: Any):
        if not value:
            return EXERCISE_TYPES.copy()
        items = [str(item).strip() for item in value if str(item).strip()]
        return list(dict.fromkeys(items)) or EXERCISE_TYPES.copy()

    @field_validator("difficulty")
    @classmethod
    def normalize_request_difficulty(cls, value: str) -> str:
        value = _DIFFICULTY_ALIASES.get((value or "").strip(), (value or "").strip())
        return value if value in DIFFICULTIES else "متدرج"


class ExerciseGenerationResponse(BaseModel):
    success: bool
    exercise_set: Optional[ExerciseSet] = None
    validation_errors: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    model_used: Optional[str] = None
