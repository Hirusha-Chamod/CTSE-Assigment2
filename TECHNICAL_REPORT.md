# SE4010 – CTSE | Assignment 2 – Technical Report
## EduMAS: A Locally-Hosted Multi-Agent Personalized Learning System

---

## 1. Problem Domain

### 1.1 Background

Students preparing for examinations often receive quiz results that reveal weak areas without any actionable guidance on what to study or how to prioritize recovery. A human tutor would normally (1) identify the weakest topic, (2) research prerequisite concepts, (3) design targeted practice questions, and (4) build a structured study schedule. Automating this four-step process end-to-end is a well-defined, domain-appropriate problem for a Multi-Agent System.

### 1.2 Problem Statement

**Given** a student's quiz attempt (a JSON file recording per-question topic labels and correctness), **produce** a personalized, topic-specific study plan that includes a knowledge brief, practice flashcards, and a 7-day schedule — with no human intervention and no cloud dependencies.

### 1.3 Why Multi-Agent?

Each phase of the problem requires a distinct _reasoning style_:

| Phase | Reasoning style | Agent |
|---|---|---|
| Identify the weakest topic | Deterministic calculation | AssessmentAgent |
| Summarise prerequisite knowledge | Grounded retrieval + compression | GapAnalystAgent |
| Generate self-test material | Creative but format-constrained | QuestionGeneratorAgent |
| Produce an actionable schedule | Planning + reference injection | StudyPlannerAgent |

Encoding all four responsibilities in one LLM call degrades output quality and destroys traceability. Decomposing them into agents lets each carry a tight, purpose-built system prompt and interact with a purpose-built tool.

---

## 2. System Architecture

### 2.1 High-Level Diagram

```
         ┌──────────────────────────────────────────────────────────┐
         │                     StudyState (TypedDict)               │
         │  quiz_path · student_input · weak_topic ·                │
         │  knowledge_brief · practice_questions ·                  │
         │  study_plan · study_plan_path · logs                     │
         └──────────────────────────────────────────────────────────┘
                ▲  grows with each agent; never overwritten silently

 START
   │
   ▼
┌─────────────────────┐     tool: quiz_parser_tool (file I/O)
│   AssessmentAgent   │──►  Reads quiz JSON, finds weakest topic, adds rationale
└─────────────────────┘
   │
   ▼
┌─────────────────────┐     tool: wiki_tool (public API)
│   GapAnalystAgent   │──►  Fetches Wikipedia extract, synthesises 3-bullet brief
└─────────────────────┘
   │
   ▼
┌────────────────────────────┐   tool: flashcard_tool (SQLite)
│  QuestionGeneratorAgent    │──►  Generates 5 Q/A pairs, persists to local DB
└────────────────────────────┘
   │
   ▼
┌────────────────────────────┐   tool: study_plan_writer_tool (Markdown)
│    StudyPlannerAgent       │──►  Produces 7-day plan, writes outputs/*.md
└────────────────────────────┘
   │
  END
```

### 2.2 Technology Choices

| Layer | Technology | Reason |
|---|---|---|
| Orchestrator | **LangGraph** | Explicit state machine; each node returns a partial `StudyState` that LangGraph merges, giving deterministic state transitions and a clear debug surface |
| LLM engine | **Ollama** (`llama3:8b`) | Zero cost, local execution, no data leaves the machine |
| LLM interface | Direct HTTP to `localhost:11434` | No extra SDK; full control over request/response logging |
| Database | SQLite | No server required; ships with Python stdlib |
| Logging | Python `logging` + `RotatingFileHandler` | Every tool call and LLM invocation recorded in `logs/run.log` |
| Testing | pytest + `hypothesis` | Property-based tool tests + LLM-as-a-Judge agent tests |

### 2.3 Ollama Integration & LLM Dependency

All four agents call Ollama, but with very different levels of dependency on it. The tools themselves **never** call Ollama — they are pure Python (file I/O, public API, SQLite, file writing).

| Agent | Uses Ollama for | Core logic without Ollama |
|---|---|---|
| **AssessmentAgent** | One-sentence rationale only | The weak topic is still identified correctly — that is pure Python maths in `quiz_parser_tool`. Ollama only adds a human-readable "why" sentence. |
| **GapAnalystAgent** | Compressing the Wikipedia text into 3 bullets | Pipeline fails — the knowledge brief is the primary output of this agent. |
| **QuestionGeneratorAgent** | Generating the 5 Q/A pairs as a JSON array | Pipeline fails — no questions means nothing to save to SQLite. |
| **StudyPlannerAgent** | Writing the entire 7-day plan body | Pipeline fails — no plan body means no file written to disk. |

