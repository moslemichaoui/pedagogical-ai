"""Dashboard and reporting aggregates."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func

from app import db
from app.models import Document, DocumentChunk, Exercise, GenerationRun, Lesson
from app.services.lesson_service import LessonService


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


class AnalyticsService:
    @staticmethod
    def overview() -> Dict[str, Any]:
        lessons = Lesson.query.count()
        documents = Document.query.filter_by(status="ready").count()
        chunks = DocumentChunk.query.count()
        exercises = Exercise.query.filter_by(kind="exercise").count()
        assessments = Exercise.query.filter_by(kind="assessment").count()
        week_runs = GenerationRun.query.filter(GenerationRun.created_at >= _since(7)).all()
        success = sum(1 for run in week_runs if run.status == "ok")
        return {
            "lessons": lessons,
            "documents": documents,
            "chunks": chunks,
            "exercises": exercises,
            "assessments": assessments,
            "runs_week": len(week_runs),
            "success_rate": round(success / len(week_runs) * 100) if week_runs else None,
            "avg_latency_ms": round(
                sum(run.latency_ms or 0 for run in week_runs) / len(week_runs)
            )
            if week_runs
            else None,
        }

    @staticmethod
    def subject_breakdown() -> List[Dict[str, Any]]:
        rows = (
            db.session.query(Lesson.material, func.count(Lesson.id))
            .group_by(Lesson.material)
            .order_by(func.count(Lesson.id).desc())
            .all()
        )
        total = sum(count for _, count in rows) or 1
        return [
            {
                "subject": subject or "غير محدد",
                "count": count,
                "share": round(count / total * 100),
            }
            for subject, count in rows
        ]

    @staticmethod
    def recent_lessons(limit: int = 5) -> List[Dict[str, Any]]:
        lessons = Lesson.query.order_by(Lesson.created_at.desc()).limit(limit).all()
        return [LessonService.serialize(lesson) for lesson in lessons]

    @staticmethod
    def recent_documents(limit: int = 5) -> List[Dict[str, Any]]:
        from app.services.document_service import DocumentService

        documents = Document.query.order_by(Document.created_at.desc()).limit(limit).all()
        return [DocumentService.serialize(document) for document in documents]

    @staticmethod
    def level_breakdown() -> List[Dict[str, Any]]:
        rows = (
            db.session.query(Lesson.level, func.count(Lesson.id))
            .group_by(Lesson.level)
            .all()
        )
        return [{"level": level or "غير محدد", "count": count} for level, count in rows]

    @staticmethod
    def activity_by_day(days: int = 14) -> List[Dict[str, Any]]:
        start = _since(days)
        lessons = Lesson.query.filter(Lesson.created_at >= start).all()
        buckets: Counter[str] = Counter()
        for lesson in lessons:
            if lesson.created_at:
                buckets[lesson.created_at.strftime("%Y-%m-%d")] += 1
        return [
            {"date": (start + timedelta(days=offset)).strftime("%Y-%m-%d"),
             "count": buckets[(start + timedelta(days=offset)).strftime("%Y-%m-%d")]}
            for offset in range(days + 1)
        ]
