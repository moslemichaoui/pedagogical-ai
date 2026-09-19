"""Service for validating pedagogical content quality and completeness."""
from typing import List, Dict, Any, Optional
from app.ai.schemas import LessonPlan


class ValidationService:
    """Service for validating lesson plans and pedagogical content."""
    
    def validate_lesson_plan(self, lesson_plan: LessonPlan) -> Dict[str, Any]:
        """Validate a complete lesson plan and return validation results."""
        errors = []
        warnings = []
        
        # Validate required fields
        errors.extend(self._validate_required_fields(lesson_plan))
        
        # Validate Arabic content
        errors.extend(self._validate_arabic_content(lesson_plan))
        
        # Validate duration coherence
        duration_result = self._validate_duration_coherence(lesson_plan)
        if not duration_result['valid']:
            errors.extend(duration_result['errors'])
        else:
            warnings.extend(duration_result['warnings'])
        
        # Validate pedagogical completeness
        errors.extend(self._validate_pedagogical_completeness(lesson_plan))
        
        # Validate lesson phases
        errors.extend(self._validate_lesson_phases(lesson_plan))
        
        # Validate safety
        errors.extend(self._validate_safety(lesson_plan))
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'error_count': len(errors),
            'warning_count': len(warnings)
        }
    
    def _validate_required_fields(self, lesson_plan: LessonPlan) -> List[str]:
        """Validate that all required fields are present and non-empty."""
        errors = []
        
        required_fields = {
            'title': lesson_plan.title,
            'subject': lesson_plan.subject,
            'educational_level': lesson_plan.educational_level,
            'duration': lesson_plan.duration,
            'competency': lesson_plan.competency,
        }
        
        for field_name, field_value in required_fields.items():
            if not field_value or (isinstance(field_value, str) and not field_value.strip()):
                errors.append(f"Required field '{field_name}' is missing or empty")
        
        return errors
    
    def _validate_arabic_content(self, lesson_plan: LessonPlan) -> List[str]:
        """Validate that Arabic content is present and appears authentic."""
        errors = []
        
        # Check for Arabic characters in key fields
        arabic_fields = {
            'title': lesson_plan.title,
            'subject': lesson_plan.subject,
            'competency': lesson_plan.competency,
            'introduction': lesson_plan.introduction,
            'summary': lesson_plan.summary,
        }
        
        arabic_char_count = 0
        for field_name, field_value in arabic_fields.items():
            if field_value and self._contains_arabic(field_value):
                arabic_char_count += 1
        
        if arabic_char_count < 3:
            errors.append("Insufficient Arabic content in key fields. At least title, subject, and competency should be in Arabic.")
        
        # Check learning objectives for Arabic
        if lesson_plan.learning_objectives:
            arabic_objectives = sum(1 for obj in lesson_plan.learning_objectives if self._contains_arabic(obj))
            if arabic_objectives == 0:
                errors.append("Learning objectives should be in Arabic")
        
        return errors
    
    def _validate_duration_coherence(self, lesson_plan: LessonPlan) -> Dict[str, Any]:
        """Validate that lesson phase durations are coherent with total duration."""
        errors = []
        warnings = []
        
        if not lesson_plan.lesson_phases:
            errors.append("No lesson phases defined")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        total_phase_duration = lesson_plan.get_total_phase_duration()
        requested_duration = lesson_plan.duration
        
        # Check if phases have zero duration
        zero_duration_phases = [i for i, phase in enumerate(lesson_plan.lesson_phases) if phase.duration == 0]
        if zero_duration_phases:
            errors.append(f"Lesson phases {zero_duration_phases} have zero duration")
        
        # Check duration coherence with 20% tolerance
        tolerance = 0.2
        lower_bound = requested_duration * (1 - tolerance)
        upper_bound = requested_duration * (1 + tolerance)
        
        if total_phase_duration < lower_bound:
            errors.append(
                f"Total phase duration ({total_phase_duration} min) is significantly less than requested duration ({requested_duration} min)"
            )
        elif total_phase_duration > upper_bound:
            warnings.append(
                f"Total phase duration ({total_phase_duration} min) exceeds requested duration ({requested_duration} min) by more than 20%"
            )
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_pedagogical_completeness(self, lesson_plan: LessonPlan) -> List[str]:
        """Validate that the lesson plan contains essential pedagogical components."""
        errors = []
        
        # Check learning objectives
        if not lesson_plan.learning_objectives:
            errors.append("Learning objectives are missing")
        elif len(lesson_plan.learning_objectives) < 1:
            errors.append("At least one learning objective is required")
        
        # Check prerequisites
        if not lesson_plan.prerequisites:
            errors.append("Prerequisites are missing")
        
        # Check materials
        if not lesson_plan.materials:
            errors.append("Teaching materials are missing")
        
        # Check key concepts
        if not lesson_plan.key_concepts:
            errors.append("Key concepts and terminology are missing")
        
        # Check assessment
        if not lesson_plan.assessment or not lesson_plan.assessment.strip():
            errors.append("Assessment methods are missing")
        
        # Check remediation
        if not lesson_plan.remediation or not lesson_plan.remediation.strip():
            errors.append("Remediation and support activities are missing")
        
        # Check summary
        if not lesson_plan.summary or not lesson_plan.summary.strip():
            errors.append("Lesson summary is missing")
        
        # Check homework
        if not lesson_plan.homework or not lesson_plan.homework.strip():
            errors.append("Homework or follow-up activities are missing")
        
        return errors
    
    def _validate_lesson_phases(self, lesson_plan: LessonPlan) -> List[str]:
        """Validate that lesson phases are properly structured."""
        errors = []
        
        if not lesson_plan.lesson_phases:
            errors.append("No lesson phases defined")
            return errors
        
        for i, phase in enumerate(lesson_plan.lesson_phases):
            if not phase.name or not phase.name.strip():
                errors.append(f"Phase {i+1} is missing a name")
            
            if phase.duration <= 0:
                errors.append(f"Phase {i+1} has invalid duration: {phase.duration}")
            
            if not phase.teacher_actions:
                errors.append(f"Phase {i+1} is missing teacher actions")
            
            if not phase.learner_actions:
                errors.append(f"Phase {i+1} is missing learner actions")
        
        return errors
    
    def _validate_safety(self, lesson_plan: LessonPlan) -> List[str]:
        """Validate that experiments and activities are safe."""
        errors = []
        
        # More specific dangerous keywords to avoid false positives
        really_dangerous_keywords = [
            'انفجار', 'سمم', 'تسمم', 'حارق', 'تحريق',
            'explosive', 'poison', 'toxic', 'acid burn', 'set fire'
        ]
        
        for experiment in lesson_plan.experiments:
            experiment_lower = experiment.lower()
            for keyword in really_dangerous_keywords:
                if keyword in experiment_lower:
                    errors.append(f"Potentially dangerous content in experiment: '{experiment[:50]}...'")
                    break
        
        for activity in lesson_plan.activities:
            activity_lower = activity.lower()
            for keyword in really_dangerous_keywords:
                if keyword in activity_lower:
                    errors.append(f"Potentially dangerous content in activity: '{activity[:50]}...'")
                    break
        
        return errors
        
        return errors
    
    def _contains_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters."""
        if not text:
            return False
        
        # Arabic Unicode range
        for char in text:
            if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F':
                return True
        return False
    
    def validate_generation_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a lesson generation request."""
        errors = []
        
        required_fields = ['subject', 'educational_level', 'topic', 'duration']
        for field in required_fields:
            if field not in request_data or not request_data[field]:
                errors.append(f"Required field '{field}' is missing")
        
        if 'duration' in request_data:
            duration = request_data['duration']
            if not isinstance(duration, int) or duration < 5 or duration > 180:
                errors.append("Duration must be an integer between 5 and 180 minutes")
        
        if 'language' in request_data and request_data['language'] not in ['ar', 'fr', 'en']:
            errors.append("Language must be one of: ar, fr, en")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
