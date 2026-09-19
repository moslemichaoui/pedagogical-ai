"""Structured schemas and validation for pedagogical exercise generation."""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


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


class Exercise(BaseModel):
    """One teacher-facing exercise."""

    id: int = Field(..., ge=1)
    type: str
    question: str = Field(..., min_length=1)
    instructions: Optional[str] = None
    options: List[str] = Field(default_factory=list)
    answer: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    difficulty: str
    estimated_time: int = Field(default=3, ge=1, le=60)
    lesson_reference: str = Field(..., min_length=1)

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in EXERCISE_TYPES:
            raise ValueError(f"Invalid exercise type: {value}")
        return value

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        if value not in DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {value}")
        return value

    @model_validator(mode="after")
    def validate_type_specific_fields(self):
        if self.type == "اختيار من متعدد":
            if len(self.options) < 2:
                raise ValueError("Multiple-choice exercise requires at least 2 options")
            if self.answer not in self.options:
                raise ValueError("Multiple-choice answer must match one of the options")

        if self.type == "صح / خطأ":
            normalized = self.answer.strip().lower()
            allowed = {"صح", "خطأ", "صحيح", "خاطئ", "true", "false"}
            if normalized not in allowed:
                raise ValueError("True/false answer must be صح or خطأ")

        return self


class ExerciseSet(BaseModel):
    """A validated set of exercises generated from one lesson."""

    lesson_title: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    educational_level: str = Field(..., min_length=1)
    total_exercises: int = Field(..., ge=1, le=20)
    exercises: List[Exercise]
    language: str = "ar"

    @model_validator(mode="after")
    def validate_count(self):
        if len(self.exercises) != self.total_exercises:
            raise ValueError(
                f"total_exercises ({self.total_exercises}) must equal "
                f"the number of exercises ({len(self.exercises)})"
            )
        return self


class ExerciseGenerationRequest(BaseModel):
    """API request for exercise generation."""

    lesson_plan: dict
    exercise_types: List[str] = Field(default_factory=lambda: EXERCISE_TYPES.copy())
    count: int = Field(default=10, ge=5, le=20)
    difficulty: str = "متدرج"
    language: str = "ar"

    @field_validator("exercise_types")
    @classmethod
    def validate_types(cls, values: List[str]) -> List[str]:
        if not values:
            raise ValueError("At least one exercise type is required")
        invalid = [value for value in values if value not in EXERCISE_TYPES]
        if invalid:
            raise ValueError(f"Invalid exercise types: {', '.join(invalid)}")
        return list(dict.fromkeys(values))

    @field_validator("difficulty")
    @classmethod
    def validate_request_difficulty(cls, value: str) -> str:
        if value not in DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {value}")
        return value


class ExerciseGenerationResponse(BaseModel):
    """API response for exercise generation."""

    success: bool
    exercise_set: Optional[ExerciseSet] = None
    validation_errors: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
