"""Lightweight, idempotent schema migrations for SQLite.

``db.create_all()`` creates missing tables but never alters existing ones, so
every additive change to a shipped table is listed here. Each migration checks
the live schema before touching it and is safe to run on every boot.
"""
from __future__ import annotations

from sqlalchemy import inspect, text

from app import db

SCHEMA_VERSION = 1

COLUMNS = {
    "documents": {
        "checksum": "VARCHAR(64)",
        "status": "VARCHAR(20) DEFAULT 'ready'",
        "chunk_count": "INTEGER DEFAULT 0",
        "file_size": "INTEGER DEFAULT 0",
        "error_message": "TEXT",
    },
    "document_chunks": {
        "chunk_index": "INTEGER DEFAULT 0",
    },
    "lessons": {
        "topic": "VARCHAR(300)",
        "content": "JSON",
        "status": "VARCHAR(20) DEFAULT 'ready'",
        "model_used": "VARCHAR(120)",
        "retrieved_context_count": "INTEGER DEFAULT 0",
        "duration_coherent": "BOOLEAN DEFAULT 1",
        "validation_errors": "JSON",
        "validation_warnings": "JSON",
        "source_document_ids": "JSON",
        "updated_at": "DATETIME",
    },
    "exercises": {
        "kind": "VARCHAR(20) DEFAULT 'exercise'",
        "type": "VARCHAR(60)",
        "instructions": "TEXT",
        "options": "JSON",
        "estimated_time": "INTEGER",
        "order_index": "INTEGER DEFAULT 0",
        "lesson_reference": "VARCHAR(300)",
        "payload": "JSON",
    },
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_chunks_document ON document_chunks (document_id)",
    "CREATE INDEX IF NOT EXISTS ix_lessons_created ON lessons (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_lessons_filters ON lessons (material, level)",
    "CREATE INDEX IF NOT EXISTS ix_exercises_lesson_kind ON exercises (lesson_id, kind)",
    "CREATE INDEX IF NOT EXISTS ix_documents_checksum ON documents (checksum)",
    "CREATE INDEX IF NOT EXISTS ix_documents_status ON documents (status)",
]


def _table_names() -> set[str]:
    return set(inspect(db.engine).get_table_names())


def _column_names(table: str) -> set[str]:
    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _add_missing_columns() -> None:
    existing_tables = _table_names()
    for table, columns in COLUMNS.items():
        if table not in existing_tables:
            continue
        present = _column_names(table)
        for name, ddl in columns.items():
            if name in present:
                continue
            with db.engine.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                )


def _create_indexes() -> None:
    with db.engine.begin() as connection:
        for statement in INDEXES:
            try:
                connection.execute(text(statement))
            except Exception:
                # An index on a table that does not exist yet is not fatal;
                # create_all runs again on the next boot.
                continue


def run_migrations() -> None:
    """Create tables, then converge an existing database to the schema."""
    db.create_all()
    if db.engine.dialect.name != "sqlite":
        return
    _add_missing_columns()
    _create_indexes()
    with db.engine.begin() as connection:
        connection.execute(text(f"PRAGMA user_version = {SCHEMA_VERSION}"))

