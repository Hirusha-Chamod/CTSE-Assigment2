"""Gap Analyst Agent — owned by Reshan.

Persona: Educational Curriculum Researcher.
Responsibility: Take the weak topic identified by the Assessment Agent,
fetch a Wikipedia summary via `wiki_tool`, and synthesize a concise
3-bullet "knowledge brief" that downstream agents can consume.

Key constraints in the system prompt:
  * Use ONLY the supplied Wikipedia text — no prior-knowledge embellishment.
  * Output exactly 3 bullet points, no preamble, no closing remarks.
"""
from __future__ import annotations

from core.llm import ollama_chat
from core.logger import get_logger
from core.state import StudyState
from tools.wiki_tool import fetch_wikipedia_summary

_logger = get_logger("agent.gap_analyst")
_AGENT_NAME = "GapAnalystAgent"

SYSTEM_PROMPT = (
    "You are an Educational Curriculum Researcher (Gap Analyst) in a "
    "multi-agent educational pipeline. You receive (a) an academic topic the "
    "student is weak in and (b) a Wikipedia extract for that topic.\n\n"
    "Your job is to write a *Knowledge Gap Brief*: exactly THREE concise "
    "bullet points summarizing the core concepts the student must understand "
    "to close the gap.\n\n"
    "Strict constraints:\n"
    "- Use ONLY information supported by the supplied Wikipedia text.\n"
    "- Do NOT invent definitions, formulas, dates, or examples.\n"
    "- Output ONLY the three bullet points. Each bullet starts with `- `.\n"
    "- Keep each bullet under 30 words.\n"
    "- No preamble, no closing line, no headings, no numbering."
)


def run_gap_analyst_agent(state: StudyState) -> StudyState:
    """LangGraph node: research the weak topic and produce a 3-bullet brief."""
    topic = state.get("weak_topic")
    if not topic:
        raise ValueError("GapAnalystAgent: state['weak_topic'] is required.")

    _logger.info("[%s] researching topic=%s", _AGENT_NAME, topic)
    wiki_data = fetch_wikipedia_summary(topic) or "Topic not found on Wikipedia."

    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Wikipedia extract:\n{wiki_data}\n\n"
        f"Produce the Knowledge Gap Brief now."
    )

    brief = ollama_chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        agent_name=_AGENT_NAME,
        temperature=0.2,
    )

    logs = list(state.get("logs", []))
    logs.append(f"[{_AGENT_NAME}] wiki_chars={len(wiki_data)}")
    logs.append(f"[{_AGENT_NAME}] brief_preview={brief[:120]!r}")

    return {
        "knowledge_brief": brief,
        "logs": logs,
    }
