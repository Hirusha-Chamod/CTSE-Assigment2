"""Question Generator Agent — owned by Member C.

Persona: Practice Question Author.
Responsibility: Given the topic and the Gap Analyst's 3-bullet brief,
produce 5 short Q/A pairs and persist them via `flashcard_tool` so they
survive across runs (demonstrating local DB usage).

Output format is enforced by the system prompt: a JSON array of objects
with `question` and `answer` keys. The agent re-parses to fail-fast on
malformed model output.
"""
from __future__ import annotations

import json
import re
from typing import List

from core.llm import ollama_chat
from core.logger import get_logger
from core.state import PracticeQuestion, StudyState
from tools.flashcard_tool import Flashcard, save_flashcards

_logger = get_logger("agent.question_generator")
_AGENT_NAME = "QuestionGeneratorAgent"

SYSTEM_PROMPT = (
    "You are a Practice Question Author in a multi-agent educational pipeline. "
    "You receive an academic topic and a 3-bullet knowledge brief about it. "
    "Your job is to produce exactly 5 short practice Q/A pairs that test the "
    "concepts in the brief.\n\n"
    "Strict output contract:\n"
    "- Reply with a single JSON array — no markdown fences, no commentary.\n"
    "- The array MUST contain exactly 5 objects.\n"
    "- Each object MUST have keys `question` and `answer`, both strings.\n"
    "- Questions must be answerable from the brief.\n"
    "- Keep each question under 20 words and each answer under 40 words.\n\n"
    'Example: [{"question":"...", "answer":"..."}]'
)

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _extract_json_array(raw: str) -> List[PracticeQuestion]:
    """Pull the JSON array out of the model output, even if it wrapped it
    in fences or chatter, then validate the shape."""
    match = _JSON_ARRAY_RE.search(raw)
    if not match:
        raise ValueError(f"Model output contained no JSON array: {raw[:200]}")

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model output was not valid JSON: {exc}") from exc

    if not isinstance(parsed, list) or len(parsed) == 0:
        raise ValueError("Model output JSON must be a non-empty array.")

    questions: List[PracticeQuestion] = []
    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise ValueError(f"questions[{idx}] is not an object: {item!r}")
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()
        if not q or not a:
            raise ValueError(
                f"questions[{idx}] missing non-empty 'question' or 'answer'."
            )
        questions.append(PracticeQuestion(question=q, answer=a))
    return questions


def run_question_generator_agent(state: StudyState) -> StudyState:
    """LangGraph node: generate 5 Q/A pairs and persist them to SQLite."""
    topic = state.get("weak_topic")
    brief = state.get("knowledge_brief")
    if not topic:
        raise ValueError("QuestionGeneratorAgent: state['weak_topic'] is required.")
    if not brief:
        raise ValueError("QuestionGeneratorAgent: state['knowledge_brief'] is required.")

    _logger.info("[%s] generating questions for topic=%s", _AGENT_NAME, topic)

    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Knowledge brief:\n{brief}\n\n"
        f"Produce the JSON array of 5 Q/A objects now."
    )

    raw = ollama_chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        agent_name=_AGENT_NAME,
        temperature=0.3,
    )
    questions = _extract_json_array(raw)

    cards: List[Flashcard] = [
        Flashcard(question=q["question"], answer=q["answer"]) for q in questions
    ]
    saved = save_flashcards(topic, cards)

    logs = list(state.get("logs", []))
    logs.append(f"[{_AGENT_NAME}] generated={len(questions)} saved={saved}")

    return {
        "practice_questions": questions,
        "logs": logs,
    }
