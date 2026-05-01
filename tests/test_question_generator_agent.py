"""Evaluation script for the Question Generator Agent — owned by Member C.

Three layers:
  1. Property-based tests on the `flashcard_tool` (round-trip persistence).
  2. Mocked-LLM unit test asserting JSON parsing + DB write.
  3. Live LLM-as-a-Judge test (skipped unless EDUMAS_LIVE=1).
"""
from __future__ import annotations

import json

import pytest
from hypothesis import given, settings, strategies as st

from agents.question_generator_agent import (
    _extract_json_array,
    run_question_generator_agent,
)
from tools.flashcard_tool import (
    Flashcard,
    FlashcardToolError,
    load_flashcards,
    save_flashcards,
)
from tests.conftest import live_only


# ---------- 1. Tool round-trip / property tests ----------

@settings(max_examples=15, deadline=None)
@given(
    cards=st.lists(
        st.fixed_dictionaries({
            "question": st.text(min_size=1, max_size=80).filter(str.strip),
            "answer":   st.text(min_size=1, max_size=80).filter(str.strip),
        }),
        min_size=1, max_size=10,
    ),
    topic=st.text(alphabet=st.characters(min_codepoint=65, max_codepoint=90),
                  min_size=1, max_size=20),
)
def test_flashcard_round_trip(tmp_path_factory, cards, topic):
    db = tmp_path_factory.mktemp("db") / "fc.db"
    saved = save_flashcards(topic, cards, db_path=db)
    loaded = load_flashcards(topic, db_path=db)
    assert saved == len(cards)
    assert len(loaded) == len(cards)
    for original, retrieved in zip(cards, loaded):
        assert original["question"].strip() == retrieved["question"]
        assert original["answer"].strip() == retrieved["answer"]


def test_flashcard_rejects_empty_topic():
    with pytest.raises(ValueError, match="topic"):
        save_flashcards("", [Flashcard(question="q", answer="a")])


def test_flashcard_rejects_empty_card_fields(tmp_path):
    with pytest.raises(ValueError):
        save_flashcards(
            "T",
            [Flashcard(question="", answer="a")],
            db_path=tmp_path / "fc.db",
        )


def test_flashcard_load_returns_empty_for_missing_db(tmp_path):
    assert load_flashcards("Anything", db_path=tmp_path / "nope.db") == []


# ---------- 2. JSON extractor + agent node ----------

def test_extract_json_array_strips_markdown_fences():
    raw = '```json\n[{"question": "Q?", "answer": "A."}]\n```'
    out = _extract_json_array(raw)
    assert out == [{"question": "Q?", "answer": "A."}]


def test_extract_json_array_rejects_non_json():
    with pytest.raises(ValueError):
        _extract_json_array("just some prose, no JSON here")


def test_extract_json_array_rejects_missing_keys():
    with pytest.raises(ValueError):
        _extract_json_array('[{"question": "Q?"}]')


def test_question_generator_persists_to_db(tmp_path, monkeypatch, patch_ollama):
    five = json.dumps([
        {"question": f"Q{i}?", "answer": f"A{i}."} for i in range(1, 6)
    ])
    patch_ollama["QuestionGeneratorAgent"] = five

    db_path = tmp_path / "fc.db"
    monkeypatch.setattr(
        "agents.question_generator_agent.save_flashcards",
        lambda topic, cards: save_flashcards(topic, cards, db_path=db_path),
    )

    update = run_question_generator_agent({
        "weak_topic": "Calculus",
        "knowledge_brief": "- one\n- two\n- three",
    })
    assert len(update["practice_questions"]) == 5
    assert load_flashcards("Calculus", db_path=db_path) != []


def test_question_generator_requires_brief():
    with pytest.raises(ValueError, match="knowledge_brief"):
        run_question_generator_agent({"weak_topic": "X"})


# ---------- 3. Live LLM-as-a-Judge ----------

@live_only
def test_question_generator_output_via_judge():
    from tests._judge import judge_output

    update = run_question_generator_agent({
        "weak_topic": "Photosynthesis",
        "knowledge_brief": (
            "- Photosynthesis converts light energy into chemical energy.\n"
            "- It uses chlorophyll inside plant cells.\n"
            "- It produces oxygen as a byproduct."
        ),
    })
    qa = update["practice_questions"]

    assert len(qa) == 5, "Agent must produce exactly 5 Q/A pairs."
    qa_text = "\n".join(f"Q: {q['question']}\nA: {q['answer']}" for q in qa)

    verdict = judge_output(
        contract=[
            "There are exactly 5 question-answer pairs.",
            "Every question is under 20 words.",
            "Every answer is under 40 words.",
            "Every question is answerable from a brief about photosynthesis.",
        ],
        agent_output=qa_text,
    )
    assert verdict["passed"], f"Judge failed: {verdict}"


def test_flashcard_tool_error_class_exists():
    """Sanity: the dedicated error type is exported and is a RuntimeError."""
    assert issubclass(FlashcardToolError, RuntimeError)
