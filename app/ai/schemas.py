"""Structured schemas for pedagogical content generation.

The lesson sheet follows the Tunisian primary-school convention: twenty-one
sections, a five-phase session spine, formative and summative assessment, and
source attribution. All fields keep their original English names for API
compatibility; the Arabic labels live in :data:`SECTION_LABELS`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SECTION_LABELS = [
    ("title", "عنوان الدرس"),
    ("subject", "المادة"),
    ("educational_level", "المستوى الدراسي"),
    ("duration", "المدة الزمنية"),
    ("competency", "الكفاءة المستهدفة"),
    ("learning_objectives", "الأهداف التعليمية"),
    ("prerequisites", "المكتسبات السابقة"),
    ("materials", "الوسائل التعليمية"),
    ("key_concepts", "المفاهيم والمصطلحات الأساسية"),
    ("introduction", "وضعية الانطلاق"),
    ("lesson_phases", "مراحل بناء التعلمات"),
    ("teacher_actions", "أنشطة المعلم"),
    ("learner_actions", "أنشطة المتعلم"),
    ("guiding_questions", "الأسئلة التوجيهية"),
    ("experiments", "التجارب أو الأنشطة العلمية"),
    ("examples", "الأمثلة"),
    ("formative_assessment", "التقويم التكويني"),
    ("summative_assessment", "التقويم النهائي"),
    ("remediation", "الدعم والعلاج"),
    ("summary", "خلاصة الدرس"),
    ("homework", "نشاط أو واجب منزلي"),
]

PHASE_SPINE = [
    "التمهيد",
    "وضعية الانطلاق",
    "بناء التعلمات",
    "التقويم",
    "الخلاصة",
]


class ExperimentBlock(BaseModel):
    """A safe, feasible classroom experiment."""

    model_config = ConfigDict(extra="ignore")

    title: str = ""
    materials: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    safety_notes: List[str] = Field(default_factory=list)
    expected_observation: str = ""
    risk_level: str = "منعدم"


class AssessmentItem(BaseModel):
    """One assessment question with its correction."""

    model_config = ConfigDict(extra="ignore")

    question: str = ""
    answer: str = ""
    explanation: str = ""
    objective: str = ""
    difficulty: str = "متوسط"
    type: str = "سؤال قصير"


class AssessmentBlock(BaseModel):
    """A formative or summative assessment blueprint."""

    model_config = ConfigDict(extra="ignore")

    description: str = ""
    items: List[AssessmentItem] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.description.strip() and not self.items


class LessonPhase(BaseModel):
    """One phase of the session, with both actor perspectives."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, description="Phase name in Arabic")
    phase_key: str = Field(default="", description="Spine key, e.g. التمهيد")
    duration: int = Field(..., ge=1, description="Duration in minutes")
    teacher_actions: List[str] = Field(default_factory=list)
    learner_actions: List[str] = Field(default_factory=list)
    guiding_questions: List[str] = Field(default_factory=list)
    expected_responses: List[str] = Field(default_factory=list)
    activities: List[str] = Field(default_factory=list)


