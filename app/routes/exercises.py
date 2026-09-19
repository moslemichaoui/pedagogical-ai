"""API routes for exercise generation."""
from flask import Blueprint, jsonify, request

from app.ai.exercise_schemas import ExerciseGenerationRequest
from app.services.exercise_generation_service import ExerciseGenerationService

bp = Blueprint("exercises", __name__)


@bp.route("/api/exercises/generate", methods=["POST"])
def generate_exercises():
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                "success": False,
                "error": "Request body is required",
            }), 400

        try:
            generation_request = ExerciseGenerationRequest(**request_data)
        except Exception as exc:
            return jsonify({
                "success": False,
                "error": "Invalid exercise generation request",
                "validation_errors": [str(exc)],
            }), 400

        response = ExerciseGenerationService().generate_exercises(generation_request)

        if response.success:
            return jsonify({
                "success": True,
                "exercise_set": response.exercise_set.model_dump(),
                "validation_errors": response.validation_errors,
            }), 200

        return jsonify({
            "success": False,
            "error": response.error_message,
            "validation_errors": response.validation_errors,
        }), 400

    except Exception as exc:
        return jsonify({
            "success": False,
            "error": f"Exercise generation failed: {exc}",
        }), 500
