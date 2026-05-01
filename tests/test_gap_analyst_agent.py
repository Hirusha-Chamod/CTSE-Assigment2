"""Evaluation script for the Gap Analyst Agent — owned by Reshan.

Three layers:
  1. Tool tests on `fetch_wikipedia_summary` (network-mocked + edge cases).
  2. Mocked-LLM unit test on the agent node.
  3. Live LLM-as-a-Judge test (skipped unless EDUMAS_LIVE=1).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agents.gap_analyst_agent import run_gap_analyst_agent
from tools.wiki_tool import WikiToolError, fetch_wikipedia_summary
from tests.conftest import live_only


# ---------- 1. Tool tests ----------

def test_wiki_tool_returns_none_for_blank_topic():
    assert fetch_wikipedia_summary("") is None
    assert fetch_wikipedia_summary("   ") is None


def test_wiki_tool_returns_extract_on_success():
    fake_response = type("R", (), {
        "status_code": 200,
        "json": lambda self: {"extract": "Photosynthesis is a process used by plants."},
    })()
    with patch("tools.wiki_tool.requests.get", return_value=fake_response):
        out = fetch_wikipedia_summary("Photosynthesis")
    assert out is not None and "process" in out


def test_wiki_tool_handles_404():
    fake_response = type("R", (), {"status_code": 404})()
    with patch("tools.wiki_tool.requests.get", return_value=fake_response):
        out = fetch_wikipedia_summary("ThisTopicDoesNotExistAtAll")
    assert out == "Topic not found on Wikipedia."


def test_wiki_tool_raises_on_network_error():
    import requests as _r
    with patch(
        "tools.wiki_tool.requests.get",
        side_effect=_r.exceptions.ConnectionError("boom"),
    ):
        with pytest.raises(WikiToolError):
            fetch_wikipedia_summary("Photosynthesis")


# ---------- 2. Mocked agent node test ----------

def test_gap_analyst_writes_brief_to_state(patch_ollama):
    patch_ollama["GapAnalystAgent"] = (
        "- Bullet one about photosynthesis.\n"
        "- Bullet two about chlorophyll.\n"
        "- Bullet three about light reactions."
    )

    fake_resp = type("R", (), {
        "status_code": 200,
        "json": lambda self: {"extract": "Photosynthesis converts light energy."},
    })()
    with patch("tools.wiki_tool.requests.get", return_value=fake_resp):
        update = run_gap_analyst_agent({"weak_topic": "Photosynthesis"})

    assert update["knowledge_brief"].count("- ") == 3
    assert any("GapAnalystAgent" in line for line in update["logs"])


def test_gap_analyst_requires_weak_topic():
    with pytest.raises(ValueError, match="weak_topic"):
        run_gap_analyst_agent({})


# ---------- 3. Live LLM-as-a-Judge ----------

@live_only
def test_gap_analyst_brief_meets_contract_via_judge():
    from tests._judge import judge_output

    update = run_gap_analyst_agent({"weak_topic": "Photosynthesis"})
    brief = update["knowledge_brief"]

    verdict = judge_output(
        contract=[
            "Output contains exactly THREE bullet points.",
            "Every bullet starts with the literal characters '- '.",
            "There is no preamble, heading, or closing remark.",
            "Bullets describe core concepts of the topic.",
        ],
        agent_output=brief,
    )
    assert verdict["passed"], f"Judge failed: {verdict}"
