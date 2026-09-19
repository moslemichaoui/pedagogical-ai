"""Service for generating lesson plans using RAG and AI."""
import json
import logging
from typing import Dict, Any, List, Optional

from app.ai.schemas import LessonPlan, GenerationRequest, GenerationResponse
from app.ai.prompts import SYSTEM_PROMPT, build_lesson_generation_prompt
from app.ai.gemini_provider import GeminiProvider
from app.services.retrieval_service import RetrievalService
from app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)


class LessonGenerationService:
    """Service for generating lesson plans using RAG retrieval and AI generation."""
    
    def __init__(self):
        self.retrieval_service = RetrievalService()
        self.gemini_provider = GeminiProvider()
        self.validation_service = ValidationService()
    
    def generate_lesson(self, request: GenerationRequest) -> GenerationResponse:
        """Generate a complete lesson plan based on teacher request."""
        
        try:
            # Step 1: Retrieve relevant educational context
            logger.info(f"Retrieving context for topic: {request.topic}")
            retrieved_context = self._retrieve_context(request)
            
            # Step 2: Build the generation prompt
            logger.info("Building generation prompt")
            prompt = build_lesson_generation_prompt(
                subject=request.subject,
                educational_level=request.educational_level,
                topic=request.topic,
                duration=request.duration,
                objectives=request.objectives,
                difficulty=request.difficulty,
                language=request.language,
                retrieved_context=retrieved_context,
                teacher_instructions=request.teacher_instructions
            )
            
            # Step 3: Generate lesson plan using Gemini
            logger.info("Calling Gemini for lesson generation")
            full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
            
            try:
                response_text = self.gemini_provider.generate(
                    prompt=full_prompt
                )
            except RuntimeError as e:
                # Gemini not available
                logger.warning(f"Gemini provider not available: {e}")
                return GenerationResponse(
                    success=False,
                    error_message=f"Gemini API not available: {str(e)}",
                    retrieved_context_count=len(retrieved_context)
                )
            
            # Step 4: Parse JSON response
            logger.info("Parsing Gemini response")
            lesson_plan_dict = self._parse_json_response(response_text)
            
            if lesson_plan_dict is None:
                return GenerationResponse(
                    success=False,
                    error_message="Failed to parse valid JSON from Gemini response",
                    retrieved_context_count=len(retrieved_context)
                )
            
            # Step 5: Validate and create LessonPlan
            logger.info("Validating lesson plan structure")
            try:
                lesson_plan = LessonPlan(**lesson_plan_dict)
            except Exception as e:
                return GenerationResponse(
                    success=False,
                    error_message=f"Lesson plan validation failed: {str(e)}",
                    retrieved_context_count=len(retrieved_context)
                )
            
            # Step 6: Validate pedagogical quality
            logger.info("Validating pedagogical quality")
            validation_result = self.validation_service.validate_lesson_plan(lesson_plan)
            
            # Step 7: Check duration coherence
            duration_coherent = lesson_plan.validate_duration_coherence(tolerance=0.2)
            
            # Step 8: Return response
            return GenerationResponse(
                success=validation_result['valid'],
                lesson_plan=lesson_plan,
                validation_errors=validation_result['errors'],
                error_message=None if validation_result['valid'] else "Pedagogical validation failed",
                retrieved_context_count=len(retrieved_context),
                duration_coherent=duration_coherent
            )
            
        except Exception as e:
            logger.error(f"Lesson generation failed: {e}", exc_info=True)
            return GenerationResponse(
                success=False,
                error_message=f"Lesson generation failed: {str(e)}",
                retrieved_context_count=0
            )
    
    def _retrieve_context(self, request: GenerationRequest) -> List[Dict[str, Any]]:
        """Retrieve relevant educational context using RAG."""
        try:
            # Build retrieval query
            topic = request.topic
            subject = request.subject
            educational_level = request.educational_level
            language = request.language
            
            # Use retrieval service
            results = self.retrieval_service.retrieve(
                subject=subject,
                educational_level=educational_level,
                topic=topic,
                language=language,
                n_results=5
            )
            
            logger.info(f"Retrieved {len(results)} context chunks")
            return results
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}", exc_info=True)
            return []
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from Gemini response, handling various formats."""
        if not response_text:
            return None
        
        try:
            # Try direct JSON parsing first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            try:
                # Look for ```json ... ``` or ``` ... ```
                if '```' in response_text:
                    # Extract content between code blocks
                    lines = response_text.split('\n')
                    json_lines = []
                    in_json_block = False
                    
                    for line in lines:
                        if '```json' in line or '```' in line:
                            in_json_block = not in_json_block
                            continue
                        if in_json_block:
                            json_lines.append(line)
                    
                    if json_lines:
                        json_text = '\n'.join(json_lines)
                        return json.loads(json_text)
            except json.JSONDecodeError:
                pass
            
            # Try to find JSON by looking for { and }
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            logger.error("Failed to parse JSON from response")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the lesson generation service."""
        health = {
            'service': 'lesson_generation',
            'status': 'healthy',
            'components': {}
        }
        
        # Check retrieval service
        try:
            health['components']['retrieval'] = 'available'
        except Exception as e:
            health['components']['retrieval'] = f'unavailable: {str(e)}'
            health['status'] = 'degraded'
        
        # Check Gemini provider
        try:
            gemini_health = self.gemini_provider.health_check()
            health['components']['gemini'] = gemini_health['status']
            if gemini_health['status'] != 'healthy':
                health['status'] = 'degraded'
        except Exception as e:
            health['components']['gemini'] = f'unavailable: {str(e)}'
            health['status'] = 'degraded'
        
        # Check validation service
        try:
            health['components']['validation'] = 'available'
        except Exception as e:
            health['components']['validation'] = f'unavailable: {str(e)}'
            health['status'] = 'degraded'
        
        return health
