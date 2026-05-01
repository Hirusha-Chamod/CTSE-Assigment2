"""Assessment Agent — owned by Member A.

Persona: Academic Counselor.
Responsibility: Read the student's quiz file via `quiz_parser_tool`,
identify the single weakest topic, and write a one-sentence rationale
into the global state for the next agent to pick up.

This agent demonstrates:
  * Tool use (file I/O via quiz_parser_tool)
  * SLM-backed natural-language rationale
  * Strict output contract (writes exactly two state keys)
"""
from __future__ import annotations

from core.llm import ollama_chat
from core.logger import get_logger
from core.state import StudyState
from tools.quiz_parser_tool import parse_quiz_file

_logger = get_logger("agent.assessment")
_AGENT_NAME = "AssessmentAgent"

SYSTEM_PROMPT = (
    "You are an Academic Counselor agent in a multi-agent educational pipeline. "
    "You receive a structured summary of a student's quiz performance. "
    "Your job is to confirm the WEAKEST topic and produce ONE short sentence "
    "(under 25 words) explaining why that topic deserves remediation. "
    "Constraints:\n"
    "- Reply with ONLY that one sentence — no preamble, no bullet points, no markdown.\n"
    "- Do NOT recommend study materials. That is the job of a downstream agent.\n"
    "- Do NOT invent statistics not present in the input."
)


def run_assessment_agent(state: StudyState) -> StudyState:
    """LangGraph node: parse the quiz file and set the weak topic."""
    quiz_path = state.get("quiz_path")
    if not quiz_path:
        raise ValueError("AssessmentAgent: state['quiz_path'] is required.")

    _logger.info("[%s] starting; quiz_path=%s", _AGENT_NAME, quiz_path)

    summary = parse_quiz_file(quiz_path)
    student_input = (
        f"Student: {summary['student']}\n"
        f"Per-topic accuracy:\n"
        + "\n".join(
            f"  - {t['topic']}: {t['correct']}/{t['total']} ({t['accuracy']:.0%})"
            for t in summary["per_topic"]
        )
        + f"\nWeakest topic identified: {summary['weakest_topic']} "
          f"({summary['weakest_accuracy']:.0%})"
    )

    rationale = ollama_chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=student_input,
        agent_name=_AGENT_NAME,
        temperature=0.1,
    )

    logs = list(state.get("logs", []))
    logs.append(f"[{_AGENT_NAME}] weak_topic={summary['weakest_topic']!r}")
    logs.append(f"[{_AGENT_NAME}] rationale={rationale!r}")

    return {
        "student_input": student_input + f"\nRationale: {rationale}",
        "weak_topic": summary["weakest_topic"],
        "logs": logs,
    }
