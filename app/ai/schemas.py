"""Structured schemas for pedagogical content generation."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class LessonPhase(BaseModel):
    """A single phase of the lesson with duration and activities."""
    name: str = Field(..., description="Name of the lesson phase")
    duration: int = Field(..., ge=1, description="Duration in minutes")
    teacher_actions: List[str] = Field(default_factory=list, description="Actions performed by the teacher")
    learner_actions: List[str] = Field(default_factory=list, description="Actions performed by learners")
    guiding_questions: List[str] = Field(default_factory=list, description="Questions to guide the phase")
    expected_responses: List[str] = Field(default_factory=list, description="Expected responses from learners")
    activities: List[str] = Field(default_factory=list, description="Activities conducted in this phase")


class LessonPlan(BaseModel):
    """Structured lesson plan for pedagogical content generation."""
    
    # Basic information
    title: str = Field(..., description="Lesson title")
    subject: str = Field(..., description="Subject (e.g., الإيقاظ العلمي)")
    educational_level: str = Field(..., description="Educational level (e.g., السنة الثالثة ابتدائي)")
    duration: int = Field(..., ge=1, description="Total lesson duration in minutes")
    competency: str = Field(..., description="Target competency")
    
    # Learning components
    learning_objectives: List[str] = Field(default_factory=list, description="Learning objectives")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites and prior knowledge")
    materials: List[str] = Field(default_factory=list, description="Teaching materials and resources")
    key_concepts: List[str] = Field(default_factory=list, description="Key concepts and terminology")
    
    # Lesson structure
    introduction: str = Field(default="", description="Introduction and situation de départ")
    lesson_phases: List[LessonPhase] = Field(default_factory=list, description="Structured lesson phases")
    
    # Teaching and learning activities
    teacher_actions: List[str] = Field(default_factory=list, description="General teacher actions throughout the lesson")
    learner_actions: List[str] = Field(default_factory=list, description="General learner actions throughout the lesson")
    guiding_questions: List[str] = Field(default_factory=list, description="Guiding questions for the lesson")
    expected_answers: List[str] = Field(default_factory=list, description="Expected answers to guiding questions")
    
    # Activities and experiments
    activities: List[str] = Field(default_factory=list, description="Classroom activities")
    experiments: List[str] = Field(default_factory=list, description="Scientific experiments when appropriate")
    
    # Assessment and support
    exercises: List[str] = Field(default_factory=list, description="Exercises for practice")
    assessment: str = Field(default="", description="Assessment methods and questions")
    remediation: str = Field(default="", description="Support and remediation activities")
    
    # Conclusion
    summary: str = Field(default="", description="Lesson summary and synthesis")
    homework: str = Field(default="", description="Homework or follow-up activities")
    
    # Sources
    sources: List[str] = Field(default_factory=list, description="Source documents and references")
    
    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v: int) -> int:
        """Ensure duration is reasonable for a lesson."""
        if v < 5:
            raise ValueError("Duration must be at least 5 minutes")
        if v > 180:
            raise ValueError("Duration cannot exceed 180 minutes (3 hours)")
        return v
    
    @field_validator('lesson_phases')
    @classmethod
    def validate_phases_duration(cls, v: List[LessonPhase]) -> List[LessonPhase]:
        """Ensure total phase duration matches lesson duration approximately."""
        if not v:
            return v
        
        total_phase_duration = sum(phase.duration for phase in v)
        # Allow 20% tolerance
        if total_phase_duration == 0:
            raise ValueError("Phase durations cannot be zero")
        
        return v
    
    def get_total_phase_duration(self) -> int:
        """Calculate total duration of all phases."""
        return sum(phase.duration for phase in self.lesson_phases)
    
    def validate_duration_coherence(self, tolerance: float = 0.2) -> bool:
        """Check if total phase duration is coherent with lesson duration."""
        if not self.lesson_phases:
            return True
        
        total = self.get_total_phase_duration()
        lower_bound = self.duration * (1 - tolerance)
        upper_bound = self.duration * (1 + tolerance)
        
        return lower_bound <= total <= upper_bound


class GenerationRequest(BaseModel):
    """Request for lesson generation."""
    subject: str = Field(..., description="Subject (e.g., الإيقاظ العلمي)")
    educational_level: str = Field(..., description="Educational level")
    topic: str = Field(..., description="Lesson topic")
    duration: int = Field(..., ge=5, le=180, description="Duration in minutes")
    objectives: List[str] = Field(default_factory=list, description="Learning objectives")
    difficulty: str = Field(default="متوسط", description="Difficulty level")
    language: str = Field(default="ar", description="Language code (e.g., ar, fr)")
    teacher_instructions: Optional[str] = Field(None, description="Additional teacher instructions")


class GenerationResponse(BaseModel):
    """Response from lesson generation."""
    success: bool
    lesson_plan: Optional[LessonPlan] = None
    validation_errors: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    retrieved_context_count: int = 0
    duration_coherent: bool = True
