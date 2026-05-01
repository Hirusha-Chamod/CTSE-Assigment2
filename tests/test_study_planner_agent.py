"""Evaluation script for the Study Planner Agent — owned by Member D.

Three layers:
  1. Tests on `study_plan_writer_tool` (file I/O, slugging, validation, PDF).
  2. Mocked-LLM unit test on the agent node — verifies both files land on disk.
  3. Live LLM-as-a-Judge test (skipped unless EDUMAS_LIVE=1).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agents.study_planner_agent import run_study_planner_agent
from tools.study_plan_writer_tool import (
    StudyPlanWriteError,
    _slugify,
    write_study_plan,
)
from tests.conftest import live_only


# ---------- 1. Tool tests ----------

def test_slugify_handles_punctuation():
    assert _slugify("Calculus II!") == "calculus_ii"
    assert _slugify("   ") == "topic"
    assert _slugify("Photosynthesis & Respiration") == "photosynthesis_respiration"


def test_write_study_plan_returns_both_paths(tmp_path):
    paths = write_study_plan(
        topic="Calculus",
        knowledge_brief="- limits\n- derivatives\n- integrals",
        practice_questions=[
            {"question": "What is a limit?", "answer": "A value a function approaches."},
        ],
        plan_body="### Day 1 — Limits\n- Read chapter 1.",
        output_dir=tmp_path,
    )
    assert "md_path" in paths
    assert "pdf_path" in paths
    assert paths["md_path"].endswith(".md")
    assert paths["pdf_path"].endswith(".pdf")
    assert Path(paths["md_path"]).exists()
    assert Path(paths["pdf_path"]).exists()


def test_write_study_plan_md_has_required_sections(tmp_path):
    paths = write_study_plan(
        topic="Calculus",
        knowledge_brief="- limits\n- derivatives\n- integrals",
        practice_questions=[
            {"question": "What is a limit?", "answer": "A value a function approaches."},
        ],
        plan_body="### Day 1 — Limits\n- Read chapter 1.",
        output_dir=tmp_path,
    )
    text = Path(paths["md_path"]).read_text(encoding="utf-8")
    assert "# Personalized Study Plan: Calculus" in text
    assert "## 1. Knowledge Brief" in text
    assert "## 2. Practice Questions" in text
    assert "## 3. 7-Day Study Plan" in text
    assert "What is a limit?" in text


def test_write_study_plan_pdf_is_valid_pdf(tmp_path):
    paths = write_study_plan(
        topic="Calculus",
        knowledge_brief="- limits\n- derivatives\n- integrals",
        practice_questions=[],
        plan_body="### Day 1 — Limits\n- Read chapter 1.",
        output_dir=tmp_path,
    )
    # PDF files start with the magic bytes %PDF
    header = Path(paths["pdf_path"]).read_bytes()[:4]
    assert header == b"%PDF", "Output is not a valid PDF file."


def test_write_study_plan_rejects_empty_topic(tmp_path):
    with pytest.raises(ValueError, match="topic"):
        write_study_plan(
            topic="", knowledge_brief="b", practice_questions=[],
            plan_body="### Day 1 — x", output_dir=tmp_path,
        )


def test_write_study_plan_rejects_empty_plan_body(tmp_path):
    with pytest.raises(ValueError, match="plan_body"):
        write_study_plan(
            topic="X", knowledge_brief="b", practice_questions=[],
            plan_body="", output_dir=tmp_path,
        )


def test_write_study_plan_handles_no_questions(tmp_path):
    paths = write_study_plan(
        topic="X", knowledge_brief="b", practice_questions=[],
        plan_body="### Day 1 — x", output_dir=tmp_path,
    )
    assert "(no questions generated)" in Path(paths["md_path"]).read_text(encoding="utf-8")


def test_study_plan_write_error_class_exists():
    assert issubclass(StudyPlanWriteError, RuntimeError)


# ---------- 2. Mocked agent node test ----------

def test_study_planner_writes_both_files_to_disk(tmp_path, monkeypatch, patch_ollama):
    patch_ollama["StudyPlannerAgent"] = (
        "### Day 1 — Foundations\n- Read the brief.\n"
        "### Day 2 — Practice\n- Attempt Q1.\n"
        "### Day 3 — Deepen\n- Re-read.\n"
        "### Day 4 — More practice\n- Attempt Q2.\n"
        "### Day 5 — Apply\n- Try a real example.\n"
        "### Day 6 — Review\n- Self-test.\n"
        "### Day 7 — Consolidate\n- Summarize in your own words."
    )
    monkeypatch.setattr(
        "agents.study_planner_agent.write_study_plan",
        lambda **kw: write_study_plan(output_dir=tmp_path, **kw),
    )

    update = run_study_planner_agent({
        "weak_topic": "Calculus",
        "knowledge_brief": "- limits\n- derivatives\n- integrals",
        "practice_questions": [
            {"question": "What is a derivative?", "answer": "A rate of change."},
        ],
    })

    assert update["study_plan_path"].endswith(".md")
    assert update["study_plan_pdf_path"].endswith(".pdf")
    assert Path(update["study_plan_path"]).exists()
    assert Path(update["study_plan_pdf_path"]).exists()
    assert "Day 1" in update["study_plan"]


def test_study_planner_requires_brief():
    with pytest.raises(ValueError, match="knowledge_brief"):
        run_study_planner_agent({"weak_topic": "X"})


# ---------- 3. Live LLM-as-a-Judge ----------

@live_only
def test_study_plan_meets_contract_via_judge(tmp_path, monkeypatch):
    from tests._judge import judge_output

    monkeypatch.setattr(
        "agents.study_planner_agent.write_study_plan",
        lambda **kw: write_study_plan(output_dir=tmp_path, **kw),
    )
    update = run_study_planner_agent({
        "weak_topic": "Photosynthesis",
        "knowledge_brief": (
            "- Photosynthesis converts light energy into chemical energy.\n"
            "- It uses chlorophyll inside plant cells.\n"
            "- It produces oxygen as a byproduct."
        ),
        "practice_questions": [
            {"question": "What is chlorophyll?", "answer": "A green pigment."},
            {"question": "What gas does photosynthesis release?", "answer": "Oxygen."},
        ],
    })
    plan = update["study_plan"]

    verdict = judge_output(
        contract=[
            "Plan contains exactly 7 daily sections.",
            "Each day starts with a heading like '### Day N'.",
            "Days build on each other (review -> practice -> application).",
            "There is no preamble before Day 1 and no summary after Day 7.",
        ],
        agent_output=plan,
    )
    assert verdict["passed"], f"Judge failed: {verdict}"
