"""Study Planner Agent — owned by Member D.

Persona: Senior Study Planner.
Responsibility: Take everything in StudyState (weak topic, brief, Q/A
pairs) and produce a structured 7-day study plan, then write it to
disk as both a Markdown and a PDF file via `study_plan_writer_tool`.
Both file paths are stored back into StudyState.
"""
from __future__ import annotations

from core.llm import ollama_chat
from core.logger import get_logger
from core.state import StudyState
from tools.study_plan_writer_tool import write_study_plan

_logger = get_logger("agent.study_planner")
_AGENT_NAME = "StudyPlannerAgent"

SYSTEM_PROMPT = (
    "You are a Senior Study Planner in a multi-agent educational pipeline. "
    "You receive an academic topic, a 3-bullet knowledge brief about it, "
    "and a small set of practice questions. Your job is to produce a clear, "
    "actionable 7-day study plan that gradually builds mastery.\n\n"
    "Strict output contract:\n"
    "- Output 7 sections, one per day, formatted as Markdown:\n"
    "    ### Day N — <short focus phrase>\n"
    "    - 2 to 4 bullets describing what to study or practice that day.\n"
    "- Days must build on each other (review → practice → application).\n"
    "- Reference the practice questions on at least two of the days.\n"
    "- No preamble before Day 1. No closing summary after Day 7.\n"
    "- Keep the whole plan under ~400 words."
)


def _format_questions(state: StudyState) -> str:
    questions = state.get("practice_questions") or []
    if not questions:
        return "(no practice questions provided)"
    return "\n".join(
        f"  Q{idx}. {q['question']}" for idx, q in enumerate(questions, start=1)
    )


def run_study_planner_agent(state: StudyState) -> StudyState:
    """LangGraph node: generate the 7-day plan and write it to outputs/ as MD + PDF."""
    topic = state.get("weak_topic")
    brief = state.get("knowledge_brief")
    if not topic:
        raise ValueError("StudyPlannerAgent: state['weak_topic'] is required.")
    if not brief:
        raise ValueError("StudyPlannerAgent: state['knowledge_brief'] is required.")

    _logger.info("[%s] planning for topic=%s", _AGENT_NAME, topic)

    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Knowledge brief:\n{brief}\n\n"
        f"Practice questions to weave in:\n{_format_questions(state)}\n\n"
        f"Produce the 7-day study plan now."
    )

    plan_body = ollama_chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        agent_name=_AGENT_NAME,
        temperature=0.3,
    )

    paths = write_study_plan(
        topic=topic,
        knowledge_brief=brief,
        practice_questions=list(state.get("practice_questions") or []),
        plan_body=plan_body,
    )

    logs = list(state.get("logs", []))
    logs.append(
        f"[{_AGENT_NAME}] plan_chars={len(plan_body)} "
        f"md={paths['md_path']} pdf={paths['pdf_path']}"
    )

    return {
        "study_plan": plan_body,
        "study_plan_path": paths["md_path"],
        "study_plan_pdf_path": paths["pdf_path"],
        "logs": logs,
    }
