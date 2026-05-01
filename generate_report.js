const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  PageNumber, Header, Footer, LevelFormat, TableOfContents,
  PageBreak, ExternalHyperlink
} = require("docx");
const fs = require("fs");
const path = require("path");

// ── colour palette ───────────────────────────────────────────────────────────
const BLUE      = "1F3864";   // dark navy  – headings
const ACCENT    = "2E75B6";   // mid blue   – section rule
const LIGHT_BG  = "EBF3FB";   // pale blue  – table header, code
const CODE_FONT = "Courier New";
const BODY_FONT = "Calibri";

// ── helpers ──────────────────────────────────────────────────────────────────
const BORDER = { style: BorderStyle.SINGLE, size: 1, color: "BFBFBF" };
const CELL_BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };
const CELL_MARGINS = { top: 100, bottom: 100, left: 140, right: 140 };

function body(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: BODY_FONT, size: 22 })],
    spacing: { after: 120 },
  });
}

function bodyRuns(runs) {
  return new Paragraph({
    children: runs,
    spacing: { after: 120 },
  });
}

function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    children: [new TextRun({ text, font: BODY_FONT, size: 22 })],
    spacing: { after: 60 },
  });
}

function numbered(text) {
  return new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    children: [new TextRun({ text, font: BODY_FONT, size: 22 })],
    spacing: { after: 60 },
  });
}

function code(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: CODE_FONT, size: 18 })],
    shading: { fill: "F2F2F2", type: ShadingType.CLEAR },
    spacing: { before: 40, after: 40 },
    indent: { left: 360 },
  });
}

function gap(size = 120) {
  return new Paragraph({ children: [], spacing: { after: size } });
}

function sectionRule() {
  return new Paragraph({
    children: [],
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 1 } },
    spacing: { before: 60, after: 200 },
  });
}

function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, font: BODY_FONT, size: 32, bold: true, color: BLUE })],
    spacing: { before: 360, after: 160 },
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, font: BODY_FONT, size: 26, bold: true, color: BLUE })],
    spacing: { before: 240, after: 120 },
  });
}

function heading3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text, font: BODY_FONT, size: 24, bold: true, color: "404040" })],
    spacing: { before: 180, after: 80 },
  });
}

function label(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: BODY_FONT, size: 22, bold: true })],
    spacing: { after: 60 },
  });
}

// colWidths must sum to 9026 (A4 with 1" margins)
function makeTable(headers, rows, colWidths) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) =>
      new TableCell({
        borders: CELL_BORDERS,
        margins: CELL_MARGINS,
        width: { size: colWidths[i], type: WidthType.DXA },
        shading: { fill: LIGHT_BG, type: ShadingType.CLEAR },
        children: [new Paragraph({
          children: [new TextRun({ text: h, bold: true, font: BODY_FONT, size: 20 })],
        })],
      })
    ),
  });

  const dataRows = rows.map(row =>
    new TableRow({
      children: row.map((cell, i) =>
        new TableCell({
          borders: CELL_BORDERS,
          margins: CELL_MARGINS,
          width: { size: colWidths[i], type: WidthType.DXA },
          children: [new Paragraph({
            children: [new TextRun({ text: cell, font: BODY_FONT, size: 20 })],
          })],
        })
      ),
    })
  );

  return new Table({
    width: { size: 9026, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [headerRow, ...dataRows],
  });
}

