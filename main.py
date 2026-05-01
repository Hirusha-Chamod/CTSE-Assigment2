"""EduMAS — entrypoint.

Wires the 4 agents into a LangGraph state machine and runs the pipeline.

Pipeline:
    START -> assessment -> gap_analyst -> question_generator -> study_planner -> END

Each node receives the full StudyState, returns a partial update that
LangGraph merges back in. Run via:

    python main.py                              # uses data/sample_quiz.json
    python main.py path/to/your_quiz.json       # custom input
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from agents.assessment_agent import run_assessment_agent
from agents.gap_analyst_agent import run_gap_analyst_agent
from agents.question_generator_agent import run_question_generator_agent
from agents.study_planner_agent import run_study_planner_agent
from core.logger import get_logger
from core.state import StudyState, init_state

_logger = get_logger("main")


def build_graph():
    """Construct the LangGraph orchestrator for the 4-agent pipeline."""
    graph = StateGraph(StudyState)

    graph.add_node("assessment", run_assessment_agent)
    graph.add_node("gap_analyst", run_gap_analyst_agent)
    graph.add_node("question_generator", run_question_generator_agent)
    graph.add_node("study_planner", run_study_planner_agent)

    graph.add_edge(START, "assessment")
    graph.add_edge("assessment", "gap_analyst")
    graph.add_edge("gap_analyst", "question_generator")
    graph.add_edge("question_generator", "study_planner")
    graph.add_edge("study_planner", END)

    return graph.compile()


def run(quiz_path: str) -> StudyState:
    """Run the full 4-agent pipeline on the given quiz file."""
    if not Path(quiz_path).is_file():
        raise FileNotFoundError(f"Quiz file not found: {quiz_path}")

    _logger.info("=" * 70)
    _logger.info("EduMAS run starting | quiz=%s", quiz_path)
    _logger.info("=" * 70)

    app = build_graph()
    final_state: StudyState = app.invoke(init_state(quiz_path))

    _logger.info("=" * 70)
    _logger.info("EduMAS run finished | weak_topic=%s", final_state.get("weak_topic"))
    _logger.info("Output saved to: %s", final_state.get("study_plan_path"))
    _logger.info("=" * 70)
    return final_state


def _print_summary(state: StudyState) -> None:
    print("\n" + "=" * 70)
    print("FINAL RESULT")
    print("=" * 70)
    print(f"Weak topic       : {state.get('weak_topic')}")
    print(f"Study plan (MD)  : {state.get('study_plan_path')}")
    print(f"Study plan (PDF) : {state.get('study_plan_pdf_path')}")
    print("\n--- Knowledge Brief ---")
    print(state.get("knowledge_brief", "(none)"))
    print("\n--- Practice Questions ---")
    for idx, q in enumerate(state.get("practice_questions") or [], start=1):
        print(f"  Q{idx}. {q['question']}")
        print(f"      {q['answer']}")
    print("\n--- 7-Day Plan ---")
    print(state.get("study_plan", "(none)"))
    print("=" * 70)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EduMAS — Multi-Agent Study Planner")
    parser.add_argument(
        "quiz_path",
        nargs="?",
        default="data/sample_quiz.json",
        help="Path to the student's quiz JSON file (default: data/sample_quiz.json).",
    )
    args = parser.parse_args(argv)

    try:
        final_state = run(args.quiz_path)
    except Exception as exc:  # surface the failure clearly in the demo
        _logger.exception("Pipeline failed: %s", exc)
        return 1

    _print_summary(final_state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
