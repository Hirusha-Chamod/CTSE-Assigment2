"""Project-wide logging setup.

Every agent and tool gets its logger via `get_logger(name)`. Logs go
to both stdout and `logs/run.log`, giving full traceability of:
  - which agent ran
  - which tools it invoked (with args)
  - which LLM calls it made (with timing)
  - the final output

This satisfies the LLMOps/AgentOps observability requirement.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "run.log"
_FORMAT = "%(asctime)s [%(levelname)s] %(name)s :: %(message)s"

_initialized = False


def _ensure_setup() -> None:
    """Idempotently configure the root project logger."""
    global _initialized
    if _initialized:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("edumas")
    root.setLevel(logging.INFO)
    root.propagate = False

    if not root.handlers:
        formatter = logging.Formatter(_FORMAT)

        file_handler = RotatingFileHandler(
            _LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

        # stdout — keep INFO+ visible during demo
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(
            logging.DEBUG if os.environ.get("EDUMAS_DEBUG") else logging.INFO
        )
        root.addHandler(stream_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced child logger that writes to logs/run.log + stdout."""
    _ensure_setup()
    return logging.getLogger(f"edumas.{name}")
