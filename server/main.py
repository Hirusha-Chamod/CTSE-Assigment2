"""EduMAS FastAPI server.

Run from the project root:
    pip install -r server/requirements.txt
    uvicorn server.main:app --reload

POST /api/run        — starts a background job, returns {run_id} immediately
GET  /api/run/{id}   — poll status, logs, and result
GET  /api/pdf?path=  — serve a generated PDF
GET  /api/health     — liveness check
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from main import run

# ---------------------------------------------------------------------------
# Background job store
# ---------------------------------------------------------------------------

@dataclass
class _Job:
    run_id: str
    status: str = "running"          # "running" | "done" | "error"
    logs: list[str] = field(default_factory=list)
    result: Optional[dict] = None
    error: Optional[str] = None

_jobs: dict[str, _Job] = {}
_pool = ThreadPoolExecutor(max_workers=4)

# ---------------------------------------------------------------------------
# Live log capture via ContextVar + logging.Handler
# Each worker thread sets _active_job; the handler appends to it in real time.
# ---------------------------------------------------------------------------

_active_job: ContextVar[Optional[_Job]] = ContextVar("active_job", default=None)


class _JobLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        job = _active_job.get()
        if job is not None:
            job.logs.append(self.format(record))


_log_handler = _JobLogHandler()
_log_handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
logging.getLogger().addHandler(_log_handler)
logging.getLogger().setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_OUTPUTS_DIR = (Path(__file__).resolve().parent.parent / "outputs").resolve()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="EduMAS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    quiz_json: dict

class StartRunResponse(BaseModel):
    run_id: str

class RunResultPayload(BaseModel):
    weak_topic: str
    knowledge_brief: str
    practice_questions: list[dict]
    study_plan: str
    study_plan_path: str
    study_plan_pdf_path: str
    logs: list[str]

class RunStatusResponse(BaseModel):
    status: str
    logs: list[str]
    result: Optional[RunResultPayload] = None
    error: Optional[str] = None

# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

def _execute(run_id: str, quiz_json: dict) -> None:
    job = _jobs[run_id]
    token = _active_job.set(job)
    tmp_path: Optional[str] = None
    try:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(quiz_json, tmp)
        tmp.close()
        tmp_path = tmp.name

        state = run(tmp_path)

        job.result = {
            "weak_topic": state.get("weak_topic", ""),
            "knowledge_brief": state.get("knowledge_brief", ""),
            "practice_questions": list(state.get("practice_questions") or []),
            "study_plan": state.get("study_plan", ""),
            "study_plan_path": state.get("study_plan_path", ""),
            "study_plan_pdf_path": state.get("study_plan_pdf_path", ""),
            "logs": job.logs[:],  # snapshot at completion
        }
        job.status = "done"
    except Exception as exc:
        job.error = str(exc)
        job.status = "error"
    finally:
        _active_job.reset(token)
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/run", response_model=StartRunResponse)
def start_run(req: RunRequest) -> StartRunResponse:
    """Submit a new pipeline run. Returns a run_id immediately."""
    run_id = str(uuid.uuid4())
    _jobs[run_id] = _Job(run_id=run_id)
    _pool.submit(_execute, run_id, req.quiz_json)
    return StartRunResponse(run_id=run_id)


@app.get("/api/run/{run_id}", response_model=RunStatusResponse)
def get_run(run_id: str) -> RunStatusResponse:
    """Poll the status, live logs, and (when done) the full result."""
    job = _jobs.get(run_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found. The server may have restarted — please start a new run.",
        )
    result_model = RunResultPayload(**job.result) if job.result else None
    return RunStatusResponse(
        status=job.status,
        logs=job.logs[:],
        result=result_model,
        error=job.error,
    )


@app.get("/api/pdf")
def get_pdf(path: str = Query(...)) -> FileResponse:
    p = Path(path).resolve()
    if not str(p).startswith(str(_OUTPUTS_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not p.exists() or p.suffix != ".pdf":
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(str(p), media_type="application/pdf", filename=p.name)
