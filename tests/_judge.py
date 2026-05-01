"""LLM-as-a-Judge helper.

A small wrapper that asks a local Ollama model to grade another agent's
output against a checklist, returning a structured pass/fail verdict.
Used by the live tests gated behind `EDUMAS_LIVE=1`.
"""
from __future__ import annotations

import json
import re
from typing import List, TypedDict

from core.llm import ollama_chat

_JUDGE_SYSTEM = (
    "You are an impartial Quality Assurance judge for a multi-agent system. "
    "You will be given (a) the contract an agent is supposed to satisfy, "
    "and (b) the agent's actual output. Decide whether the output satisfies "
    "every item in the contract.\n\n"
    "Reply with a single JSON object — NO markdown, NO commentary — with keys:\n"
    '  "passed":   true | false,\n'
    '  "score":    integer 0-10,\n'
    '  "failures": list of strings (empty if passed),\n'
    '  "rationale": one short sentence.'
)

_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


class JudgeVerdict(TypedDict):
    passed: bool
    score: int
    failures: List[str]
    rationale: str


def judge_output(contract: List[str], agent_output: str) -> JudgeVerdict:
    """Grade `agent_output` against the bullet list `contract` via Ollama."""
    user = (
        "Contract (every item must hold):\n"
        + "\n".join(f"- {c}" for c in contract)
        + "\n\nAgent output:\n"
        + agent_output
        + "\n\nReturn the JSON verdict now."
    )
    raw = ollama_chat(
        system_prompt=_JUDGE_SYSTEM,
        user_prompt=user,
        agent_name="LLMJudge",
        temperature=0.0,
    )
    match = _JSON_OBJ_RE.search(raw)
    if not match:
        return JudgeVerdict(
            passed=False, score=0,
            failures=["Judge did not return JSON."],
            rationale=raw[:200],
        )
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return JudgeVerdict(
            passed=False, score=0,
            failures=["Judge JSON was malformed."],
            rationale=raw[:200],
        )
    return JudgeVerdict(
        passed=bool(parsed.get("passed", False)),
        score=int(parsed.get("score", 0)),
        failures=list(parsed.get("failures") or []),
        rationale=str(parsed.get("rationale", "")),
    )