**Key design insight:** The AssessmentAgent deliberately minimises LLM involvement — topic selection is deterministic so hallucination cannot distort what the rest of the pipeline studies. The three downstream agents are LLM-heavy by necessity; their outputs are creative/generative by nature. If Ollama is not running, the pipeline will fail at the AssessmentAgent's rationale step and nothing downstream will execute. All four agents require `ollama serve` to be active for a complete run.

### 2.4 Project Layout

```
.
├── agents/                    # one agent file per team member
│   ├── assessment_agent.py
│   ├── gap_analyst_agent.py
│   ├── question_generator_agent.py
│   └── study_planner_agent.py
├── tools/                     # one custom tool per team member
│   ├── quiz_parser_tool.py
│   ├── wiki_tool.py
│   ├── flashcard_tool.py
│   └── study_plan_writer_tool.py
├── core/                      # shared infrastructure
│   ├── state.py               # TypedDict definitions
│   ├── llm.py                 # Ollama HTTP wrapper
│   └── logger.py              # File + stdout logging setup
├── tests/                     # evaluation scripts
│   ├── conftest.py            # shared fixtures, patch_ollama, live_only marker
│   ├── _judge.py              # LLM-as-a-Judge helper
│   ├── test_assessment_agent.py
│   ├── test_gap_analyst_agent.py
│   ├── test_question_generator_agent.py
│   └── test_study_planner_agent.py
├── data/sample_quiz.json      # sample input
├── outputs/                   # generated study plans (gitignored)
├── logs/                      # execution traces (gitignored)
├── main.py                    # LangGraph entrypoint
└── requirements.txt
```

---

## 3. Agent Design

All four agents are implemented as **LangGraph nodes**: Python functions that receive the full `StudyState`, call their tool and/or LLM, and return a _partial_ state dict that LangGraph merges back in. Every LLM call is routed through `core.llm.ollama_chat`, which logs timing and character counts on both sides of every request.

### 3.1 AssessmentAgent (`agents/assessment_agent.py`)
**Owner: Member A**

**Persona:** Academic Counselor — precise, data-driven, concise.

**System prompt constraints:**
- Reply with ONE sentence (under 25 words) naming why the weakest topic needs remediation.
- Do NOT recommend study materials (downstream agents handle that).
- Do NOT invent statistics not present in the quiz summary.

**Reasoning logic:** The agent receives a fully computed per-topic accuracy table from `quiz_parser_tool` (deterministic). The LLM is only used to produce a human-readable rationale sentence — it cannot affect the topic selection, which prevents hallucination from distorting the pipeline.

**Writes to state:** `weak_topic`, `student_input`, `logs`.

---

### 3.2 GapAnalystAgent (`agents/gap_analyst_agent.py`)
**Owner: Reshan**

**Persona:** Educational Curriculum Researcher — grounded, concise, citation-aware.

**System prompt constraints:**
- Use ONLY information from the supplied Wikipedia extract.
- Output EXACTLY THREE bullet points; each starts with `- `.
- No preamble, no closing summary, no headings.
- Each bullet under 30 words.

**Reasoning logic:** The LLM acts as a compression and reformatting layer over a grounded text source (Wikipedia). The "use only the supplied text" constraint prevents prior-knowledge hallucination, which is the main failure mode for SLMs on factual topics.

**Writes to state:** `knowledge_brief`, `logs`.

---

### 3.3 QuestionGeneratorAgent (`agents/question_generator_agent.py`)
**Owner: Member C**

**Persona:** Practice Question Author — structured, format-disciplined.

**System prompt constraints:**
- Output a single JSON array — no markdown fences, no commentary.
- Exactly 5 objects with `question` and `answer` keys.
- Questions answerable from the brief; question ≤ 20 words, answer ≤ 40 words.

**Reasoning logic:** The output contract is enforced at two levels: (1) the system prompt demands raw JSON, and (2) `_extract_json_array()` parses and validates the response, failing fast with a clear error rather than silently corrupting state. Generated pairs are also persisted to SQLite by `flashcard_tool` so they survive across runs.

**Writes to state:** `practice_questions`, `logs`.

---

### 3.4 StudyPlannerAgent (`agents/study_planner_agent.py`)
**Owner: Member D**

**Persona:** Senior Study Planner — structured, motivational, builds progressively.