// ── document ─────────────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }],
      },
      {
        reference: "numbers",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }],
      },
      {
        reference: "numbers2",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }],
      },
    ],
  },

  styles: {
    default: {
      document: { run: { font: BODY_FONT, size: 22 } },
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: BODY_FONT, color: BLUE },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 },
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: BODY_FONT, color: BLUE },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 },
      },
      {
        id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: BODY_FONT, color: "404040" },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 },
      },
    ],
  },

  sections: [
    // ── TITLE PAGE ────────────────────────────────────────────────────────────
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ children: [PageNumber.CURRENT], font: BODY_FONT, size: 18, color: "808080" }),
            ],
          })],
        }),
      },
      children: [
        gap(2000),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Sri Lanka Institute of Information Technology", font: BODY_FONT, size: 26, bold: true, color: BLUE })],
          spacing: { after: 120 },
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "SE4010 – Current Trends in Software Engineering", font: BODY_FONT, size: 24, color: "404040" })],
          spacing: { after: 120 },
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Assignment 2 – Machine Learning", font: BODY_FONT, size: 24, color: "404040" })],
          spacing: { after: 600 },
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: ACCENT, space: 1 } },
          spacing: { after: 600 },
          children: [],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "EduMAS", font: BODY_FONT, size: 56, bold: true, color: BLUE })],
          spacing: { after: 160 },
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "A Locally-Hosted Multi-Agent Personalized Learning System", font: BODY_FONT, size: 28, color: "404040" })],
          spacing: { after: 120 },
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Technical Report", font: BODY_FONT, size: 24, italics: true, color: "606060" })],
          spacing: { after: 800 },
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "May 2025", font: BODY_FONT, size: 22, color: "404040" })],
          spacing: { after: 200 },
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "GitHub: https://github.com/Hirusha-Chamod/CTSE-Assigment2", font: BODY_FONT, size: 20, color: "808080" })],
        }),
      ],
    },

    // ── MAIN CONTENT ─────────────────────────────────────────────────────────
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ children: [PageNumber.CURRENT], font: BODY_FONT, size: 18, color: "808080" }),
            ],
          })],
        }),
      },
      children: [

        // ── 1. Problem Domain ───────────────────────────────────────────────
        heading1("1. Problem Domain"),
        sectionRule(),

        heading2("1.1  Background"),
        body("Students preparing for examinations often receive quiz results that reveal weak areas without any actionable guidance on what to study or how to prioritize recovery. A human tutor would normally: (1) identify the weakest topic, (2) research prerequisite concepts, (3) design targeted practice questions, and (4) build a structured study schedule. Automating this four-step process end-to-end is a well-defined, domain-appropriate problem for a Multi-Agent System."),

        heading2("1.2  Problem Statement"),
        body("Given a student's quiz attempt (a JSON file recording per-question topic labels and correctness), produce a personalized, topic-specific study plan that includes a knowledge brief, practice flashcards, and a 7-day schedule — with no human intervention and no cloud dependencies."),

        heading2("1.3  Why Multi-Agent?"),
        body("Each phase of the problem requires a distinct reasoning style. Encoding all four responsibilities in one LLM call degrades output quality and destroys traceability. Decomposing them into agents lets each carry a tight, purpose-built system prompt and interact with a purpose-built tool."),
        gap(80),
        makeTable(
          ["Phase", "Reasoning Style", "Agent"],
          [
            ["Identify the weakest topic", "Deterministic calculation", "AssessmentAgent"],
            ["Summarise prerequisite knowledge", "Grounded retrieval + compression", "GapAnalystAgent"],
            ["Generate self-test material", "Creative but format-constrained", "QuestionGeneratorAgent"],
            ["Produce an actionable schedule", "Planning + reference injection", "StudyPlannerAgent"],
          ],
          [3200, 3000, 2826]
        ),
        gap(),

        // ── 2. System Architecture ──────────────────────────────────────────
        heading1("2. System Architecture"),
        sectionRule(),

        heading2("2.1  Technology Choices"),
        makeTable(
          ["Layer", "Technology", "Reason"],
          [
            ["Orchestrator", "LangGraph", "Explicit state machine; each node returns a partial StudyState that LangGraph merges, giving deterministic transitions and a clear debug surface"],
            ["LLM Engine", "Ollama (llama3:8b)", "Zero cost, local execution, no data leaves the machine"],
            ["LLM Interface", "Direct HTTP to localhost:11434", "No extra SDK; full control over request/response logging"],
            ["Database", "SQLite", "No server required; ships with Python standard library"],
            ["Logging", "Python logging + RotatingFileHandler", "Every tool call and LLM invocation recorded in logs/run.log"],
            ["Testing", "pytest + hypothesis", "Property-based tool tests + LLM-as-a-Judge agent tests"],
          ],
          [2200, 2400, 4426]
        ),
        gap(),

        heading2("2.2  Pipeline Overview"),
        body("The system orchestrates 4 agents in a strict sequential LangGraph pipeline. A shared StudyState TypedDict is created at startup and threaded through every node. Each agent reads what it needs and writes only its own fields — no context is ever overwritten silently."),
        gap(60),
        numbered("START → AssessmentAgent: Reads quiz JSON via quiz_parser_tool, identifies the weakest topic, writes weak_topic to state"),
        numbered("AssessmentAgent → GapAnalystAgent: Fetches Wikipedia summary via wiki_tool, synthesises a 3-bullet knowledge brief, writes knowledge_brief to state"),
        numbered("GapAnalystAgent → QuestionGeneratorAgent: Generates 5 practice Q/A pairs via Ollama, persists them to SQLite via flashcard_tool, writes practice_questions to state"),
        numbered("QuestionGeneratorAgent → StudyPlannerAgent: Produces a 7-day Markdown study plan via Ollama, writes it to disk via study_plan_writer_tool, writes study_plan and study_plan_path to state"),
        numbered("StudyPlannerAgent → END"),
        gap(),

        heading2("2.3  Project Structure"),
        ...[
          ".",
          "├── agents/                    # one agent file per team member",
          "│   ├── assessment_agent.py",
          "│   ├── gap_analyst_agent.py",
          "│   ├── question_generator_agent.py",
          "│   └── study_planner_agent.py",
          "├── tools/                     # one custom tool per team member",
          "│   ├── quiz_parser_tool.py",
          "│   ├── wiki_tool.py",
          "│   ├── flashcard_tool.py",
          "│   └── study_plan_writer_tool.py",
          "├── core/                      # shared infrastructure",
          "│   ├── state.py",
          "│   ├── llm.py",
          "│   └── logger.py",
          "├── tests/                     # evaluation scripts (one per student)",
          "├── data/sample_quiz.json",
          "├── main.py",
          "└── requirements.txt",
        ].map(code),
        gap(),

        // ── 3. Agent Design ─────────────────────────────────────────────────
        heading1("3. Agent Design"),
        sectionRule(),
        body("All four agents are implemented as LangGraph nodes: Python functions that receive the full StudyState, call their tool and/or LLM, and return a partial state dict that LangGraph merges back in. Every LLM call is routed through core.llm.ollama_chat, which logs timing and character counts on both sides of every request."),

        heading2("3.1  AssessmentAgent"),
        bodyRuns([
          new TextRun({ text: "Owner: ", bold: true, font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Member A     ", font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Persona: ", bold: true, font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Academic Counselor — precise, data-driven, concise", font: BODY_FONT, size: 22 }),
        ]),
        label("System Prompt Constraints:"),
        bullet("Reply with ONE sentence (under 25 words) naming why the weakest topic needs remediation"),
        bullet("Do NOT recommend study materials (downstream agents handle that)"),
        bullet("Do NOT invent statistics not present in the quiz summary"),
        gap(60),
        label("Reasoning Logic:"),
        body("The agent receives a fully computed per-topic accuracy table from quiz_parser_tool (deterministic). The LLM is only used to produce a human-readable rationale sentence — it cannot affect the topic selection, which prevents hallucination from distorting the pipeline."),
        bodyRuns([new TextRun({ text: "State Writes: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "weak_topic, student_input, logs", font: CODE_FONT, size: 20 })]),

        heading2("3.2  GapAnalystAgent"),
        bodyRuns([
          new TextRun({ text: "Owner: ", bold: true, font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Reshan     ", font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Persona: ", bold: true, font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Educational Curriculum Researcher — grounded, concise, citation-aware", font: BODY_FONT, size: 22 }),
        ]),
        label("System Prompt Constraints:"),
        bullet("Use ONLY information from the supplied Wikipedia extract"),
        bullet('Output EXACTLY THREE bullet points; each starts with "- "'),
        bullet("No preamble, no closing summary, no headings"),
        bullet("Each bullet under 30 words"),
        gap(60),
        label("Reasoning Logic:"),
        body('The LLM acts as a compression and reformatting layer over a grounded text source (Wikipedia). The "use only the supplied text" constraint prevents prior-knowledge hallucination, which is the main failure mode for SLMs on factual topics.'),
        bodyRuns([new TextRun({ text: "State Writes: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "knowledge_brief, logs", font: CODE_FONT, size: 20 })]),

        heading2("3.3  QuestionGeneratorAgent"),
        bodyRuns([
          new TextRun({ text: "Owner: ", bold: true, font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Member C     ", font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Persona: ", bold: true, font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Practice Question Author — structured, format-disciplined", font: BODY_FONT, size: 22 }),
        ]),
        label("System Prompt Constraints:"),
        bullet('Output a single JSON array — no markdown fences, no commentary'),
        bullet('Exactly 5 objects with "question" and "answer" keys'),
        bullet("Questions answerable from the brief; question ≤ 20 words, answer ≤ 40 words"),
        gap(60),
        label("Reasoning Logic:"),
        body("The output contract is enforced at two levels: (1) the system prompt demands raw JSON, and (2) _extract_json_array() parses and validates the response, failing fast with a clear error rather than silently corrupting state. Generated pairs are persisted to SQLite so they survive across runs."),
        bodyRuns([new TextRun({ text: "State Writes: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "practice_questions, logs", font: CODE_FONT, size: 20 })]),

        heading2("3.4  StudyPlannerAgent"),
        bodyRuns([
          new TextRun({ text: "Owner: ", bold: true, font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Member D     ", font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Persona: ", bold: true, font: BODY_FONT, size: 22 }),
          new TextRun({ text: "Senior Study Planner — structured, motivational, builds progressively", font: BODY_FONT, size: 22 }),
        ]),
        label("System Prompt Constraints:"),
        bullet('Output 7 Markdown sections: "### Day N — focus", each with 2–4 bullets'),
        bullet("Days must progress: review → practice → application"),
        bullet("Reference the practice questions on at least two days"),
        bullet("No preamble before Day 1; no closing summary after Day 7"),
        bullet("Total plan under ~400 words"),
        gap(60),
        label("Reasoning Logic:"),
        body("This agent is the synthesis node — it reads everything accumulated in StudyState and produces the final human-deliverable. The strict Markdown contract makes the study_plan_writer_tool downstream deterministic."),
        bodyRuns([new TextRun({ text: "State Writes: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "study_plan, study_plan_path, logs", font: CODE_FONT, size: 20 })]),

        heading2("3.5  Interaction Strategy"),
        body("The pipeline is strictly sequential with no back-edges. This was a deliberate design decision: SLMs running locally on limited VRAM cannot reliably implement conditional routing or self-correction loops without significantly increasing hallucination risk. A linear pipeline lets each agent specialise narrowly and receive a fully-formed context from its predecessor."),

        // ── 4. Custom Tools ─────────────────────────────────────────────────
        heading1("4. Custom Tools"),
        sectionRule(),

        heading2("4.1  quiz_parser_tool.py — File I/O Tool"),
        bodyRuns([new TextRun({ text: "Owner: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "Member A", font: BODY_FONT, size: 22 })]),
        code('def parse_quiz_file(path: str) -> QuizSummary:'),
        code('    """Parse a quiz JSON file and identify the student\'s weakest topic."""'),
        gap(60),
        bodyRuns([new TextRun({ text: "What it does: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "Reads a local JSON file, validates the schema, tallies per-topic accuracy, sorts ascending by accuracy, and returns the lowest-scoring topic as QuizSummary.weakest_topic.", font: BODY_FONT, size: 22 })]),
        bodyRuns([new TextRun({ text: "Error handling: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "QuizParseError (ValueError subclass) for missing file, bad JSON, wrong schema, empty answers, or blank topic strings.", font: BODY_FONT, size: 22 })]),

        heading2("4.2  wiki_tool.py — Public API Tool"),
        bodyRuns([new TextRun({ text: "Owner: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "Reshan", font: BODY_FONT, size: 22 })]),
        code("def fetch_wikipedia_summary(topic: str, timeout: int = 10) -> Optional[str]:"),
        code('    """Fetch the lead-paragraph summary of a topic from Wikipedia."""'),
        gap(60),
        bodyRuns([new TextRun({ text: "What it does: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "Calls the Wikipedia REST API (free, no key required) and returns the extract field.", font: BODY_FONT, size: 22 })]),
        bodyRuns([new TextRun({ text: "Error handling: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "Returns None for blank input; sentinel string for 404; raises WikiToolError on network failure.", font: BODY_FONT, size: 22 })]),

        heading2("4.3  flashcard_tool.py — SQLite Database Tool"),
        bodyRuns([new TextRun({ text: "Owner: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "Member C", font: BODY_FONT, size: 22 })]),
        code("def save_flashcards(topic: str, cards: List[Flashcard], db_path: Path = ...) -> int:"),
        code("def load_flashcards(topic: str, db_path: Path = ...) -> List[Flashcard]:"),
        gap(60),
        bodyRuns([new TextRun({ text: "What it does: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "Creates/opens a SQLite database at data/flashcards.db, auto-creates the flashcards table on first use, bulk-inserts Q/A pairs under a topic label, and supports retrieval by topic.", font: BODY_FONT, size: 22 })]),
        bodyRuns([new TextRun({ text: "Error handling: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "ValueError for empty topic or blank card fields; FlashcardToolError for SQLite failures.", font: BODY_FONT, size: 22 })]),

        heading2("4.4  study_plan_writer_tool.py — Markdown File Tool"),
        bodyRuns([new TextRun({ text: "Owner: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "Member D", font: BODY_FONT, size: 22 })]),
        code("def write_study_plan(topic, knowledge_brief, practice_questions, plan_body, output_dir) -> str:"),
        gap(60),
        bodyRuns([new TextRun({ text: "What it does: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "Assembles a three-section Markdown document, slugifies the topic for the filename, writes to outputs/study_plan_topic_timestamp.md, and returns the absolute path.", font: BODY_FONT, size: 22 })]),
        bodyRuns([new TextRun({ text: "Error handling: ", bold: true, font: BODY_FONT, size: 22 }), new TextRun({ text: "ValueError for empty topic or body; StudyPlanWriteError for filesystem failures.", font: BODY_FONT, size: 22 })]),

        // ── 5. State Management ─────────────────────────────────────────────
        heading1("5. State Management"),
        sectionRule(),

        heading2("5.1  Global State Structure"),
        body("StudyState is a TypedDict defined in core/state.py. LangGraph treats it as an immutable snapshot — each node returns a partial dict of only the keys it writes, and the framework merges it with the current state. No node can accidentally overwrite a key it did not intend to modify."),
        gap(60),
        ...[
          "class StudyState(TypedDict, total=False):",
          "    quiz_path:          str                    # set by main.py at startup",
          "    student_input:      str                    # AssessmentAgent",
          "    weak_topic:         str                    # AssessmentAgent",
          "    knowledge_brief:    str                    # GapAnalystAgent",
          "    practice_questions: List[PracticeQuestion] # QuestionGeneratorAgent",
          "    study_plan:         str                    # StudyPlannerAgent",
          "    study_plan_path:    str                    # StudyPlannerAgent",
          "    logs:               List[str]              # every agent appends",
        ].map(code),
        gap(),

        heading2("5.2  How Context Flows Without Loss"),
        body("Each downstream agent reads only the key(s) it needs — weak_topic is set once by the Assessment Agent and read by every subsequent agent. If any agent finds its required key missing it raises a ValueError immediately (fail-fast principle), preventing silent propagation of an empty context."),
        body("The logs field acts as an in-state execution trace: each agent appends one or two structured strings before returning. The full trace is therefore embedded in the final state object and can be inspected in code without parsing a log file."),

        heading2("5.3  Initialisation"),
        code("state: StudyState = init_state(quiz_path)"),
        code("final: StudyState = app.invoke(state)"),
        gap(),

        // ── 6. Evaluation ───────────────────────────────────────────────────
        heading1("6. Evaluation Methodology"),
        sectionRule(),

        heading2("6.1  Test Organisation"),
        makeTable(
          ["File", "Owner", "Coverage"],
          [
            ["test_assessment_agent.py",        "Member A", "quiz_parser_tool + AssessmentAgent"],
            ["test_gap_analyst_agent.py",        "Reshan",   "wiki_tool + GapAnalystAgent"],
            ["test_question_generator_agent.py", "Member C", "flashcard_tool + QuestionGeneratorAgent"],
            ["test_study_planner_agent.py",      "Member D", "study_plan_writer_tool + StudyPlannerAgent"],
          ],
          [3400, 1600, 4026]
        ),
        gap(),

        heading2("6.2  Three Testing Layers Per Agent"),
        heading3("Layer 1 — Property-Based Tests (hypothesis)"),
        body("Tests run against the tool function with randomly generated inputs, verifying invariants that must hold for any valid input. Example: for any non-empty list of quiz answers, parse_quiz_file must return a weakest_accuracy equal to the minimum accuracy across all topics."),
        heading3("Layer 2 — Mocked-LLM Unit Tests"),
        body("conftest.py provides a patch_ollama fixture that monkeypatches ollama_chat in every module with a deterministic stub. This lets the tests verify the agent's data-wiring logic (tool calls, state writes, error guards) without requiring Ollama. These tests run in milliseconds and pass in CI."),
        heading3("Layer 3 — LLM-as-a-Judge Live Tests (EDUMAS_LIVE=1)"),
        body("For live evaluation, tests/_judge.py sends the agent's actual output plus a contract checklist to a separate Ollama call. The judge returns a structured {passed, score, failures, rationale} verdict. The test asserts verdict[\"passed\"] is True. This validates semantic correctness beyond what string matching alone can check."),

        heading2("6.3  Test Results"),
        bodyRuns([
          new TextRun({ text: "Offline run: ", bold: true, font: BODY_FONT, size: 22 }),
          new TextRun({ text: "30 passed, 4 skipped (live tests — require EDUMAS_LIVE=1) in 3.93s", font: CODE_FONT, size: 20 }),
        ]),

        heading2("6.4  Performance & Reliability Analysis"),
        makeTable(
          ["Concern", "Approach", "Notes"],
          [
            ["SLM hallucination", "Grounded prompts + strict output contracts", "Wiki text injected verbatim; LLM told not to invent"],
            ["Malformed LLM output", "JSON regex extraction + shape validation", "_extract_json_array fails fast rather than propagating bad data"],
            ["Network failure", "WikiToolError with descriptive message", "Agent surfaces error; pipeline terminates cleanly"],
            ["Ollama not running", "OllamaError in core/llm.py", 'Clear message: "Is ollama serve running?"'],
            ["Slow SLM responses", "Configurable OLLAMA_TIMEOUT (default 120s)", "Set OLLAMA_TIMEOUT=300 for slow machines"],
          ],
          [2500, 3200, 3326]
        ),
        gap(),

        // ── 7. Individual Contributions ─────────────────────────────────────
        heading1("7. Individual Contributions"),
        sectionRule(),

        heading2("7.1  Member A — AssessmentAgent"),
        label("Agent built: agents/assessment_agent.py"),
        body("The assessment agent acts as the pipeline entry point. The key design challenge was keeping the LLM role minimal: the topic selection must be deterministic (computed by the tool), and the LLM only generates a one-sentence rationale. This prevents any hallucination from affecting which topic the rest of the pipeline targets."),
        label("Tool implemented: tools/quiz_parser_tool.py"),
        body("Strict schema validation was the main challenge — real quiz files can be malformed in many ways (missing keys, blank topic strings, empty answer lists). The dedicated QuizParseError hierarchy lets the agent give the user an actionable error message."),
        label("Challenges faced:"),
        bullet("Ensuring the weakest topic is chosen deterministically and not influenced by the LLM prompt"),
        bullet("Handling ties in accuracy (resolved by secondary sort on -total to prefer topics with more evidence)"),
        gap(),

        heading2("7.2  Reshan — GapAnalystAgent"),
        label("Agent built: agents/gap_analyst_agent.py"),
        body('The gap analyst is the grounding agent. Its core design principle is that the LLM must not "know" anything beyond the supplied Wikipedia extract — enforced both in the system prompt and in the output contract (3 bullets, no preamble). The agent also appends wiki_chars to the in-state log so downstream agents and evaluators can verify a real fetch occurred.'),
        label("Tool implemented: tools/wiki_tool.py"),
        body("The Wikipedia REST API returns different status codes and response shapes depending on whether the title is found, partially matched, or absent. Careful handling of 404 (return sentinel string) vs. network error (raise WikiToolError) was needed so downstream agents could distinguish \"topic unknown on Wikipedia\" from \"network is down\"."),
        label("Challenges faced:"),
        bullet("URL encoding: topic strings with spaces or special characters must be safely encoded before being interpolated into the API path"),
        bullet("SLM prompt brevity: llama3:8b tends to add a preamble unless the system prompt explicitly forbids it"),
        gap(),

        heading2("7.3  Member C — QuestionGeneratorAgent"),
        label("Agent built: agents/question_generator_agent.py"),
        body("The main design challenge was making SLM output machine-parseable. The agent enforces a JSON output contract and validates the parsed structure with _extract_json_array, which handles model responses that wrap the JSON in markdown fences or prose."),
        label("Tool implemented: tools/flashcard_tool.py"),
        body("The tool needed to be safe for multiple runs on the same topic. SQLite's AUTOINCREMENT primary key and ORDER BY id ASC in load_flashcards ensure stable, reproducible behaviour across runs."),
        label("Challenges faced:"),
        bullet("llama3:8b occasionally produces fewer than 5 Q/A pairs or wraps the JSON in a code block; the regex extractor handles both cases but the shape check was iteratively tightened during testing"),
        gap(),

        heading2("7.4  Member D — StudyPlannerAgent"),
        label("Agent built: agents/study_planner_agent.py"),
        body("The planner is the richest prompt in the pipeline — it receives the full accumulated context and must produce a coherent progressive schedule. The constraint to \"reference the practice questions on at least two days\" ensures the plan is specific to the content rather than generic boilerplate."),
        label("Tool implemented: tools/study_plan_writer_tool.py"),
        body("The tool assembles the final Markdown document from all three upstream products. The filename slug ensures no two runs overwrite each other, and the timestamp makes the run traceable. The _slugify function was tested independently to handle punctuation and whitespace edge cases."),
        label("Challenges faced:"),
        bullet("Local SLMs sometimes produce plans with fewer than 7 days or omit the heading format; the LLM-as-a-Judge test catches this and the system prompt was iteratively tightened"),
        gap(),

        // ── 8. GitHub ───────────────────────────────────────────────────────
        heading1("8. GitHub Repository"),
        sectionRule(),
        bodyRuns([
          new TextRun({ text: "Repository: ", bold: true, font: BODY_FONT, size: 22 }),
          new ExternalHyperlink({
            link: "https://github.com/Hirusha-Chamod/CTSE-Assigment2",
            children: [new TextRun({
              text: "https://github.com/Hirusha-Chamod/CTSE-Assigment2",
              style: "Hyperlink", font: BODY_FONT, size: 22,
            })],
          }),
        ]),
        body("All individual contributions are visible in the git history. Each agent, tool, and test file carries an Owner comment at the top identifying the responsible team member."),
        gap(),

        // ── Appendix ────────────────────────────────────────────────────────
        heading1("Appendix: Running the System"),
        sectionRule(),
        label("Step 1 — Install Ollama and pull the model"),
        code("ollama pull llama3:8b"),
        code("ollama serve"),
        gap(80),
        label("Step 2 — Install Python dependencies"),
        code("python -m venv .venv && .venv\\Scripts\\activate"),
        code("pip install -r requirements.txt"),
        gap(80),
        label("Step 3 — Run the full pipeline"),
        code("python main.py"),
        gap(80),
        label("Step 4 — Run offline tests (no Ollama needed)"),
        code("pytest tests/ -v"),
        gap(80),
        label("Step 5 — Run all tests including LLM-as-a-Judge"),
        code("set EDUMAS_LIVE=1 && pytest tests/ -v"),
        gap(80),
        label("Step 6 — View execution trace"),
        code("type logs\\run.log"),
        gap(),
      ],
    },
  ],
});

const outPath = path.join(__dirname, "CTSE_Assignment2_Technical_Report.docx");
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outPath, buffer);
  console.log("Created:", outPath);
});
