"""
Gemini Service for LectureLens.
Handles communication with Google Gemini API using the official google-genai SDK.
"""

import json
import os
import re
import logging
from typing import Dict, Any, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def get_gemini_client() -> genai.Client:
    """
    Instantiate and return a Gemini Client.
    Validates server-side GEMINI_API_KEY environment variable.
    """
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is not configured on the server. "
            "Please provide a valid API key in your .env file or hosting environment settings."
        )

    return genai.Client(api_key=api_key)


def get_notes_model() -> str:
    """Return configured model for note generation."""
    return os.getenv("GEMINI_NOTES_MODEL", "gemini-3.5-flash").strip()


def build_system_instruction(
    language: str,
    detail_level: str,
    include_key_terms: bool,
    include_examples_formulas: bool,
    include_questions: bool,
    include_flashcards: bool,
) -> str:
    """Construct an academic note-taking system instruction tailored to user preferences."""
    
    lang_instruction = "Maintain the original language of the lecture transcript."
    if language.lower() == "english":
        lang_instruction = "Generate all output in English. Preserve non-English technical terms only where relevant."
    elif language.lower() == "hindi":
        lang_instruction = (
            "Generate the output primarily in clean, readable Hindi (using Devanagari script). "
            "Technical terms and standard scientific jargon can include English transliterations or English terms in parentheses."
        )

    detail_guide = {
        "concise": "Provide a high-density, high-impact summary focusing strictly on core takeaways, high-level architecture, and executive highlights.",
        "standard": "Provide balanced, comprehensive academic notes covering all major concepts, logical flow, and supporting context.",
        "detailed": "Provide an in-depth, thorough breakdown. Elaborate on nuanced arguments, step-by-step logic, background foundations, and detailed applications."
    }.get(detail_level.lower(), "Provide balanced, comprehensive academic notes.")

    instruction = f"""You are LectureLens, an elite academic note-taking assistant and pedagogical synthesizer.
Your mission is to transform raw lecture transcripts into exceptionally well-structured, clear, and comprehensive study notes.

LANGUAGE REQUIREMENT:
{lang_instruction}

DETAIL LEVEL:
{detail_guide}

CORE PEDAGOGICAL PRINCIPLES:
1. Truthfulness & Accuracy: Faithfully preserve the lecture's factual meaning and technical depth.
2. Anti-Hallucination: Never invent facts, quotations, external claims, or formulas that are not supported by the lecture. If a statement in the transcript is unclear or incomplete, explicitly mark it as "[Note: Lecture context was brief or unclear on this point]" rather than guessing.
3. Logical Hierarchy: Organize content hierarchically with descriptive headings, intuitive subheadings, and digestible bullet points.
4. Jargon & Clarity: Explain complex concepts in clean, beginner-accessible language while strictly preserving authentic technical terminology.
5. Inferences: Clearly distinguish explicit lecture statements from reasonable contextual inferences.
6. Cleanliness: Eliminate conversational filler words, repeated stammering, administrative banter, and false starts from the transcript.

OUTPUT FORMAT REQUIREMENTS:
You MUST respond with a single, strictly valid JSON object adhering to this schema:
{{
  "title": "A clear, academic title for this lecture",
  "subject": "Identified subject or academic discipline",
  "overview": "A 2-3 sentence introductory overview of what the lecture addresses",
  "executive_summary": "A cohesive executive summary paragraph encapsulating the core lecture thesis",
  "structured_notes": [
    {{
      "heading": "Major Topic Heading",
      "subheading": "Optional Subtopic or Focus",
      "content": "Narrative explanation of the topic",
      "bullet_points": ["Key takeaway or specific detail", "Another supporting detail"]
    }}
  ],
  "key_concepts": [
    {{
      "concept": "Concept Name",
      "simple_explanation": "Intuitive, beginner-friendly explanation"
    }}
  ],
  "key_terms": [
    {{
      "term": "Technical Term",
      "definition": "Precise definition based on the lecture"
    }}
  ],
  "examples_and_formulas": [
    {{
      "title": "Example or Formula Title",
      "type": "formula | example | calculation | code",
      "content": "The actual formula (e.g. LaTeX/math), code snippet, or scenario",
      "explanation": "Why this example/formula matters and how it works"
    }}
  ],
  "important_facts": [
    "Crucial fact, statistic, or principle to memorize"
  ],
  "revision_summary": "A concise concluding wrap-up for rapid exam-eve revision",
  "exam_questions": [
    {{
      "question": "Realistic exam question testing understanding",
      "answer": "Complete, high-scoring model answer based on the lecture",
      "difficulty": "Easy | Medium | Hard"
    }}
  ],
  "flashcards": [
    {{
      "front": "Prompt or Question",
      "back": "Key Concept or Answer",
      "category": "Topic Category"
    }}
  ]
}}

SECTION FILTERING RULES:
- If 'key_terms' was not requested, keep the key_terms array empty [].
- If 'examples_and_formulas' was not requested, or if the lecture contains no genuine formulas, code, or distinct examples, keep the array empty []. Do NOT fabricate artificial code or formulas.
- If 'exam_questions' was not requested, keep the array empty [].
- If 'flashcards' was not requested, keep the array empty [].

Always return ONLY the JSON object. Do not include markdown code fence formatting (```json) or conversational preamble.
"""
    return instruction


def clean_json_text(raw_text: str) -> str:
    """Clean raw response text to extract valid JSON."""
    text = raw_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # If surrounded by non-JSON wrapper, find outer { and }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace : last_brace + 1]

    return text