class LessonPlan(BaseModel):
    """A complete, printable lesson sheet (جذاذة)."""

    model_config = ConfigDict(extra="ignore")

    # Identity
    title: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    educational_level: str = Field(..., min_length=1)
    duration: int = Field(..., ge=1, le=180)
    competency: str = Field(default="")

    # Preparation
    learning_objectives: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    materials: List[str] = Field(default_factory=list)
    key_concepts: List[str] = Field(default_factory=list)

    # Session
    introduction: str = ""
    lesson_phases: List[LessonPhase] = Field(default_factory=list)
    teacher_actions: List[str] = Field(default_factory=list)
    learner_actions: List[str] = Field(default_factory=list)
    guiding_questions: List[str] = Field(default_factory=list)
    expected_answers: List[str] = Field(default_factory=list)
    activities: List[str] = Field(default_factory=list)
    experiments: List[ExperimentBlock] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)

    # Assessment and closure
    exercises: List[str] = Field(default_factory=list)
    formative_assessment: AssessmentBlock = Field(default_factory=AssessmentBlock)
    summative_assessment: AssessmentBlock = Field(default_factory=AssessmentBlock)
    assessment: str = ""
    remediation: str = ""
    summary: str = ""
    homework: str = ""

    # Provenance
    sources: List[str] = Field(default_factory=list)
    insufficient_sources: bool = False

    @field_validator("experiments", mode="before")
    @classmethod
    def coerce_experiments(cls, value: Any):
        if not value:
            return []
        coerced = []
        for item in value:
            if isinstance(item, str):
                coerced.append({"title": item, "steps": [item]})
            elif isinstance(item, dict):
                coerced.append(item)
        return coerced

    @field_validator("lesson_phases", mode="before")
    @classmethod
    def coerce_phases(cls, value: Any):
        if not value:
            return []
        return [item for item in value if isinstance(item, (dict, LessonPhase))]

    @model_validator(mode="after")
    def fill_derived_fields(self):
        """Keep the legacy free-text ``assessment`` field in sync."""
        blocks = [self.formative_assessment, self.summative_assessment]
        if not self.assessment.strip() and any(not b.is_empty() for b in blocks):
            parts = []
            for label, block in zip(("التقويم التكويني", "التقويم النهائي"), blocks):
                if block.is_empty():
                    continue
                parts.append(label + ": " + (block.description or "").strip())
                for item in block.items:
                    parts.append(f"- {item.question} — {item.answer}")
            self.assessment = "\n".join(part for part in parts if part.strip())
        if not self.examples and self.key_concepts:
            self.examples = []
        return self

    # --- Derived helpers -------------------------------------------------
    def get_total_phase_duration(self) -> int:
        return sum(phase.duration for phase in self.lesson_phases)

    def validate_duration_coherence(self, tolerance: float = 0.1) -> bool:
        if not self.lesson_phases:
            return False
        total = self.get_total_phase_duration()
        return abs(total - self.duration) <= max(1, int(self.duration * tolerance))

    def normalize_durations(self) -> "LessonPlan":
        """Scale phase durations so they sum exactly to the requested time."""
        if not self.lesson_phases:
            return self
        from app.utils.text import scale_durations

        scaled = scale_durations(
            [phase.duration for phase in self.lesson_phases], self.duration
        )
        for phase, minutes in zip(self.lesson_phases, scaled):
            phase.duration = minutes
        return self

    def sections(self) -> List[Dict[str, Any]]:
        """Ordered section list for the document view."""
        return [
            {"key": key, "label": label, "value": getattr(self, key)}
            for key, label in SECTION_LABELS
        ]

    def summary_line(self) -> str:
        return f"{self.subject} · {self.educational_level} · {self.duration} د"


class GenerationRequest(BaseModel):
    """Request for lesson generation."""

    subject: str = Field(..., min_length=1)
    educational_level: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=2, max_length=300)
    duration: int = Field(..., ge=5, le=180)
    objectives: List[str] = Field(default_factory=list)
    difficulty: str = "متوسط"
    language: str = "ar"
    teacher_instructions: Optional[str] = None
    use_documents: bool = True
    source_document_ids: List[int] = Field(default_factory=list)

    @field_validator("objectives", mode="before")
    @classmethod
    def split_objectives(cls, value: Any):
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        return value or []

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        allowed = {"مبتدئ", "سهل", "متوسط", "متقدم", "صعب", "متدرج"}
        return value if value in allowed else "متوسط"

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return value if value in {"ar", "fr", "en"} else "ar"


class GenerationResponse(BaseModel):
    """Response from lesson generation."""

    success: bool
    lesson_plan: Optional[LessonPlan] = None
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retrieved_context_count: int = 0
    duration_coherent: bool = True
    model_used: Optional[str] = None
    lesson_id: Optional[int] = None
    quality: Dict[str, Any] = Field(default_factory=dict)
