"""Flashcard tool — owned by Member C (Question Generator Agent).

Persists generated practice Q/A pairs into a local SQLite database so
they outlive a single run and can be replayed later. Demonstrates
"agent uses a local database" from the rubric.

Schema:
    flashcards(id INTEGER PK, topic TEXT, question TEXT, answer TEXT,
               created_at TIMESTAMP)
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import List, TypedDict

from core.logger import get_logger

_logger = get_logger("tool.flashcard")

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "flashcards.db"


class Flashcard(TypedDict):
    question: str
    answer: str


class FlashcardToolError(RuntimeError):
    """Raised when the SQLite database cannot be opened or written."""


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error as exc:
        raise FlashcardToolError(f"Could not open SQLite DB at {db_path}: {exc}") from exc
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS flashcards (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            topic      TEXT    NOT NULL,
            question   TEXT    NOT NULL,
            answer     TEXT    NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def save_flashcards(
    topic: str,
    cards: List[Flashcard],
    db_path: Path = _DEFAULT_DB,
) -> int:
    """Persist a batch of flashcards under a single topic.

    Args:
        topic: The educational topic these flashcards belong to. Must be non-empty.
        cards: A list of {question, answer} dicts. Empty list is a no-op.
        db_path: Override the default SQLite location (mostly used by tests).

    Returns:
        The number of rows inserted.

    Raises:
        FlashcardToolError: If the database cannot be opened or a row
            cannot be inserted.
        ValueError: If `topic` is empty/whitespace, or if any card is
            missing 'question' or 'answer'.
    """
    if not topic or not topic.strip():
        raise ValueError("topic must be a non-empty string.")
    if not cards:
        _logger.info("save_flashcards: no cards to save for topic=%s", topic)
        return 0

    rows = []
    for idx, card in enumerate(cards):
        q = (card.get("question") or "").strip()
        a = (card.get("answer") or "").strip()
        if not q or not a:
            raise ValueError(
                f"cards[{idx}] is missing a non-empty 'question' or 'answer'."
            )
        rows.append((topic.strip(), q, a))

    with closing(_connect(db_path)) as conn:
        try:
            conn.executemany(
                "INSERT INTO flashcards (topic, question, answer) VALUES (?, ?, ?)",
                rows,
            )
            conn.commit()
        except sqlite3.Error as exc:
            raise FlashcardToolError(f"Failed to insert flashcards: {exc}") from exc

    _logger.info("Saved %d flashcards for topic=%s", len(rows), topic)
    return len(rows)


def load_flashcards(topic: str, db_path: Path = _DEFAULT_DB) -> List[Flashcard]:
    """Retrieve all flashcards previously saved for a given topic.

    Args:
        topic: Topic to filter by. Returns an empty list if topic is
            empty or not found.
        db_path: Override the default SQLite location.

    Returns:
        A list of {question, answer} dicts, oldest first.

    Raises:
        FlashcardToolError: If the database cannot be opened.
    """
    if not topic or not topic.strip():
        return []
    if not Path(db_path).exists():
        return []

    with closing(_connect(db_path)) as conn:
        try:
            cursor = conn.execute(
                "SELECT question, answer FROM flashcards WHERE topic = ? ORDER BY id ASC",
                (topic.strip(),),
            )
            rows = cursor.fetchall()
        except sqlite3.Error as exc:
            raise FlashcardToolError(f"Failed to load flashcards: {exc}") from exc

    return [Flashcard(question=q, answer=a) for q, a in rows]
