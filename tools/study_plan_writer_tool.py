"""Study plan writer tool — owned by Member D (Study Planner Agent).

Renders the final 7-day study plan to BOTH a Markdown file and a styled
PDF inside `outputs/`. Both paths are returned so they can be stored in
StudyState and surfaced to the user at the end of the run.

PDF is built with ReportLab Platypus — pure Python, no external binaries.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, TypedDict

from core.logger import get_logger

_logger = get_logger("tool.study_plan_writer")

_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")

# ── PDF colour palette ────────────────────────────────────────────────────────
_NAVY   = "#1F3864"
_BLUE   = "#2E75B6"
_LIGHT  = "#EBF3FB"
_GREY   = "#F5F5F5"
_BLACK  = "#1A1A1A"


class Flashcard(TypedDict):
    question: str
    answer: str


class StudyPlanPaths(TypedDict):
    md_path: str
    pdf_path: str


class StudyPlanWriteError(RuntimeError):
    """Raised when an output file cannot be created or written."""


def _slugify(text: str) -> str:
    """Lowercase + collapse non-alphanumerics to underscores. Always non-empty."""
    slug = _SLUG_RE.sub("_", text.strip().lower()).strip("_")
    return slug or "topic"


# ── Markdown writer ───────────────────────────────────────────────────────────

def _write_markdown(
    topic: str,
    knowledge_brief: str,
    practice_questions: List[Flashcard],
    plan_body: str,
    output_dir: Path,
    timestamp: str,
) -> str:
    """Write the study plan as a Markdown file. Returns the absolute path."""
    file_path = output_dir / f"study_plan_{_slugify(topic)}_{timestamp}.md"

    parts: List[str] = [
        f"# Personalized Study Plan: {topic.strip()}",
        f"_Generated: {datetime.now().isoformat(timespec='seconds')}_",
        "",
        "## 1. Knowledge Brief",
        (knowledge_brief.strip() or "_(no brief produced)_"),
        "",
        "## 2. Practice Questions",
    ]
    if practice_questions:
        for idx, card in enumerate(practice_questions, start=1):
            q = (card.get("question") or "").strip()
            a = (card.get("answer") or "").strip()
            parts.append(f"**Q{idx}.** {q}")
            parts.append(f"> {a}")
            parts.append("")
    else:
        parts.append("_(no questions generated)_")
        parts.append("")

    parts.append("## 3. 7-Day Study Plan")
    parts.append(plan_body.strip())
    parts.append("")

    try:
        file_path.write_text("\n".join(parts), encoding="utf-8")
    except OSError as exc:
        raise StudyPlanWriteError(f"Could not write {file_path}: {exc}") from exc

    _logger.info("Wrote Markdown plan to %s", file_path)
    return str(file_path)


# ── PDF writer ────────────────────────────────────────────────────────────────

def _build_pdf_styles():
    """Return a dict of ReportLab ParagraphStyles for the study plan."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.styles import ParagraphStyle

    navy  = colors.HexColor(_NAVY)
    blue  = colors.HexColor(_BLUE)
    light = colors.HexColor(_LIGHT)
    black = colors.HexColor(_BLACK)
    grey  = colors.HexColor(_GREY)

    return {
        "title": ParagraphStyle(
            "Title",
            fontName="Helvetica-Bold", fontSize=22,
            textColor=navy, spaceAfter=4, alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName="Helvetica", fontSize=11,
            textColor=colors.HexColor("#606060"), spaceAfter=16, alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName="Helvetica-Bold", fontSize=14,
            textColor=navy, spaceBefore=18, spaceAfter=6,
        ),
        "day_heading": ParagraphStyle(
            "DayHeading",
            fontName="Helvetica-Bold", fontSize=12,
            textColor=blue, spaceBefore=12, spaceAfter=4,
            backColor=light, borderPad=4,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName="Helvetica", fontSize=10,
            textColor=black, leftIndent=16, spaceAfter=3,
            bulletIndent=4, bulletText="•",
        ),
        "q_label": ParagraphStyle(
            "QLabel",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=navy, spaceBefore=6, spaceAfter=2,
        ),
        "answer": ParagraphStyle(
            "Answer",
            fontName="Helvetica-Oblique", fontSize=10,
            textColor=colors.HexColor("#404040"),
            leftIndent=16, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica", fontSize=10,
            textColor=black, spaceAfter=4,
        ),
        "divider_space": ParagraphStyle(
            "DividerSpace",
            fontName="Helvetica", fontSize=4, spaceAfter=4,
        ),
    }


def _parse_plan_body(plan_body: str, styles: dict) -> list:
    """Convert the LLM's markdown plan body into ReportLab flowables."""
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.units import mm

    flowables = []
    for line in plan_body.splitlines():
        stripped = line.strip()
        if not stripped:
            flowables.append(Spacer(1, 2 * mm))
        elif stripped.startswith("###"):
            text = stripped.lstrip("#").strip()
            flowables.append(Paragraph(text, styles["day_heading"]))
        elif stripped.startswith("##"):
            text = stripped.lstrip("#").strip()
            flowables.append(Paragraph(text, styles["section"]))
        elif stripped.startswith("-"):
            text = stripped.lstrip("-").strip()
            flowables.append(Paragraph(text, styles["bullet"]))
        else:
            flowables.append(Paragraph(stripped, styles["body"]))
    return flowables


