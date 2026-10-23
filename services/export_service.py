"""
Export Service for LectureLens.
Generates structured downloads in Markdown (.md), Plain Text (.txt), and PDF (.pdf).
"""

import io
import os
import re
import html
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# Register accessible TrueType font if available for wider Unicode support
UNICODE_FONT_NAME = "Helvetica"
try:
    windows_arial = "C:/Windows/Fonts/arial.ttf"
    linux_dejavu = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    if os.path.exists(windows_arial):
        pdfmetrics.registerFont(TTFont("CustomSans", windows_arial))
        UNICODE_FONT_NAME = "CustomSans"
    elif os.path.exists(linux_dejavu):
        pdfmetrics.registerFont(TTFont("CustomSans", linux_dejavu))
        UNICODE_FONT_NAME = "CustomSans"
except Exception as font_err:
    logger.warning("Could not register custom TrueType font, defaulting to Helvetica: %s", font_err)
    UNICODE_FONT_NAME = "Helvetica"


def sanitize_filename(title: str, extension: str) -> str:
    """
    Sanitize lecture title for secure, filesystem-safe filenames.
    Example: 'Operating Systems: Lecture #1 (CS101)' -> 'lecture_notes_operating_systems_lecture_1_cs101.pdf'
    """
    if not title or not title.strip():
        title = "lecture_notes"

    clean = title.strip().lower()
    # Replace non-alphanumeric characters with underscores
    clean = re.sub(r"[^\w\s-]", "", clean)
    clean = re.sub(r"[-\s]+", "_", clean).strip("_")

    # Limit length to 60 characters
    if len(clean) > 60:
        clean = clean[:60].rstrip("_")

    if not clean:
        clean = "lecture_notes"

    ext = extension.lstrip(".")
    return f"lecture_notes_{clean}.{ext}"


def export_to_markdown(notes: Dict[str, Any]) -> str:
    """Generate clean, publication-ready Markdown study notes."""
    title = notes.get("title", "Lecture Study Notes")
    subject = notes.get("subject", "General")
    overview = notes.get("overview", "")
    summary = notes.get("executive_summary", "")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# {title}",
        f"**Subject:** {subject}  ",
        f"**Synthesized on:** {timestamp} via [LectureLens](https://github.com/)  ",
        "",
        "---",
        "",
    ]

    if overview:
        lines.extend([
            "## 📌 Overview",
            overview,
            "",
        ])

    if summary:
        lines.extend([
            "## 📝 Executive Summary",
            f"> {summary}",
            "",
        ])

    # Structured Notes
    structured = notes.get("structured_notes", [])
    if structured:
        lines.append("## 📚 Structured Lecture Notes\n")
        for section in structured:
            heading = section.get("heading", "Notes")
            subheading = section.get("subheading", "")
            content = section.get("content", "")
            bullets = section.get("bullet_points", [])

            lines.append(f"### {heading}")
            if subheading:
                lines.append(f"*{subheading}*\n")
            if content:
                lines.append(f"{content}\n")
            if bullets:
                for b in bullets:
                    lines.append(f"- {b}")
                lines.append("")

    # Key Concepts
    concepts = notes.get("key_concepts", [])
    if concepts:
        lines.append("## 💡 Key Concepts Explained Simply\n")
        for item in concepts:
            c_name = item.get("concept", "")
            c_expl = item.get("simple_explanation", "")
            lines.append(f"- **{c_name}**: {c_expl}")
        lines.append("")

    # Key Terms
    terms = notes.get("key_terms", [])
    if terms:
        lines.append("## 📖 Key Terms & Definitions\n")
        lines.append("| Term | Definition |")
        lines.append("| :--- | :--- |")
        for t in terms:
            term_name = t.get("term", "").replace("|", "-")
            term_def = t.get("definition", "").replace("|", "-")
            lines.append(f"| **{term_name}** | {term_def} |")
        lines.append("")

    # Examples & Formulas
    examples = notes.get("examples_and_formulas", [])
    if examples:
        lines.append("## 🔬 Important Examples, Formulas & Code\n")
        for ex in examples:
            ex_title = ex.get("title", "Example")
            ex_type = ex.get("type", "example").upper()
            ex_content = ex.get("content", "")
            ex_expl = ex.get("explanation", "")

            lines.append(f"#### [{ex_type}] {ex_title}")
            if ex_content:
                lines.append(f"```text\n{ex_content}\n```")
            if ex_expl:
                lines.append(f"**Explanation:** {ex_expl}\n")

    # Important Facts
    facts = notes.get("important_facts", [])
    if facts:
        lines.append("## 🎯 Crucial Facts to Remember\n")
        for i, fact in enumerate(facts, 1):
            lines.append(f"{i}. {fact}")
        lines.append("")

    # Revision Summary
    rev_sum = notes.get("revision_summary", "")
    if rev_sum:
        lines.extend([
            "## ⚡ Final Revision Wrap-Up",
            rev_sum,
            "",
        ])

    # Exam Questions
    questions = notes.get("exam_questions", [])
    if questions:
        lines.append("## ❓ Potential Examination Questions\n")
        for idx, q in enumerate(questions, 1):
            q_text = q.get("question", "")
            a_text = q.get("answer", "")
            diff = q.get("difficulty", "Standard")
            lines.append(f"### Question {idx} [{diff}]")
            lines.append(f"**Q:** {q_text}\n")
            lines.append(f"<details><summary><b>Reveal Model Answer</b></summary>\n\n> {a_text}\n</details>\n")

    # Flashcards
    flashcards = notes.get("flashcards", [])
    if flashcards:
        lines.append("## 🃏 Study Flashcards\n")
        for idx, fc in enumerate(flashcards, 1):
            front = fc.get("front", "")
            back = fc.get("back", "")
            cat = fc.get("category", "General")
            lines.append(f"**Card #{idx} [{cat}]**")
            lines.append(f"- **Front (Prompt):** {front}")
            lines.append(f"- **Back (Answer):** {back}\n")

    lines.append("---\n*Generated automatically by LectureLens — AI-Powered Smart Study Notes.*")
    return "\n".join(lines)


