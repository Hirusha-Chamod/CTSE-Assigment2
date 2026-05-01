"""Evaluation script for the Assessment Agent — owned by Member A.

Three layers:
  1. Property-based tests on `parse_quiz_file` (the tool).
  2. Mocked-LLM unit test on the agent node — no Ollama required.
  3. Live LLM-as-a-Judge test (skipped unless EDUMAS_LIVE=1).
"""
from __future__ import annotations

import json

import pytest
from hypothesis import given, settings, strategies as st

from agents.assessment_agent import run_assessment_agent
from core.state import init_state
from tools.quiz_parser_tool import QuizParseError, parse_quiz_file
from tests.conftest import live_only


# ---------- 1. Property-based tests on the tool ----------

@settings(max_examples=25, deadline=None)
@given(
    answers=st.lists(
        st.fixed_dictionaries({
            "topic": st.sampled_from(["A", "B", "C", "D"]),
            "correct": st.booleans(),
        }),
        min_size=1, max_size=30,
    )
)
def test_quiz_parser_picks_the_lowest_accuracy_topic(tmp_path_factory, answers):
    """For any valid quiz, the weakest topic must have the minimum accuracy."""
    path = tmp_path_factory.mktemp("quiz") / "q.json"
    path.write_text(json.dumps({"student": "X", "answers": answers}), encoding="utf-8")

    summary = parse_quiz_file(str(path))

    assert 0.0 <= summary["weakest_accuracy"] <= 1.0
    min_acc = min(t["accuracy"] for t in summary["per_topic"])
    assert summary["weakest_accuracy"] == pytest.approx(min_acc)


def test_quiz_parser_rejects_missing_file(tmp_path):
    with pytest.raises(QuizParseError, match="not found"):
        parse_quiz_file(str(tmp_path / "missing.json"))


def test_quiz_parser_rejects_empty_answers(tmp_path):
    p = tmp_path / "q.json"
    p.write_text(json.dumps({"student": "X", "answers": []}), encoding="utf-8")
    with pytest.raises(QuizParseError, match="non-empty"):
        parse_quiz_file(str(p))


def test_quiz_parser_rejects_bad_answer_shape(tmp_path):
    p = tmp_path / "q.json"
    p.write_text(json.dumps({"answers": [{"topic": "A"}]}), encoding="utf-8")
    with pytest.raises(QuizParseError):
        parse_quiz_file(str(p))


# ---------- 2. Mocked agent node test ----------

def test_assessment_agent_writes_weak_topic_to_state(patch_ollama, sample_quiz_path):
    patch_ollama["AssessmentAgent"] = "Calculus needs urgent remediation."

    state = init_state(sample_quiz_path)
    update = run_assessment_agent(state)

    assert update["weak_topic"] == "Calculus"
    assert "Calculus" in update["student_input"]
    assert any("AssessmentAgent" in line for line in update["logs"])


def test_assessment_agent_requires_quiz_path():
    with pytest.raises(ValueError, match="quiz_path"):
        run_assessment_agent({})


# ---------- 3. Live LLM-as-a-Judge ----------

@live_only
def test_assessment_rationale_is_concise_via_judge(sample_quiz_path):
    """The rationale field must be a single short sentence per the system prompt."""
    from tests._judge import judge_output

    state = init_state(sample_quiz_path)
    update = run_assessment_agent(state)
    rationale = update["student_input"].split("Rationale:", 1)[-1].strip()

    verdict = judge_output(
        contract=[
            "Output is exactly ONE sentence.",
            "Sentence is under 25 words.",
            "Output contains no bullet points or markdown.",
            "Output does NOT recommend study materials.",
        ],
        agent_output=rationale,
    )
    assert verdict["passed"], f"Judge failed: {verdict}"
