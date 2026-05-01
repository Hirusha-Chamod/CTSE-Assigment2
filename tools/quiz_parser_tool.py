"""Quiz parser tool — owned by Member A (Assessment Agent).

Reads a local JSON file containing a student's quiz attempt, validates
its shape, and computes per-topic accuracy. Returns the topic with the
*lowest* accuracy as the candidate "weak topic" to investigate.

Sample expected input shape (data/sample_quiz.json):

    {
      "student": "Alice",
      "answers": [
        {"topic": "Calculus",       "correct": false},
        {"topic": "Linear Algebra", "correct": true},
        {"topic": "Calculus",       "correct": false},
        ...
      ]
    }
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, TypedDict

from core.logger import get_logger

_logger = get_logger("tool.quiz_parser")


class TopicScore(TypedDict):
    topic: str
    correct: int
    total: int
    accuracy: float


class QuizSummary(TypedDict):
    student: str
    weakest_topic: str
    weakest_accuracy: float
    per_topic: List[TopicScore]


class QuizParseError(ValueError):
    """Raised when the quiz file is missing, malformed, or empty."""


def parse_quiz_file(path: str) -> QuizSummary:
    """Parse a quiz JSON file and identify the student's weakest topic.

    Args:
        path: Filesystem path to a JSON file shaped like the module docstring.

    Returns:
        QuizSummary with the student's name, the weakest topic, that
        topic's accuracy in [0.0, 1.0], and per-topic breakdown.

    Raises:
        QuizParseError: If the file is missing, is not valid JSON, has no
            `answers` list, has an empty answers list, or contains an
            answer entry that is missing the required keys.
    """
    quiz_path = Path(path)
    _logger.info("Parsing quiz file: %s", quiz_path)

    if not quiz_path.is_file():
        raise QuizParseError(f"Quiz file not found: {quiz_path}")

    try:
        raw = quiz_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QuizParseError(f"Quiz file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise QuizParseError(f"Could not read quiz file: {exc}") from exc

    if not isinstance(data, dict):
        raise QuizParseError("Quiz JSON root must be an object.")

    answers = data.get("answers")
    if not isinstance(answers, list) or not answers:
        raise QuizParseError("Quiz JSON must contain a non-empty 'answers' list.")

    student = str(data.get("student") or "Anonymous")

    tally: Dict[str, List[int]] = defaultdict(lambda: [0, 0])  # [correct, total]
    for idx, item in enumerate(answers):
        if not isinstance(item, dict) or "topic" not in item or "correct" not in item:
            raise QuizParseError(
                f"answers[{idx}] must be an object with 'topic' and 'correct' keys."
            )
        topic = str(item["topic"]).strip()
        if not topic:
            raise QuizParseError(f"answers[{idx}].topic must be non-empty.")
        tally[topic][1] += 1
        if bool(item["correct"]):
            tally[topic][0] += 1

    per_topic: List[TopicScore] = [
        TopicScore(
            topic=topic,
            correct=correct,
            total=total,
            accuracy=correct / total if total else 0.0,
        )
        for topic, (correct, total) in tally.items()
    ]
    per_topic.sort(key=lambda t: (t["accuracy"], -t["total"]))

    weakest = per_topic[0]
    summary = QuizSummary(
        student=student,
        weakest_topic=weakest["topic"],
        weakest_accuracy=weakest["accuracy"],
        per_topic=per_topic,
    )
    _logger.info(
        "Quiz parsed: student=%s weakest=%s acc=%.2f topics=%d",
        student, weakest["topic"], weakest["accuracy"], len(per_topic),
    )
    return summary


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "data/sample_quiz.json"
    print(json.dumps(parse_quiz_file(target), indent=2))
