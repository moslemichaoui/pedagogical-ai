"""SQLAlchemy models for the Pedagogical AI platform."""
from datetime import datetime

from app import db


class User(db.Model):
    """User of the platform."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(50), default='teacher')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Document(db.Model):
    """Reference to a stored document (PDF, DOCX, TXT)."""
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    source_type = db.Column(db.String(30))  # official | teacher_upload | web
    text_content = db.Column(db.Text, nullable=True)
    page_numbers = db.Column(db.String(1000))
    subject = db.Column(db.String(100), nullable=True)
    educational_level = db.Column(db.String(50), nullable=True)
    language = db.Column(db.String(50), nullable=True)
    chapter = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    chunks = db.relationship(
        'DocumentChunk',
        backref='document',
        lazy=True,
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', type='{self.source_type}')>"


class DocumentChunk(db.Model):
    """A chunk of text from a document (for RAG/vector storage)."""
    __tablename__ = 'document_chunks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    chunk_id = db.Column(db.String(100), unique=True, nullable=False)
    text = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer, nullable=True)
    subject = db.Column(db.String(100), nullable=True)
    educational_level = db.Column(db.String(50), nullable=True)
    language = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, doc_id={self.document_id}, chunk_id='{self.chunk_id}')>"


class Lesson(db.Model):
    """A complete lesson unit."""
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(300), nullable=False)
    material = db.Column(db.String(100))
    level = db.Column(db.String(30))
    duration = db.Column(db.Integer)
    objectives = db.Column(db.JSON)
    difficulty = db.Column(db.String(30))
    language = db.Column(db.String(50))
    reference_documents = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Lesson(id={self.id}, title='{self.title}', level='{self.level}')>"


class Exercise(db.Model):
    """An exercise within a lesson."""
    __tablename__ = 'exercises'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=True)
    explanation = db.Column(db.Text, nullable=True)
    objective = db.Column(db.String(200))
    difficulty = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Exercise(id={self.id}, lesson_id={self.lesson_id})>"


class Assessment(db.Model):
    """A structured assessment."""
    __tablename__ = 'assessments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=True)
    explanation = db.Column(db.Text, nullable=True)
    objective = db.Column(db.String(200))
    difficulty = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Assessment(id={self.id}, lesson_id={self.lesson_id})>"


class GenerationRequest(db.Model):
    """Request for generating a lesson."""
    __tablename__ = 'generation_requests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    topic = db.Column(db.String(200))
    level = db.Column(db.String(30))
    subject = db.Column(db.String(100))
    language = db.Column(db.String(50))
    duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<GenerationRequest(id={self.id}, lesson_id={self.lesson_id})>"