**System prompt constraints:**
- Output 7 Markdown sections: `### Day N — <focus>`, each with 2–4 bullets.
- Days must progress: review → practice → application.
- Reference the practice questions on at least two days.
- No preamble before Day 1; no closing summary after Day 7.
- Total plan under ~400 words.

**Reasoning logic:** This agent is the synthesis node — it reads everything that was accumulated in `StudyState` (`weak_topic`, `knowledge_brief`, `practice_questions`) and produces the final human-deliverable. The strict Markdown contract makes the `study_plan_writer_tool` downstream deterministic (it simply wraps the body in a file skeleton).

**Writes to state:** `study_plan`, `study_plan_path`, `logs`.

---

### 3.5 Interaction Strategy

The pipeline is **strictly sequential with no back-edges**. This was a deliberate design decision: SLMs running locally on limited VRAM cannot reliably implement conditional routing or self-correction loops without significantly increasing hallucination risk. A linear pipeline lets each agent specialize narrowly and receive a fully-formed context from its predecessor.

---

## 4. Custom Tools

### 4.1 `quiz_parser_tool.py` — File I/O Tool
**Owner: Member A**

```python
def parse_quiz_file(path: str) -> QuizSummary:
    """Parse a quiz JSON file and identify the student's weakest topic."""
```

- **What it does:** Reads a local JSON file, validates the schema, tallies per-topic accuracy, sorts ascending by accuracy, and returns the lowest-scoring topic as `QuizSummary.weakest_topic`.
- **Error handling:** `QuizParseError` (a `ValueError`) for missing file, bad JSON, wrong schema, empty answers, blank topic strings.
- **Example:**
  ```json
  Input:  {"student": "Alice", "answers": [{"topic":"Calculus","correct":false}, ...]}
  Output: {"student":"Alice","weakest_topic":"Calculus","weakest_accuracy":0.0,"per_topic":[...]}
  ```

---

### 4.2 `wiki_tool.py` — Public API Tool
**Owner: Reshan**

```python
def fetch_wikipedia_summary(topic: str, timeout: int = 10) -> Optional[str]:
    """Fetch the lead-paragraph summary of a topic from Wikipedia."""
```

- **What it does:** Calls `https://en.wikipedia.org/api/rest_v1/page/summary/{title}` (free, no key required) and returns the `extract` field.
- **Error handling:** Returns `None` for blank input; returns a sentinel string for 404; raises `WikiToolError` (a `RuntimeError`) on network failure or non-200 status.
- **Example:**
  ```
  Input:  "Calculus"
  Output: "Calculus is the mathematical study of continuous change..."
  ```

---

### 4.3 `flashcard_tool.py` — SQLite Database Tool
**Owner: Member C**

```python
def save_flashcards(topic: str, cards: List[Flashcard], db_path: Path = ...) -> int:
def load_flashcards(topic: str, db_path: Path = ...) -> List[Flashcard]:
```

- **What it does:** Creates/opens a SQLite database at `data/flashcards.db`, auto-creates the `flashcards` table on first use, bulk-inserts Q/A pairs under a topic label, and supports retrieval by topic.
- **Error handling:** `ValueError` for empty topic or blank card fields; `FlashcardToolError` (a `RuntimeError`) for SQLite failures.
- **Example:**
  ```python
  save_flashcards("Calculus", [{"question":"What is a derivative?","answer":"A rate of change."}])
  # → 1 row inserted
  load_flashcards("Calculus")
  # → [{"question": "What is a derivative?", "answer": "A rate of change."}]
  ```

---

### 4.4 `study_plan_writer_tool.py` — Markdown File Tool
**Owner: Member D**

```python
def write_study_plan(topic, knowledge_brief, practice_questions, plan_body, output_dir) -> str:
```

- **What it does:** Assembles a three-section Markdown document (Knowledge Brief, Practice Questions, 7-Day Plan), slugifies the topic for the filename, writes to `outputs/study_plan_<topic>_<timestamp>.md`, and returns the absolute path.
- **Error handling:** `ValueError` for empty topic or body; `StudyPlanWriteError` (a `RuntimeError`) for filesystem failures.
- **Example output filename:** `outputs/study_plan_calculus_20250501_143200.md`

---

## 5. State Management

### 5.1 Global State Structure

`StudyState` is a `TypedDict` (defined in `core/state.py`). LangGraph treats it as an immutable snapshot — each node returns a **partial dict** of only the keys it writes, and the framework merges it with the current state. No node can accidentally overwrite a key it didn't intend to modify.

