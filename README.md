# EduMAS — Personalized Educational Assistant
### SE4010 – CTSE | Assignment 2 | Multi-Agent System

A locally-hosted, zero-cost Multi-Agent System that takes a student's quiz results, identifies their weakest topic, researches it via Wikipedia, generates practice flashcards, and produces a personalized 7-day study plan — all powered by local Small Language Models through [Ollama](https://ollama.com). No paid APIs. No cloud.

---

## Quick Start

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 or higher |
| [Ollama](https://ollama.com/download) | Latest |
| `llama3:8b` model | pulled via Ollama |

---

## Step 1 — Install Ollama and pull the model

Download and install Ollama from [https://ollama.com/download](https://ollama.com/download), then:

```bash
ollama pull llama3:8b
```

Start the Ollama server (keep this terminal open):

```bash
ollama serve
# Running at http://localhost:11434
```

> **Alternative models:** You can use `phi3`, `qwen2:7b`, or any other Ollama model.
> Change it with the env var: `set OLLAMA_MODEL=phi3` (Windows) or `export OLLAMA_MODEL=phi3` (macOS/Linux).

---

## Step 2 — Clone the repository and install dependencies

```bash
git clone <your-github-repo-url>
cd CTSE-Assigment2
```

Create and activate a virtual environment:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Step 3 — Run the full pipeline

```bash
python main.py
```

This uses the bundled sample quiz at `data/sample_quiz.json`.
The system will:
1. Parse the quiz and identify the weakest topic
2. Fetch a Wikipedia summary for that topic
3. Generate 5 practice Q/A pairs and save them to a local SQLite database
4. Write a 7-day study plan to `outputs/study_plan_<topic>_<timestamp>.md`

**To use your own quiz file:**

```bash
python main.py path/to/your_quiz.json
```

The quiz file must follow this shape:

```json
{
  "student": "Your Name",
  "answers": [
    { "topic": "Calculus",      "correct": false },
    { "topic": "Calculus",      "correct": false },
    { "topic": "Linear Algebra","correct": true  }
  ]
}
```

---

## Step 4 — View the outputs

**Generated study plan:**

```bash
# Windows
dir outputs\

# macOS / Linux
ls outputs/
```

Open the `.md` file in any Markdown viewer or text editor.

**Execution trace / logs:**

```bash
# Windows
type logs\run.log

# macOS / Linux
cat logs/run.log
```

Every LLM call, tool invocation, and agent handoff is timestamped in `logs/run.log`.

---

## Step 5 — Run the test suite

**Offline tests** (no Ollama required — property-based + mocked LLM):

```bash
pytest tests/ -v
```

Expected output:
```
30 passed, 4 skipped  (live tests skipped — set EDUMAS_LIVE=1 to enable)
```

**Full tests including LLM-as-a-Judge** (requires Ollama running):

```bash
# Windows
set EDUMAS_LIVE=1 && pytest tests/ -v

# macOS / Linux
EDUMAS_LIVE=1 pytest tests/ -v
```

**Run a single student's evaluation script:**

```bash
pytest tests/test_gap_analyst_agent.py -v
pytest tests/test_assessment_agent.py -v
pytest tests/test_question_generator_agent.py -v
pytest tests/test_study_planner_agent.py -v
```

---

## Architecture

```
 Student Quiz (JSON)
        │
        ▼
┌───────────────────┐   quiz_parser_tool (file I/O)
│  AssessmentAgent  │─► Identifies weakest topic
└───────────────────┘
        │  weak_topic
        ▼
┌───────────────────┐   wiki_tool (Wikipedia API)
│  GapAnalystAgent  │─► Produces 3-bullet knowledge brief
└───────────────────┘
        │  knowledge_brief
        ▼
┌──────────────────────────┐   flashcard_tool (SQLite DB)
│  QuestionGeneratorAgent  │─► Generates 5 practice Q/A pairs
└──────────────────────────┘
        │  practice_questions
        ▼
┌──────────────────────────┐   study_plan_writer_tool (Markdown)
│    StudyPlannerAgent     │─► Writes personalized 7-day plan
└──────────────────────────┘
        │
        ▼
  outputs/study_plan_<topic>.md
```

All agents share a single **`StudyState`** TypedDict that is passed through the LangGraph pipeline. Each agent reads what it needs and writes only its own fields — no context is lost between handoffs.

---

## Individual Contributions

| Student | Agent | Tool | Test File |
|---|---|---|---|
| Member A | `assessment_agent.py` | `quiz_parser_tool.py` | `test_assessment_agent.py` |
| **Reshan** | `gap_analyst_agent.py` | `wiki_tool.py` | `test_gap_analyst_agent.py` |
| Member C | `question_generator_agent.py` | `flashcard_tool.py` | `test_question_generator_agent.py` |
| Member D | `study_planner_agent.py` | `study_plan_writer_tool.py` | `test_study_planner_agent.py` |

> Replace "Member A / C / D" with actual names before submission.

---

## Configuration

All settings can be overridden via environment variables — no code changes needed:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_MODEL` | `llama3:8b` | Model tag to use |
| `OLLAMA_TIMEOUT` | `120` | HTTP timeout in seconds |
| `EDUMAS_LIVE` | _(unset)_ | Set to `1` to enable LLM-as-a-Judge tests |
| `EDUMAS_DEBUG` | _(unset)_ | Set to `1` for verbose DEBUG logs in stdout |

---

## Troubleshooting

**"Could not reach Ollama at http://localhost:11434"**
→ Run `ollama serve` in a separate terminal and keep it open.

**"Quiz file not found"**
→ Check the path passed to `main.py`. Run `python main.py data/sample_quiz.json` to test with the bundled file.

**Slow responses / timeout errors**
→ Increase the timeout: `set OLLAMA_TIMEOUT=300` and re-run. Consider a smaller model: `set OLLAMA_MODEL=phi3`.

**Model produces fewer than 5 questions or malformed output**
→ This is an SLM reliability issue. Re-run the pipeline — the output is non-deterministic and usually succeeds on the second attempt.

---

## Technical Report

See [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md) for the full 8-page technical report covering system architecture, agent design, state management, tool descriptions, and evaluation methodology.

---

## GitHub Repository

> _(insert your repository URL here before submission)_
