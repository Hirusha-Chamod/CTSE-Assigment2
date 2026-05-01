"""Shared pytest fixtures and helpers for the unified test harness.

Conventions:
- Tests that don't need Ollama monkeypatch `core.llm.ollama_chat` (and the
  copies imported into each agent module) — they run instantly.
- Tests that DO need Ollama (the LLM-as-a-judge ones) are gated by the
  `EDUMAS_LIVE=1` env var, so they're skipped in CI/offline.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make the project root importable when running `pytest` from anywhere.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _live_enabled() -> bool:
    return os.environ.get("EDUMAS_LIVE") == "1"


live_only = pytest.mark.skipif(
    not _live_enabled(),
    reason="Live Ollama tests skipped — set EDUMAS_LIVE=1 to enable.",
)


@pytest.fixture
def patch_ollama(monkeypatch):
    """Replace `ollama_chat` in every agent module with a stub.

    Returns a dict so tests can program per-agent responses:
        responses["AssessmentAgent"] = "Calculus is the weakest topic."
    """
    responses: dict[str, str] = {}

    def _stub(system_prompt, user_prompt, *, agent_name="unknown", **_kwargs):
        if agent_name in responses:
            return responses[agent_name]
        return f"<stub response for {agent_name}>"

    # Patch in every module that imported the symbol.
    for module_path in (
        "core.llm.ollama_chat",
        "agents.assessment_agent.ollama_chat",
        "agents.gap_analyst_agent.ollama_chat",
        "agents.question_generator_agent.ollama_chat",
        "agents.study_planner_agent.ollama_chat",
    ):
        monkeypatch.setattr(module_path, _stub)

    return responses


@pytest.fixture
def sample_quiz_path(tmp_path):
    """Write a deterministic sample quiz file to a tmp dir, return its path."""
    import json
    quiz = {
        "student": "TestStudent",
        "answers": [
            {"topic": "Calculus",       "correct": False},
            {"topic": "Calculus",       "correct": False},
            {"topic": "Calculus",       "correct": False},
            {"topic": "Linear Algebra", "correct": True},
            {"topic": "Linear Algebra", "correct": True},
        ],
    }
    path = tmp_path / "quiz.json"
    path.write_text(json.dumps(quiz), encoding="utf-8")
    return str(path)
