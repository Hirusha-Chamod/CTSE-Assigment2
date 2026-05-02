"""EduMAS FastAPI server.

Run from the project root:
    pip install -r server/requirements.txt
    uvicorn server.main:app --reload
"""
from __future__ import annotations

import json
import os
import tempfile

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from main import run

app = FastAPI(title="EduMAS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    quiz_json: dict


class RunResponse(BaseModel):
    weak_topic: str
    knowledge_brief: str
    practice_questions: list[dict]
    study_plan: str
    study_plan_path: str
    study_plan_pdf_path: str
    logs: list[str]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/run", response_model=RunResponse)
def run_pipeline(req: RunRequest):
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    try:
        json.dump(req.quiz_json, tmp)
        tmp.close()
        state = run(tmp.name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    return RunResponse(
        weak_topic=state.get("weak_topic", ""),
        knowledge_brief=state.get("knowledge_brief", ""),
        practice_questions=list(state.get("practice_questions") or []),
        study_plan=state.get("study_plan", ""),
        study_plan_path=state.get("study_plan_path", ""),
        study_plan_pdf_path=state.get("study_plan_pdf_path", ""),
        logs=list(state.get("logs") or []),
    )