def export_to_text(notes: Dict[str, Any]) -> str:
    """Generate clean, highly readable Plain Text notes with structured ASCII borders."""
    title = notes.get("title", "Lecture Study Notes").upper()
    subject = notes.get("subject", "General Studies")
    overview = notes.get("overview", "")
    summary = notes.get("executive_summary", "")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    divider = "=" * 70
    sub_divider = "-" * 70

    lines = [
        divider,
        f"LECTURELENS STUDY NOTES: {title}",
        f"Subject: {subject} | Date: {timestamp}",
        divider,
        "",
    ]

    if overview:
        lines.extend([
            "[OVERVIEW]",
            overview,
            "",
            sub_divider,
            "",
        ])

    if summary:
        lines.extend([
            "[EXECUTIVE SUMMARY]",
            summary,
            "",
            sub_divider,
            "",
        ])

    # Structured Notes
    structured = notes.get("structured_notes", [])
    if structured:
        lines.append("[STRUCTURED LECTURE NOTES]\n")
        for idx, sec in enumerate(structured, 1):
            heading = sec.get("heading", f"Section {idx}")
            subheading = sec.get("subheading", "")
            content = sec.get("content", "")
            bullets = sec.get("bullet_points", [])

            lines.append(f"{idx}. {heading.upper()}")
            if subheading:
                lines.append(f"   Subtopic: {subheading}")
            if content:
                lines.append(f"   {content}")
            if bullets:
                for b in bullets:
                    lines.append(f"   * {b}")
            lines.append("")
        lines.append(sub_divider)
        lines.append("")

    # Key Concepts
    concepts = notes.get("key_concepts", [])
    if concepts:
        lines.append("[KEY CONCEPTS EXPLAINED SIMPLY]\n")
        for item in concepts:
            lines.append(f"* {item.get('concept', '')}:")
            lines.append(f"  -> {item.get('simple_explanation', '')}")
        lines.append("")
        lines.append(sub_divider)
        lines.append("")

    # Key Terms
    terms = notes.get("key_terms", [])
    if terms:
        lines.append("[KEY TERMS AND DEFINITIONS]\n")
        for t in terms:
            lines.append(f"* {t.get('term', '')}: {t.get('definition', '')}")
        lines.append("")
        lines.append(sub_divider)
        lines.append("")

    # Examples & Formulas
    examples = notes.get("examples_and_formulas", [])
    if examples:
        lines.append("[EXAMPLES, FORMULAS & CODE]\n")
        for ex in examples:
            lines.append(f"Type: {ex.get('type', 'Example').upper()} - {ex.get('title', '')}")
            if ex.get('content'):
                lines.append(f"Content:\n{ex.get('content')}")
            if ex.get('explanation'):
                lines.append(f"Explanation: {ex.get('explanation')}")
            lines.append("")
        lines.append(sub_divider)
        lines.append("")

    # Important Facts
    facts = notes.get("important_facts", [])
    if facts:
        lines.append("[IMPORTANT FACTS TO REMEMBER]\n")
        for i, fact in enumerate(facts, 1):
            lines.append(f"[{i}] {fact}")
        lines.append("")
        lines.append(sub_divider)
        lines.append("")

    # Revision Summary
    rev_sum = notes.get("revision_summary", "")
    if rev_sum:
        lines.extend([
            "[FINAL REVISION SUMMARY]",
            rev_sum,
            "",
            sub_divider,
            "",
        ])

    # Questions
    questions = notes.get("exam_questions", [])
    if questions:
        lines.append("[PRACTICE EXAMINATION QUESTIONS]\n")
        for idx, q in enumerate(questions, 1):
            lines.append(f"Question #{idx} ({q.get('difficulty', 'Standard')}):")
            lines.append(f"Q: {q.get('question', '')}")
            lines.append(f"A: {q.get('answer', '')}")
            lines.append("")
        lines.append(sub_divider)
        lines.append("")

    # Flashcards
    flashcards = notes.get("flashcards", [])
    if flashcards:
        lines.append("[STUDY FLASHCARDS]\n")
        for idx, fc in enumerate(flashcards, 1):
            lines.append(f"Card #{idx} [{fc.get('category', 'General')}]:")
            lines.append(f"  Front: {fc.get('front', '')}")
            lines.append(f"  Back:  {fc.get('back', '')}")
            lines.append("")

    lines.append(divider)
    lines.append("Generated by LectureLens - Smart Notes Generator")
    return "\n".join(lines)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page count."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont(UNICODE_FONT_NAME, 8)
        self.setFillColor(colors.HexColor("#64748B"))  # Slate-500

        # Running header (only on page 2 onwards)
        if self._pageNumber > 1:
            self.drawString(54, 750, "LectureLens — Smart Study Notes")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 744, letter[0] - 54, 744)

        # Footer on all pages
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawString(54, 35, "Generated with LectureLens • Powered by Google Gemini")
        self.drawRightString(letter[0] - 54, 35, page_str)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 47, letter[0] - 54, 47)

        self.restoreState()


