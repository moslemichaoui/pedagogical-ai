"""SQLAlchemy models for the pedagogical platform.

The lesson body is stored as one JSON document (``Lesson.content``) rather than
normalised into twenty-one tables. Scalar columns exist only for listing,
filtering and analytics; they are derived from the same payload at save time.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app import db


def utcnow() -> datetime:
    """Naive UTC timestamp, kept for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    """Reserved for future multi-teacher deployments."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120))
    role = db.Column(db.String(50), default="teacher")
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self) -> str:
        return f"<User {self.id} {self.username!r}>"


class Document(db.Model):
    """A reference document used for retrieval-augmented generation."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    source_type = db.Column(db.String(30), default="teacher_upload")
    text_content = db.Column(db.Text)
    page_numbers = db.Column(db.String(1000))
    subject = db.Column(db.String(100))
    educational_level = db.Column(db.String(50))
    language = db.Column(db.String(50), default="ar")
    chapter = db.Column(db.String(255))

    checksum = db.Column(db.String(64), index=True)
    status = db.Column(db.String(20), default="ready", index=True)
    chunk_count = db.Column(db.Integer, default=0)
    file_size = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    chunks = db.relationship(
        "DocumentChunk",
        backref="document",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document {self.id} {self.title!r}>"


class DocumentChunk(db.Model):
    """A retrievable slice of a document."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        db.Index("ix_chunks_document", "document_id"),
        db.UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_index"),
    )

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    chunk_id = db.Column(db.String(100), unique=True, nullable=False)
    chunk_index = db.Column(db.Integer, default=0)
    text = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer)
    subject = db.Column(db.String(100))
    educational_level = db.Column(db.String(50))
    language = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self) -> str:
        return f"<DocumentChunk {self.chunk_id}>"


class Lesson(db.Model):
    """A generated lesson sheet (جذاذة)."""

    __tablename__ = "lessons"
    __table_args__ = (
        db.Index("ix_lessons_created", "created_at"),
        db.Index("ix_lessons_filters", "material", "level"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    topic = db.Column(db.String(300))
    material = db.Column(db.String(100))
    level = db.Column(db.String(30))
    duration = db.Column(db.Integer)
    objectives = db.Column(db.JSON)
    difficulty = db.Column(db.String(30))
    language = db.Column(db.String(50), default="ar")
    reference_documents = db.Column(db.Text)

    content = db.Column(db.JSON)
    status = db.Column(db.String(20), default="ready", index=True)
    model_used = db.Column(db.String(120))
    retrieved_context_count = db.Column(db.Integer, default=0)
    duration_coherent = db.Column(db.Boolean, default=True)
    validation_errors = db.Column(db.JSON)
    validation_warnings = db.Column(db.JSON)
    source_document_ids = db.Column(db.JSON)

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    exercises = db.relationship(
        "Exercise",
        backref="lesson",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="Exercise.order_index",
    )

    def __repr__(self) -> str:
        return f"<Lesson {self.id} {self.title!r}>"


class Exercise(db.Model):
    """One exercise or assessment item belonging to a lesson.

    ``kind`` separates practice exercises from assessment items so the UI can
    present teacher and student views from a single table.
    """

    __tablename__ = "exercises"
    __table_args__ = (
        db.Index("ix_exercises_lesson_kind", "lesson_id", "kind"),
    )

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    kind = db.Column(db.String(20), default="exercise")
    type = db.Column(db.String(60))
    question = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text)
    options = db.Column(db.JSON)
    answer = db.Column(db.Text)
    explanation = db.Column(db.Text)
    objective = db.Column(db.String(300))
    difficulty = db.Column(db.String(30))
    estimated_time = db.Column(db.Integer)
    order_index = db.Column(db.Integer, default=0)
    lesson_reference = db.Column(db.String(300))
    payload = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self) -> str:
        return f"<Exercise {self.id} kind={self.kind}>"


class Assessment(db.Model):
    """Legacy table kept so existing databases keep opening.

    New assessment items are stored in :class:`Exercise` with ``kind`` set to
    ``assessment``.
    """

    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    explanation = db.Column(db.Text)
    objective = db.Column(db.String(200))
    difficulty = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=utcnow)


class GenerationRequest(db.Model):
    """Legacy request log, superseded by :class:`GenerationRun`."""

    __tablename__ = "generation_requests"

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    topic = db.Column(db.String(200))
    level = db.Column(db.String(30))
    subject = db.Column(db.String(100))
    language = db.Column(db.String(50))
    duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=utcnow)


class GenerationRun(db.Model):
    """Telemetry for every generation attempt, successful or not."""

    __tablename__ = "generation_runs"
    __table_args__ = (db.Index("ix_runs_created", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"))
    kind = db.Column(db.String(30), default="lesson")
    request = db.Column(db.JSON)
    status = db.Column(db.String(20), default="ok")
    error_code = db.Column(db.String(80))
    model_used = db.Column(db.String(120))
    latency_ms = db.Column(db.Integer)
    retrieved_context_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utcnow)
