"""Schemas for formative and summative assessment generation."""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ASSESSMENT_KINDS = {"formative": "تقويم تكويني", "summative": "تقويم نهائي"}
DIFFICULTIES = ["سهل", "متوسط", "صعب", "متدرج"]
_ALIASES = {"سهلة": "سهل", "متوسطة": "متوسط", "صعبة": "صعب", "متدرجة": "متدرج"}


class AssessmentItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str = Field(..., min_length=2)
    answer: str = Field(..., min_length=1)
    explanation: str = ""
    objective: str = ""
    difficulty: str = "متوسط"
    type: str = "سؤال قصير"
    points: int = Field(default=1, ge=1, le=10)

    @field_validator("difficulty")
    @classmethod
    def normalize_difficulty(cls, value: str) -> str:
        value = _ALIASES.get((value or "").strip(), (value or "").strip())
        return value if value in DIFFICULTIES else "متوسط"


class AssessmentSet(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lesson_title: str = ""
    subject: str = ""
    educational_level: str = ""
    kind: str = "formative"
    description: str = ""
    items: List[AssessmentItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def reconcile(self):
        if self.kind not in ASSESSMENT_KINDS:
            self.kind = "formative"
        if not self.description:
            self.description = ASSESSMENT_KINDS[self.kind]
        return self

    @property
    def total_points(self) -> int:
        return sum(item.points for item in self.items)


class AssessmentGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lesson_plan: dict
    kinds: List[str] = Field(default_factory=lambda: ["formative", "summative"])
    count: int = Field(default=6, ge=1, le=20)
    difficulty: str = "متدرج"
    language: str = "ar"

    @field_validator("kinds", mode="before")
    @classmethod
    def normalize_kinds(cls, value: Any):
        if not value:
            return ["formative", "summative"]
        mapping = {"تكويني": "formative", "نهائي": "summative", "formative": "formative", "summative": "summative"}
        result = []
        for item in value:
            key = mapping.get(str(item).strip().lower()) or mapping.get(str(item).strip())
            if key and key not in result:
                result.append(key)
        return result or ["formative", "summative"]


class AssessmentGenerationResponse(BaseModel):
    success: bool
    assessments: List[AssessmentSet] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    model_used: Optional[str] = None