def safe_pdf_text(text: str) -> str:
    """Escape text for ReportLab Paragraphs and replace problematic characters safely."""
    if not text:
        return ""
    # XML/HTML escape
    escaped = html.escape(str(text))
    # Replace non-breaking or specific unicode entities with safe equivalents
    escaped = escaped.replace("–", "-").replace("—", "-").replace("“", '"').replace("”", '"').replace("’", "'")
    return escaped


def export_to_pdf(notes: Dict[str, Any]) -> bytes:
    """
    Generate an elegant, professional PDF study document using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_color = colors.HexColor("#1E293B")       # Navy / Slate 800
    accent_color = colors.HexColor("#4338CA")      # Indigo 700
    text_color = colors.HexColor("#334155")        # Slate 700
    subtext_color = colors.HexColor("#64748B")     # Slate 500
    card_bg = colors.HexColor("#F8FAFC")           # Slate 50
    card_border = colors.HexColor("#E2E8F0")       # Slate 200

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName=UNICODE_FONT_NAME,
        fontSize=20,
        leading=24,
        textColor=brand_color,
        spaceAfter=4,
    )

    meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName=UNICODE_FONT_NAME,
        fontSize=10,
        leading=13,
        textColor=accent_color,
        spaceAfter=14,
    )

    h2_style = ParagraphStyle(
        "DocH2",
        parent=styles["Heading2"],
        fontName=UNICODE_FONT_NAME,
        fontSize=13,
        leading=16,
        textColor=accent_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    h3_style = ParagraphStyle(
        "DocH3",
        parent=styles["Heading3"],
        fontName=UNICODE_FONT_NAME,
        fontSize=11,
        leading=14,
        textColor=brand_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName=UNICODE_FONT_NAME,
        fontSize=9.5,
        leading=14,
        textColor=text_color,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "DocBullet",
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    callout_style = ParagraphStyle(
        "DocCallout",
        parent=body_style,
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1E1B4B"),
    )

    code_style = ParagraphStyle(
        "DocCode",
        parent=body_style,
        fontName="Courier",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []

    # Title & Subject Header
    title = notes.get("title", "Lecture Study Notes")
    subject = notes.get("subject", "General Studies")
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    story.append(Paragraph(safe_pdf_text(title), title_style))
    story.append(Paragraph(f"<b>Subject:</b> {safe_pdf_text(subject)} &nbsp;|&nbsp; <b>Date:</b> {date_str}", meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=card_border, spaceBefore=0, spaceAfter=12))

    # Overview Callout
    overview = notes.get("overview", "")
    if overview:
        callout_content = [
            [Paragraph("<b>Overview</b>", h3_style)],
            [Paragraph(safe_pdf_text(overview), callout_style)],
        ]
        t = Table(callout_content, colWidths=[504])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), card_bg),
            ('BOX', (0, 0), (-1, -1), 1, card_border),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

    # Executive Summary
    summary = notes.get("executive_summary", "")
    if summary:
        story.append(Paragraph("Executive Summary", h2_style))
        story.append(Paragraph(safe_pdf_text(summary), body_style))
        story.append(Spacer(1, 8))

    # Structured Notes
    structured = notes.get("structured_notes", [])
    if structured:
        story.append(Paragraph("Structured Notes", h2_style))
        for sec in structured:
            heading = sec.get("heading", "")
            subheading = sec.get("subheading", "")
            content = sec.get("content", "")
            bullets = sec.get("bullet_points", [])

            section_elements = []
            if heading:
                section_elements.append(Paragraph(safe_pdf_text(heading), h3_style))
            if subheading:
                section_elements.append(Paragraph(f"<i>{safe_pdf_text(subheading)}</i>", ParagraphStyle("SubH", parent=body_style, textColor=subtext_color, spaceAfter=4)))
            if content:
                section_elements.append(Paragraph(safe_pdf_text(content), body_style))
            if bullets:
                for b in bullets:
                    section_elements.append(Paragraph(f"&bull; {safe_pdf_text(b)}", bullet_style))
            section_elements.append(Spacer(1, 6))

            story.append(KeepTogether(section_elements[:3]) if len(section_elements) >= 3 else section_elements[0])
            for el in section_elements[3:]:
                story.append(el)

    # Key Concepts
    concepts = notes.get("key_concepts", [])
    if concepts:
        story.append(Paragraph("Key Concepts", h2_style))
        for c in concepts:
            c_name = c.get("concept", "")
            c_exp = c.get("simple_explanation", "")
            story.append(Paragraph(f"<b>{safe_pdf_text(c_name)}</b>: {safe_pdf_text(c_exp)}", bullet_style))
        story.append(Spacer(1, 8))

    # Key Terms Table
    terms = notes.get("key_terms", [])
    if terms:
        story.append(Paragraph("Key Terms & Definitions", h2_style))
        table_data = [[
            Paragraph("<b>Term</b>", ParagraphStyle("TH", parent=body_style, fontName=UNICODE_FONT_NAME, textColor=colors.white)),
            Paragraph("<b>Definition</b>", ParagraphStyle("TH2", parent=body_style, fontName=UNICODE_FONT_NAME, textColor=colors.white))
        ]]
        for t in terms:
            table_data.append([
                Paragraph(f"<b>{safe_pdf_text(t.get('term', ''))}</b>", body_style),
                Paragraph(safe_pdf_text(t.get('definition', '')), body_style)
            ])
        term_table = Table(table_data, colWidths=[140, 364])
        term_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), accent_color),
            ('BOX', (0, 0), (-1, -1), 0.5, card_border),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, card_border),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(term_table)
        story.append(Spacer(1, 10))

    # Examples & Formulas
    examples = notes.get("examples_and_formulas", [])
    if examples:
        story.append(Paragraph("Important Examples & Formulas", h2_style))
        for ex in examples:
            title_p = Paragraph(f"<b>[{safe_pdf_text(ex.get('type', 'Example')).upper()}] {safe_pdf_text(ex.get('title', ''))}</b>", h3_style)
            story.append(title_p)
            if ex.get("content"):
                code_table = Table([[Paragraph(safe_pdf_text(ex.get("content")), code_style)]], colWidths=[504])
                code_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ('PADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(code_table)
                story.append(Spacer(1, 4))
            if ex.get("explanation"):
                story.append(Paragraph(f"<i>Explanation:</i> {safe_pdf_text(ex.get('explanation'))}", body_style))
            story.append(Spacer(1, 6))

    # Important Facts
    facts = notes.get("important_facts", [])
    if facts:
        story.append(Paragraph("Facts to Remember", h2_style))
        for idx, fact in enumerate(facts, 1):
            story.append(Paragraph(f"<b>{idx}.</b> {safe_pdf_text(fact)}", bullet_style))
        story.append(Spacer(1, 8))

    # Revision Summary
    rev_sum = notes.get("revision_summary", "")
    if rev_sum:
        story.append(Paragraph("Revision Summary", h2_style))
        story.append(Paragraph(safe_pdf_text(rev_sum), body_style))
        story.append(Spacer(1, 8))

    # Exam Questions
    questions = notes.get("exam_questions", [])
    if questions:
        story.append(Paragraph("Practice Examination Questions", h2_style))
        for idx, q in enumerate(questions, 1):
            diff = q.get("difficulty", "Standard")
            q_elem = [
                Paragraph(f"<b>Q{idx} ({safe_pdf_text(diff)}):</b> {safe_pdf_text(q.get('question', ''))}", h3_style),
                Paragraph(f"<b>Answer:</b> {safe_pdf_text(q.get('answer', ''))}", body_style),
                Spacer(1, 4),
            ]
            story.append(KeepTogether(q_elem))

    # Build PDF with dynamic NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


def export_notes(notes: Dict[str, Any], export_format: str) -> Tuple[bytes, str, str]:
    """
    Unified dispatcher for note export.
    Returns (data_bytes, mime_type, filename).
    """
    fmt = (export_format or "md").lower().strip()
    title = notes.get("title", "Lecture Notes")

    if fmt in ["markdown", "md"]:
        md_text = export_to_markdown(notes)
        filename = sanitize_filename(title, "md")
        return md_text.encode("utf-8"), "text/markdown; charset=utf-8", filename

    elif fmt in ["text", "txt"]:
        txt_text = export_to_text(notes)
        filename = sanitize_filename(title, "txt")
        return txt_text.encode("utf-8"), "text/plain; charset=utf-8", filename

    elif fmt in ["pdf"]:
        pdf_bytes = export_to_pdf(notes)
        filename = sanitize_filename(title, "pdf")
        return pdf_bytes, "application/pdf", filename

    else:
        raise ValueError(f"Unsupported export format '{export_format}'. Must be md, txt, or pdf.")
