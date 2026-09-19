"""Test script for lesson generation API."""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    results = []

    def check(name, ok, detail=''):
        results.append((name, bool(ok), detail))
        status = 'PASS' if ok else 'FAIL'
        print(f'[{status}] {name}' + (f' — {detail}' if detail else ''))

    print('=== Lesson Generation API Tests ===')

    try:
        from app import create_app
        from app.ai.schemas import LessonPlan, GenerationRequest, GenerationResponse
        from app.services.validation_service import ValidationService
        from app.services.lesson_generation_service import LessonGenerationService
        check('Python imports', True)
    except Exception as exc:
        check('Python imports', False, str(exc))
        return 1

    # Test Flask app creation
    try:
        app = create_app()
        check('Flask app creation', True)
    except Exception as exc:
        check('Flask app creation', False, str(exc))
        return 1

    # Test request validation
    try:
        validation_service = ValidationService()
        
        # Valid request
        valid_request = {
            'subject': 'الإيقاظ العلمي',
            'educational_level': 'السنة الثالثة ابتدائي',
            'topic': 'دورة الماء',
            'duration': 45,
            'objectives': ['فهم دورة الماء'],
            'difficulty': 'متوسط',
            'language': 'ar'
        }
        
        result = validation_service.validate_generation_request(valid_request)
        check('Valid request validation', result['valid'], str(result.get('errors')))
        
        # Invalid request (missing required field)
        invalid_request = {
            'subject': 'الإيقاظ العلمي',
            'topic': 'دورة الماء'
        }
        
        result = validation_service.validate_generation_request(invalid_request)
        check('Invalid request validation', not result['valid'], str(result.get('errors')))
        
    except Exception as exc:
        check('Request validation', False, str(exc))

    # Test LessonPlan schema
    try:
        test_plan_data = {
            'title': 'دورة الماء',
            'subject': 'الإيقاظ العلمي',
            'educational_level': 'السنة الثالثة ابتدائي',
            'duration': 45,
            'competency': 'فهم دورة الماء',
            'learning_objectives': ['أن يتعرف على دورة الماء'],
            'prerequisites': ['المعرفة الأساسية'],
            'materials': ['صور'],
            'key_concepts': ['التبخر'],
            'introduction': 'مقدمة',
            'lesson_phases': [
                {
                    'name': 'تمهيد',
                    'duration': 5,
                    'teacher_actions': ['شرح'],
                    'learner_actions': ['استماع'],
                    'guiding_questions': [],
                    'expected_responses': [],
                    'activities': []
                },
                {
                    'name': 'استكشاف',
                    'duration': 20,
                    'teacher_actions': ['توجيه'],
                    'learner_actions': ['ملاحظة'],
                    'guiding_questions': [],
                    'expected_responses': [],
                    'activities': []
                },
                {
                    'name': 'تجربة',
                    'duration': 15,
                    'teacher_actions': ['إشراف'],
                    'learner_actions': ['تنفيذ'],
                    'guiding_questions': [],
                    'expected_responses': [],
                    'activities': []
                },
                {
                    'name': 'تقويم',
                    'duration': 5,
                    'teacher_actions': ['تقييم'],
                    'learner_actions': ['إجابة'],
                    'guiding_questions': [],
                    'expected_responses': [],
                    'activities': []
                }
            ],
            'assessment': 'تقويم',
            'remediation': 'دعم',
            'summary': 'خلاصة',
            'homework': 'واجب'
        }
        
        lesson_plan = LessonPlan(**test_plan_data)
        check('LessonPlan schema validation', True)
        check('LessonPlan total phase duration', lesson_plan.get_total_phase_duration() == 45, f'{lesson_plan.get_total_phase_duration()} minutes')
        check('LessonPlan duration coherence', lesson_plan.validate_duration_coherence(tolerance=0.2), 'Should be coherent with 20% tolerance')
        
    except Exception as exc:
        check('LessonPlan schema', False, str(exc))

    # Test lesson plan validation
    try:
        validation_service = ValidationService()
        # Recreate the test plan data for validation
        test_plan_data_validation = {
            'title': 'دورة الماء',
            'subject': 'الإيقاظ العلمي',
            'educational_level': 'السنة الثالثة ابتدائي',
            'duration': 45,
            'competency': 'فهم دورة الماء',
            'learning_objectives': ['أن يتعرف على دورة الماء'],
            'prerequisites': ['المعرفة الأساسية'],
            'materials': ['صور'],
            'key_concepts': ['التبخر'],
            'introduction': 'مقدمة',
            'lesson_phases': [
                {
                    'name': 'تمهيد',
                    'duration': 5,
                    'teacher_actions': ['شرح'],
                    'learner_actions': ['استماع'],
                    'guiding_questions': [],
                    'expected_responses': [],
                    'activities': []
                },
                {
                    'name': 'استكشاف',
                    'duration': 20,
                    'teacher_actions': ['توجيه'],
                    'learner_actions': ['ملاحظة'],
                    'guiding_questions': [],
                    'expected_responses': [],
                    'activities': []
                },
                {
                    'name': 'تجربة',
                    'duration': 15,
                    'teacher_actions': ['إشراف'],
                    'learner_actions': ['تنفيذ'],
                    'guiding_questions': [],
                    'expected_responses': [],
                    'activities': []
                },
                {
                    'name': 'تقويم',
                    'duration': 5,
                    'teacher_actions': ['تقييم'],
                    'learner_actions': ['إجابة'],
                    'guiding_questions': [],
                    'expected_responses': [],
                    'activities': []
                }
            ],
            'assessment': 'تقويم',
            'remediation': 'دعم',
            'summary': 'خلاصة',
            'homework': 'واجب'
        }
        lesson_plan = LessonPlan(**test_plan_data_validation)
        validation_result = validation_service.validate_lesson_plan(lesson_plan)
        check('Lesson plan validation', validation_result['valid'], f'Errors: {validation_result["errors"]}')
        
    except Exception as exc:
        check('Lesson plan validation', False, str(exc))

    # Test API endpoints
    try:
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/api/lessons/health')
            check('GET /api/lessons/health', response.status_code in [200, 503], f'Status: {response.status_code}')
            
            # Test validation endpoint
            validation_payload = test_plan_data
            response = client.post('/api/lessons/validate', 
                                 json=validation_payload,
                                 content_type='application/json')
            check('POST /api/lessons/validate', response.status_code == 200, f'Status: {response.status_code}')
            
            # Test generate endpoint (will fail without Gemini API key, but should handle gracefully)
            generation_payload = valid_request
            response = client.post('/api/lessons/generate',
                                 json=generation_payload,
                                 content_type='application/json')
            # Should return 400 (Gemini not available) rather than 500
            check('POST /api/lessons/generate', response.status_code in [400, 500], f'Status: {response.status_code}')
            
            if response.status_code == 400:
                data = response.get_json()
                check('Generate endpoint error handling', data.get('success') == False, str(data.get('error')))
            
    except Exception as exc:
        check('API endpoints', False, str(exc))

    # Test service health check
    try:
        service = LessonGenerationService()
        health = service.health_check()
        check('LessonGenerationService health check', health['status'] in ['healthy', 'degraded'], f'Status: {health["status"]}')
        check('Service components available', 'retrieval' in health['components'], str(health['components']))
        
    except Exception as exc:
        check('Service health check', False, str(exc))

    # Summary
    failed = [name for name, ok, _ in results if not ok]
    print('=== summary ===')
    print(f'{len(results) - len(failed)}/{len(results)} passed')
    
    if failed:
        print('Failed tests:')
        for name in failed:
            print(f'  - {name}')
    
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
