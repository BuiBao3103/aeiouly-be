#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to import listening lessons and their sentences into the database.
"""
import json
import sys
import os
import codecs
from datetime import datetime, timezone

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Add project root to Python path so src.* imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models so SQLAlchemy metadata is registered
import src.models  # noqa: F401

from sqlalchemy import create_engine, text
from src.config import get_database_url


DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "listening_lessons_data.json")


def parse_datetime(value: str) -> datetime:
    """Parse ISO datetime strings with optional Z suffix."""
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_lessons() -> list:
    """Load lessons from the JSON data file."""
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"Data file not found: {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "lessons" in data:
        lessons = data["lessons"]
    elif isinstance(data, list):
        lessons = data
    else:
        raise ValueError("Unexpected JSON format. Expected a list or an object with 'lessons'.")

    if not lessons:
        raise ValueError("No lessons found in JSON file.")
    return lessons


def import_listening_lessons():
    """Import lessons and sentences into the database."""
    lessons = load_lessons()
    database_url = get_database_url()
    engine = create_engine(database_url)

    with engine.begin() as conn:
        print(f"📥 Importing {len(lessons)} listening lesson(s)...")
        for lesson in lessons:
            lesson_id = lesson["id"]

            existing = conn.execute(
                text("SELECT COUNT(*) FROM listen_lessons WHERE id = :id"),
                {"id": lesson_id},
            ).scalar()
            if existing:
                print(f"ℹ️  Lesson #{lesson_id} already exists. Skipping.")
                continue

            created_at = parse_datetime(lesson.get("created_at"))
            updated_at = parse_datetime(lesson.get("updated_at"))

            conn.execute(
                text(
                    """
                    INSERT INTO listen_lessons
                    (id, title, youtube_url, level, total_sentences, created_at, updated_at, deleted_at)
                    VALUES (:id, :title, :youtube_url, :level, :total_sentences, :created_at, :updated_at, NULL)
                    """
                ),
                {
                    "id": lesson_id,
                    "title": lesson["title"],
                    "youtube_url": lesson["youtube_url"],
                    "level": lesson["level"],
                    "total_sentences": lesson.get("total_sentences", len(lesson.get("sentences", []))),
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            )

            sentences = lesson.get("sentences", [])
            if not sentences:
                print(f"⚠️  Lesson #{lesson_id} has no sentences in data file.")
                continue

            existing_sentences = conn.execute(
                text("SELECT COUNT(*) FROM sentences WHERE lesson_id = :lesson_id"),
                {"lesson_id": lesson_id},
            ).scalar()
            if existing_sentences:
                print(f"ℹ️  Sentences for lesson #{lesson_id} already exist. Skipping sentence import.")
                continue

            for sentence in sentences:
                conn.execute(
                    text(
                        """
                        INSERT INTO sentences
                        (id, lesson_id, "index", text, translation, start_time, end_time, confidence, created_at, updated_at, deleted_at)
                        VALUES (:id, :lesson_id, :index, :text, :translation, :start_time, :end_time, :confidence, :created_at, :updated_at, NULL)
                        """
                    ),
                    {
                        "id": sentence["id"],
                        "lesson_id": lesson_id,
                        "index": sentence["index"],
                        "text": sentence["text"],
                        "translation": sentence.get("translation"),
                        "start_time": sentence.get("start_time"),
                        "end_time": sentence.get("end_time"),
                        "confidence": sentence.get("confidence"),
                        "created_at": created_at,
                        "updated_at": updated_at,
                    },
                )

            print(f"✅ Imported lesson #{lesson_id} with {len(sentences)} sentence(s).")

        print("🎉 Listening lessons import completed!")


def main():
    try:
        import_listening_lessons()
    except Exception as exc:
        print(f"❌ Error importing listening lessons: {exc}")
        raise


if __name__ == "__main__":
    main()


