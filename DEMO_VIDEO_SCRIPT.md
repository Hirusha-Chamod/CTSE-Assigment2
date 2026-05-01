# EduMAS — Demo Video Script
### SE4010 CTSE Assignment 2 | Target duration: 4–5 minutes

---

## Before You Record

**Set up your screen:**
- Terminal window open at the project root (make the font large — 16pt+)
- File Explorer or VS Code open to the project folder
- Split-screen if possible: terminal on left, file browser on right

**Pre-start checklist:**
- [ ] `ollama serve` is running in a background terminal
- [ ] Virtual environment is activated (`.venv\Scripts\activate`)
- [ ] `data/sample_quiz.json` is visible in the file browser
- [ ] `outputs/` and `logs/` folders are empty (clean run)
- [ ] Close Slack, email, notifications

---

## SEGMENT 1 — Introduction (0:00 – 0:30)

**[Face cam or voice-over. Show the project folder in VS Code or Explorer]**

> "This is EduMAS — a locally-hosted Multi-Agent System built for the SE4010 CTSE Assignment 2.
>
> The system solves a real educational problem: a student submits their quiz results, and EduMAS automatically identifies their weakest topic, researches it, generates practice flashcards, and produces a personalized 7-day study plan — all without any cloud APIs, and all powered by a local language model called Ollama.
>
> We built this using LangGraph as the orchestrator, with four agents working in a sequential pipeline. Let me show you the architecture first."

**[Switch to the project folder — briefly show the layout]**

> "We have four agent files — one per team member — four custom tools, a shared state module, and a full test suite. Let me walk you through a live run."

---

## SEGMENT 2 — Show the Input (0:30 – 1:00)

**[Open `data/sample_quiz.json` in the editor or terminal]**

```bash
cat data/sample_quiz.json
```

> "This is the student's quiz file. Alice answered ten questions across four topics: Photosynthesis, Mitochondria, Calculus, and Linear Algebra. The system will read this, compute per-topic accuracy, and identify Calculus as the weakest topic — she got zero out of three correct."

**[Pause on the file for a moment so the audience can read it]**

---

## SEGMENT 3 — Run the Pipeline (1:00 – 2:30)

**[Switch to the terminal]**

```bash
python main.py
```

> "I'm running the main entry point now. You can see LangGraph firing the four nodes in sequence."

**[Narrate each log line as it appears — keep it natural, not reading robotically]**

When AssessmentAgent logs appear:
> "The Assessment Agent just parsed the quiz file and confirmed Calculus as the weakest topic. It's now passing that to the next agent."

When GapAnalystAgent logs appear:
> "The Gap Analyst is calling the Wikipedia API — you can see it fetching the Calculus extract. This is the wiki_tool, a free public API, no key required. Now it's sending that text to Ollama to synthesise the three-bullet knowledge brief."

When QuestionGeneratorAgent logs appear:
> "The Question Generator received the brief and is asking Ollama to produce five practice Q and A pairs in a strict JSON format. Once it gets the response, it saves those flashcards to a local SQLite database using the flashcard tool."

When StudyPlannerAgent logs appear:
> "Finally, the Study Planner is receiving everything — the topic, the brief, and the practice questions — and producing a seven-day study plan. It then writes the plan to the outputs folder."

When the final summary prints:
> "And we're done. The pipeline completed. You can see it printed the knowledge brief, the five practice questions, and the full seven-day plan right here in the terminal."

---

## SEGMENT 4 — Show the Output (2:30 – 3:15)

**[Open the generated file in `outputs/`]**

```bash
# In terminal — show the file was created
ls outputs/
```

> "The study plan was written to a Markdown file — outputs/study_plan_calculus_timestamp.md. Let me open it."

**[Open the file in VS Code or a Markdown previewer]**

> "You can see three sections: the knowledge brief from Wikipedia, the five practice Q and A pairs saved from the flashcard database, and the full seven-day plan. Day one starts with reviewing the core concepts, and by day seven Alice is applying what she's learned to real problems. The practice questions are referenced in days three and five."

---

## SEGMENT 5 — Show the Logs / Observability (3:15 – 3:40)

**[Open `logs/run.log` in the terminal or editor]**

```bash
type logs\run.log
```

> "For the LLMOps requirement, every single tool call and LLM invocation is logged to logs/run.log with a timestamp, the agent name, elapsed time, and character counts. You can see exactly what each agent sent to Ollama and how long it took to respond. This is the observability layer built into the core.logger module."

---

## SEGMENT 6 — Run the Tests (3:40 – 4:20)

**[Switch back to the terminal]**

```bash
pytest tests/ -v
```

> "Now let me show the test suite. We have four test files — one per team member. Each covers their own agent and tool."

**[Narrate as tests run]**

> "You can see three layers of testing firing. The property-based tests from the hypothesis library run first — these generate random inputs and check invariants. Then the mocked-LLM unit tests verify that each agent correctly wires its tool calls and state writes without needing Ollama running. And you can see: thirty tests pass."

**[Pause on the results screen]**

> "The four skipped tests are the LLM-as-a-Judge evaluations — those use a second Ollama call to grade each agent's semantic output against a contract checklist. We can enable them with EDUMAS_LIVE=1."

---

## SEGMENT 7 — Wrap-Up (4:20 – 4:50)

**[Return to project overview or face cam]**

> "To summarise what we built:
>
> Four agents in a LangGraph pipeline — Assessment, Gap Analyst, Question Generator, and Study Planner — each owned by one team member.
>
> Four custom tools covering four different real-world interaction types: local file I/O, a public API, a SQLite database, and a Markdown file writer.
>
> Shared global state using a TypedDict that threads through every agent without losing context.
>
> Full observability via structured logging to logs/run.log.
>
> And a thirty-test evaluation harness with property-based tests, mocked-LLM unit tests, and LLM-as-a-Judge live tests.
>
> The full source code is on GitHub at github.com/Hirusha-Chamod/CTSE-Assigment2. Thank you."

---

## Recording Tips

- **Keep the font large** in your terminal so the log output is readable in the recording.
- **Pause after each agent completes** — give the audience 2–3 seconds to read the log lines before narrating.
- **Don't rush the test run** — let pytest output scroll fully before moving on.
- **If the model is slow**, consider pre-recording the `python main.py` segment and cutting to the finished output, then recording the tests live.
- **Trim any dead air** between the pipeline starting and the first log lines appearing (LLM warm-up can take 10–20 seconds on first call).

---

## Backup Plan (if Ollama is slow on the day)

Pre-generate a `logs/run.log` and an `outputs/study_plan_calculus_*.md` from a previous run. Walk through those files as a "here's what a completed run looks like" — then run the tests live (they don't need Ollama and complete in under 4 seconds).