```python
class StudyState(TypedDict, total=False):
    quiz_path:          str                    # set by main.py at startup
    student_input:      str                    # ← AssessmentAgent
    weak_topic:         str                    # ← AssessmentAgent
    knowledge_brief:    str                    # ← GapAnalystAgent
    practice_questions: List[PracticeQuestion] # ← QuestionGeneratorAgent
    study_plan:         str                    # ← StudyPlannerAgent
    study_plan_path:    str                    # ← StudyPlannerAgent
    logs:               List[str]              # ← every agent appends
```

### 5.2 How Context Flows Without Loss

Each downstream agent reads only the key(s) it needs — `weak_topic` is set once by the Assessment Agent and read by every subsequent agent. If any agent finds its required key missing it raises a `ValueError` immediately (fail-fast principle), preventing silent propagation of an empty context.

The `logs` field acts as an **in-state execution trace**: each agent appends one or two structured strings (agent name, key values, counts) before returning. This means the full trace is embedded in the final state object and can be inspected in code without parsing a log file.

### 5.3 Initialization

```python
# main.py
state: StudyState = init_state(quiz_path)
# → {quiz_path: "...", student_input: "", weak_topic: "", ..., logs: []}
final: StudyState = app.invoke(state)
```

---

## 6. Evaluation Methodology

### 6.1 Test Organisation

The unified test harness lives in `tests/`. Each student owns exactly one file. All files are collected by `pytest tests/ -v`.

| File | Owner | Coverage |
|---|---|---|
| `test_assessment_agent.py` | Member A | `quiz_parser_tool` + `AssessmentAgent` |
| `test_gap_analyst_agent.py` | Reshan | `wiki_tool` + `GapAnalystAgent` |
| `test_question_generator_agent.py` | Member C | `flashcard_tool` + `QuestionGeneratorAgent` |
| `test_study_planner_agent.py` | Member D | `study_plan_writer_tool` + `StudyPlannerAgent` |

### 6.2 Three Testing Layers Per Agent

**Layer 1 — Property-based tests on the deterministic tool** (`hypothesis`)

Tests run against the tool function with randomly generated inputs, verifying invariants that must hold for *any* valid input. Example: for any non-empty list of quiz answers, `parse_quiz_file` must return a `weakest_accuracy` equal to the minimum accuracy across all topics.

**Layer 2 — Mocked-LLM unit tests on the agent node**

`conftest.py` provides a `patch_ollama` fixture that monkeypatches `ollama_chat` in every module with a deterministic stub. This lets the tests verify the agent's _data-wiring logic_ (tool calls, state writes, error guards) without requiring Ollama. These tests run in milliseconds and pass in CI.

**Layer 3 — LLM-as-a-Judge live tests** (gated by `EDUMAS_LIVE=1`)

For live evaluation, `tests/_judge.py` sends the agent's actual output plus a contract checklist to a separate Ollama call. The judge returns a structured `{passed, score, failures, rationale}` verdict. The test asserts `verdict["passed"] is True`. This approach validates *semantic* correctness (e.g., "does the brief really contain exactly 3 bullets?") beyond what string matching alone can check.

**To run live tests:**
```bash
# Windows
set EDUMAS_LIVE=1 && pytest tests/ -v

# macOS/Linux
EDUMAS_LIVE=1 pytest tests/ -v
```

### 6.3 Test Results (Offline Run)

```
30 passed, 4 skipped (live tests — require EDUMAS_LIVE=1) in 3.93s
```

The 4 skipped tests are the LLM-as-a-Judge tests, which pass when Ollama is running.

### 6.4 Performance & Reliability Analysis

| Concern | Approach | Notes |
|---|---|---|
| SLM hallucination | Grounded prompts + strict output contracts | Wiki text is injected verbatim; LLM told not to invent |
| Malformed LLM output | JSON regex extraction + shape validation | `_extract_json_array` fails fast rather than propagating bad data |
| Network failure (Wikipedia) | `WikiToolError` with descriptive message | Agent surfaces the error; pipeline terminates cleanly |
| Ollama not running | `OllamaError` raised in `core/llm.py` | Clear message: "Is `ollama serve` running?" |
| Slow SLM responses | Configurable `OLLAMA_TIMEOUT` (default 120 s) | Set `OLLAMA_TIMEOUT=300` for slow machines |

---

## 7. Individual Contributions

### Member A — AssessmentAgent