def fallback_structured_notes(raw_text: str, title: str, subject: str) -> Dict[str, Any]:
    """Fallback parser if Gemini returns non-JSON or malformed output."""
    logger.warning("Falling back to text-based note structure.")
    return {
        "title": title or "Lecture Study Notes",
        "subject": subject or "General Studies",
        "overview": "Study notes synthesized from the provided lecture transcript.",
        "executive_summary": raw_text[:500] + ("..." if len(raw_text) > 500 else ""),
        "structured_notes": [
            {
                "heading": "Synthesized Notes",
                "subheading": "Main Content",
                "content": raw_text,
                "bullet_points": [line.strip("- *• ") for line in raw_text.splitlines() if line.strip().startswith(("-", "*", "•"))][:10]
            }
        ],
        "key_concepts": [],
        "key_terms": [],
        "examples_and_formulas": [],
        "important_facts": [],
        "revision_summary": "Review the synthesized notes above for your study session.",
        "exam_questions": [],
        "flashcards": []
    }


def generate_notes_from_transcript(
    transcript: str,
    title: Optional[str] = None,
    subject: Optional[str] = None,
    language: str = "auto",
    detail_level: str = "standard",
    preferences: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """
    Generate structured notes from a lecture transcript using Gemini.
    """
    if not transcript or len(transcript.strip()) < 15:
        raise ValueError("Transcript is too short or empty. Please provide meaningful lecture content.")

    if preferences is None:
        preferences = {
            "include_key_terms": True,
            "include_examples_formulas": True,
            "include_questions": True,
            "include_flashcards": True,
        }

    client = get_gemini_client()
    model_name = get_notes_model()

    system_instruction = build_system_instruction(
        language=language,
        detail_level=detail_level,
        include_key_terms=preferences.get("include_key_terms", True),
        include_examples_formulas=preferences.get("include_examples_formulas", True),
        include_questions=preferences.get("include_questions", True),
        include_flashcards=preferences.get("include_flashcards", True),
    )

    user_prompt = f"""Generate structured academic study notes from the following lecture transcript.

USER METADATA HINTS:
- User Provided Title: {title or 'Not specified (please determine an accurate academic title)'}
- User Provided Subject: {subject or 'Not specified (please determine the appropriate academic subject)'}
- Target Language: {language}
- Detail Level: {detail_level}

USER SECTION PREFERENCES:
- Include Key Terms & Definitions: {preferences.get('include_key_terms', True)}
- Include Examples & Formulas/Code: {preferences.get('include_examples_formulas', True)}
- Include Practice Exam Questions: {preferences.get('include_questions', True)}
- Include Flashcards: {preferences.get('include_flashcards', True)}

LECTURE TRANSCRIPT:
\"\"\"
{transcript.strip()}
\"\"\"
"""

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        temperature=0.2,  # Low temperature for academic fidelity and reduced hallucination
    )

    try:
        response = None
        used_model = model_name
        models_to_try = [model_name]
        if "gemini-3.5-flash" not in models_to_try:
            models_to_try.append("gemini-3.5-flash")

        for try_model in models_to_try:
            try:
                response = client.models.generate_content(
                    model=try_model,
                    contents=user_prompt,
                    config=config,
                )
                used_model = try_model
                break
            except APIError as m_err:
                msg = str(m_err)
                if ("404" in msg or "503" in msg or "NOT_FOUND" in msg.upper()) and try_model != models_to_try[-1]:
                    logger.warning("Model '%s' failed, attempting fallback to '%s'", try_model, models_to_try[-1])
                    continue
                raise

        if not response or not response.text:
            raise ValueError("Empty response received from the Gemini model.")

        cleaned = clean_json_text(response.text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as json_err:
            logger.error("JSON parsing error: %s. Raw text snippet: %s", json_err, cleaned[:200])
            data = fallback_structured_notes(response.text, title or "Lecture Notes", subject or "General")

        # Validate and normalize core fields
        if not data.get("title") or data.get("title") == "Not specified":
            data["title"] = title or "Lecture Study Notes"
        if not data.get("subject") or data.get("subject") == "Not specified":
            data["subject"] = subject or "General Studies"

        # Ensure lists are lists
        for list_field in ["structured_notes", "key_concepts", "key_terms", "examples_and_formulas", "important_facts", "exam_questions", "flashcards"]:
            if list_field not in data or not isinstance(data[list_field], list):
                data[list_field] = []

        # Store metadata
        data["metadata"] = {
            "model_used": model_name,
            "language": language,
            "detail_level": detail_level,
            "transcript_word_count": len(transcript.split()),
        }

        return data

    except APIError as api_err:
        logger.error("Gemini API Error: %s", api_err)
        message = str(api_err)
        if "429" in message or "RESOURCE_EXHAUSTED" in message.upper():
            raise RuntimeError("Gemini API rate limit or quota exceeded. Please wait a moment or check your API quota.")
        elif "403" in message or "PERMISSION_DENIED" in message.upper():
            raise RuntimeError("Gemini API key is invalid or lacks necessary permissions. Please check your API key.")
        elif "404" in message or "NOT_FOUND" in message.upper():
            raise RuntimeError(f"Configured model '{model_name}' was not found. Please verify GEMINI_NOTES_MODEL in .env.")
        else:
            raise RuntimeError(f"Gemini API request failed: {message}")
    except Exception as exc:
        if isinstance(exc, (ValueError, RuntimeError)):
            raise
        logger.exception("Unexpected error during note generation")
        raise RuntimeError(f"Failed to generate study notes: {str(exc)}")
