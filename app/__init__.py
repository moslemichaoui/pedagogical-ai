import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))
    app.config.from_object(config_class)

    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(app.config.get('CHROMA_PERSIST_DIR', 'chromadb_data'), exist_ok=True)

    db.init_app(app)

    # Register models on SQLAlchemy metadata before create_all()
    from app.models import (  # noqa: F401
        User,
        Document,
        DocumentChunk,
        Lesson,
        Exercise,
        Assessment,
        GenerationRequest,
    )

    with app.app_context():
        db.create_all()

    from app.routes.main import bp as main_bp
    from app.routes.documents import bp as documents_bp
    from app.routes.lessons import bp as lessons_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(lessons_bp)

    @app.errorhandler(404)
    def not_found_error(error):
        return "Page not found", 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return "Internal server error", 500

    return app