**Agent built:** `agents/assessment_agent.py`
The assessment agent acts as the pipeline entry point. The key design challenge was keeping the LLM role _minimal_: the topic selection must be deterministic (computed by the tool), and the LLM only generates a one-sentence rationale. This prevents any hallucination from affecting which topic the rest of the pipeline targets.

**Tool implemented:** `tools/quiz_parser_tool.py`
Strict schema validation was the main challenge — real quiz files can be malformed in many ways (missing keys, blank topic strings, empty answer lists). The dedicated `QuizParseError` hierarchy lets the agent give the user an actionable error message.

**Challenges faced:**
- Ensuring the weakest topic is chosen deterministically and not influenced by the LLM prompt.
- Handling ties in accuracy (resolved by secondary sort on `-total` to prefer topics with more evidence).

---

### Reshan — GapAnalystAgent

**Agent built:** `agents/gap_analyst_agent.py`
The gap analyst is the grounding agent. Its core design principle is that the LLM must not "know" anything beyond the supplied Wikipedia extract — this is enforced both in the system prompt ("use ONLY information supported by the supplied Wikipedia text") and in the output contract (3 bullets, no preamble). The agent also appends `wiki_chars` to the in-state log so that downstream agents and evaluators can verify a real fetch occurred.

**Tool implemented:** `tools/wiki_tool.py`
The Wikipedia REST API returns different status codes and response shapes depending on whether the title is found, partially matched, or absent. Careful handling of 404 (return sentinel string) vs. network error (raise `WikiToolError`) was needed so downstream agents could distinguish "topic unknown on Wikipedia" from "network is down".

**Challenges faced:**
- URL encoding: topic strings with spaces or special characters must be safely encoded (`urllib.parse.quote`) before being interpolated into the API path.
- SLM prompt brevity: `llama3:8b` tends to add a preamble ("Sure, here are three bullet points...") unless the system prompt explicitly forbids it.

---

### Member C — QuestionGeneratorAgent

**Agent built:** `agents/question_generator_agent.py`
The main design challenge was making SLM output _machine-parseable_. The agent enforces a JSON output contract and validates the parsed structure with `_extract_json_array`, which handles model responses that wrap the JSON in markdown fences or prose. The strict format also means the `flashcard_tool` downstream can bulk-insert without any further parsing.

**Tool implemented:** `tools/flashcard_tool.py`
The tool needed to be idempotent-safe (running the pipeline twice on the same topic appends new cards rather than duplicating them wrongly). SQLite's `AUTOINCREMENT` primary key and the ordering guarantee of `ORDER BY id ASC` in `load_flashcards` ensure stable, reproducible behaviour across runs.

**Challenges faced:**
- `llama3:8b` occasionally produces fewer than 5 Q/A pairs or wraps the JSON in a code block. The `_extract_json_array` regex extractor handles both cases, but the shape check (exactly N items) was iteratively tightened during testing.

---

### Member D — StudyPlannerAgent

**Agent built:** `agents/study_planner_agent.py`
The planner is the richest prompt in the pipeline — it receives the full accumulated context (topic, brief, Q/A pairs) and must produce a coherent progressive schedule. The constraint "reference the practice questions on at least two days" ensures the plan is specific to the content, not generic boilerplate.

**Tool implemented:** `tools/study_plan_writer_tool.py`
The tool assembles the final Markdown document from all three upstream products (brief, Q/A, plan body). The filename slug ensures no two runs overwrite each other, and the timestamp makes the run traceable without needing to open the file. The `_slugify` function was tested independently to handle punctuation, unicode, and whitespace edge cases.

**Challenges faced:**
- Local SLMs sometimes produce plans with fewer than 7 days or omit the `### Day N` heading format. The LLM-as-a-Judge test catches this during live evaluation and the system prompt was iteratively tightened until the format was reliably respected.

---

## 8. GitHub Repository

> **Link:** _(insert your GitHub repository URL here before submission)_

All individual contributions are clearly visible in the git history. Each agent, tool, and test file carries an `Owner:` comment at the top.

---

## Appendix: Running the System

```bash
# 1. Start Ollama
ollama pull llama3:8b
ollama serve

# 2. Install dependencies
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# 3. Run the full pipeline
python main.py
# Output: outputs/study_plan_<topic>_<timestamp>.md

# 4. Run offline tests (no Ollama needed)
pytest tests/ -v

# 5. Run all tests including LLM-as-a-Judge
set EDUMAS_LIVE=1 && pytest tests/ -v   # Windows
EDUMAS_LIVE=1 pytest tests/ -v          # macOS/Linux

# 6. View execution trace
cat logs/run.log
```
