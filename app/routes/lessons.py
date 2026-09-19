"""API routes for lesson generation and management."""
from flask import Blueprint, jsonify, request

from app.ai.schemas import GenerationRequest, GenerationResponse
from app.services.lesson_generation_service import LessonGenerationService
from app.services.validation_service import ValidationService

bp = Blueprint('lessons', __name__)


@bp.route('/api/lessons/generate', methods=['POST'])
def generate_lesson():
    """Generate a lesson plan based on teacher request."""
    
    try:
        # Parse request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Validate request
        validation_service = ValidationService()
        request_validation = validation_service.validate_generation_request(request_data)
        
        if not request_validation['valid']:
            return jsonify({
                'success': False,
                'error': 'Invalid request',
                'validation_errors': request_validation['errors']
            }), 400
        
        # Create generation request
        try:
            generation_request = GenerationRequest(**request_data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Invalid request format: {str(e)}'
            }), 400
        
        # Generate lesson
        service = LessonGenerationService()
        response = service.generate_lesson(generation_request)
        
        # Return response
        if response.success:
            return jsonify({
                'success': True,
                'lesson_plan': response.lesson_plan.model_dump() if response.lesson_plan else None,
                'validation_errors': response.validation_errors,
                'retrieved_context_count': response.retrieved_context_count,
                'duration_coherent': response.duration_coherent
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': response.error_message,
                'validation_errors': response.validation_errors,
                'retrieved_context_count': response.retrieved_context_count
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Lesson generation failed: {str(e)}'
        }), 500


@bp.route('/api/lessons/health', methods=['GET'])
def lesson_generation_health():
    """Health check endpoint for lesson generation service."""
    try:
        service = LessonGenerationService()
        health = service.health_check()
        return jsonify(health), 200 if health['status'] == 'healthy' else 503
    except Exception as e:
        return jsonify({
            'service': 'lesson_generation',
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@bp.route('/api/lessons/validate', methods=['POST'])
def validate_lesson():
    """Validate a lesson plan without generating."""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Try to parse as LessonPlan
        from app.ai.schemas import LessonPlan
        try:
            lesson_plan = LessonPlan(**request_data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Invalid lesson plan format: {str(e)}'
            }), 400
        
        # Validate
        validation_service = ValidationService()
        validation_result = validation_service.validate_lesson_plan(lesson_plan)
        
        return jsonify({
            'success': validation_result['valid'],
            'validation_errors': validation_result['errors'],
            'warnings': validation_result['warnings'],
            'error_count': validation_result['error_count'],
            'warning_count': validation_result['warning_count']
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Validation failed: {str(e)}'
        }), 500