def _write_pdf(
    topic: str,
    knowledge_brief: str,
    practice_questions: List[Flashcard],
    plan_body: str,
    output_dir: Path,
    timestamp: str,
) -> str:
    """Build and write a styled PDF study plan. Returns the absolute path."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table,
            TableStyle,
        )
    except ImportError as exc:
        raise StudyPlanWriteError(
            "reportlab is required for PDF output — run: pip install reportlab"
        ) from exc

    file_path = output_dir / f"study_plan_{_slugify(topic)}_{timestamp}.pdf"
    styles = _build_pdf_styles()
    navy  = colors.HexColor(_NAVY)
    light = colors.HexColor(_LIGHT)
    blue  = colors.HexColor(_BLUE)

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title=f"Study Plan: {topic}",
        author="EduMAS",
    )

    story = []

    # ── Title block ───────────────────────────────────────────────────────────
    story.append(Paragraph(f"Personalized Study Plan", styles["title"]))
    story.append(Paragraph(topic.strip(), styles["subtitle"]))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}",
        styles["subtitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=blue, spaceAfter=12))

    # ── Section 1: Knowledge Brief ────────────────────────────────────────────
    story.append(Paragraph("1. Knowledge Brief", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=navy, spaceAfter=6))

    brief_text = knowledge_brief.strip() or "(no brief produced)"
    for line in brief_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("-"):
            story.append(Paragraph(line.lstrip("-").strip(), styles["bullet"]))
        else:
            story.append(Paragraph(line, styles["body"]))

    story.append(Spacer(1, 6 * mm))

    # ── Section 2: Practice Questions ────────────────────────────────────────
    story.append(Paragraph("2. Practice Questions", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=navy, spaceAfter=6))

    if practice_questions:
        for idx, card in enumerate(practice_questions, start=1):
            q = (card.get("question") or "").strip()
            a = (card.get("answer") or "").strip()

            tbl = Table(
                [[Paragraph(f"Q{idx}. {q}", styles["q_label"]),
                  Paragraph(f"A: {a}", styles["answer"])]],
                colWidths=["45%", "55%"],
            )
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), light),
                ("BACKGROUND", (1, 0), (1, 0), colors.white),
                ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#BFBFBF")),
                ("INNERGRID",  (0, 0), (-1, -1), 0.5, colors.HexColor("#BFBFBF")),
                ("VALIGN",     (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 2 * mm))
    else:
        story.append(Paragraph("(no questions generated)", styles["body"]))

    story.append(Spacer(1, 6 * mm))

    # ── Section 3: 7-Day Study Plan ───────────────────────────────────────────
    story.append(Paragraph("3. 7-Day Study Plan", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=navy, spaceAfter=6))
    story.extend(_parse_plan_body(plan_body, styles))

    try:
        doc.build(story)
    except Exception as exc:
        raise StudyPlanWriteError(f"ReportLab failed to build PDF: {exc}") from exc

    _logger.info("Wrote PDF plan to %s", file_path)
    return str(file_path)


# ── Public API ────────────────────────────────────────────────────────────────

def write_study_plan(
    topic: str,
    knowledge_brief: str,
    practice_questions: List[Flashcard],
    plan_body: str,
    output_dir: Path = _OUTPUT_DIR,
) -> StudyPlanPaths:
    """Write the assembled study plan as both a Markdown and a PDF file.

    Args:
        topic: Topic the plan is built around. Used in titles and filenames.
        knowledge_brief: The 3-bullet brief from the GapAnalystAgent.
        practice_questions: Q/A pairs from the QuestionGeneratorAgent.
        plan_body: The 7-day plan text generated by the StudyPlannerAgent.
        output_dir: Override the default `outputs/` directory.

    Returns:
        StudyPlanPaths with `md_path` and `pdf_path` pointing to the two
        output files (both as absolute path strings).

    Raises:
        ValueError: If `topic` or `plan_body` is empty/whitespace.
        StudyPlanWriteError: If either file cannot be created or written.
    """
    if not topic or not topic.strip():
        raise ValueError("topic must be a non-empty string.")
    if not plan_body or not plan_body.strip():
        raise ValueError("plan_body must be a non-empty string.")

    output_dir = Path(output_dir)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StudyPlanWriteError(f"Could not create {output_dir}: {exc}") from exc

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    md_path  = _write_markdown(topic, knowledge_brief, practice_questions, plan_body, output_dir, timestamp)
    pdf_path = _write_pdf(topic, knowledge_brief, practice_questions, plan_body, output_dir, timestamp)

    return StudyPlanPaths(md_path=md_path, pdf_path=pdf_path)
