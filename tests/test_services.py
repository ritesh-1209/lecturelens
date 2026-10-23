"""
Unit tests for LectureLens services:
- gemini_service (prompt construction, clean_json_text, fallback parser)
- transcription_service (validation of formats and MIME types)
- export_service (PDF generation with unicode, text, markdown)
"""

import unittest
from services.gemini_service import (
    clean_json_text,
    fallback_structured_notes,
    build_system_instruction,
)
from services.transcription_service import (
    validate_audio_file,
    ALLOWED_AUDIO_EXTENSIONS,
)
from services.export_service import (
    sanitize_filename,
    export_to_markdown,
    export_to_text,
    export_to_pdf,
    safe_pdf_text,
)


class ServicesTestCase(unittest.TestCase):

    def test_clean_json_text_strips_markdown_code_fences(self):
        """Verify markdown code blocks are properly stripped from JSON responses."""
        raw = '```json\n{"title": "Test Title", "overview": "Test Overview"}\n```'
        cleaned = clean_json_text(raw)
        self.assertEqual(cleaned, '{"title": "Test Title", "overview": "Test Overview"}')

    def test_clean_json_text_finds_nested_json(self):
        """Verify outer conversational text is stripped when extracting JSON."""
        raw = 'Here is the requested notes JSON object:\n{"title": "Calculus 1"}\nHope this helps!'
        cleaned = clean_json_text(raw)
        self.assertEqual(cleaned, '{"title": "Calculus 1"}')

    def test_fallback_structured_notes_structure(self):
        """Verify fallback generator produces all required schema keys."""
        res = fallback_structured_notes("Raw fallback notes text\n- Bullet one\n- Bullet two", "Math Lecture", "Mathematics")
        self.assertEqual(res["title"], "Math Lecture")
        self.assertEqual(res["subject"], "Mathematics")
        self.assertTrue(len(res["structured_notes"]) > 0)
        self.assertIn("Bullet one", res["structured_notes"][0]["bullet_points"])

    def test_build_system_instruction_preferences(self):
        """Verify system instruction incorporates language and detail levels."""
        instr_hindi = build_system_instruction(
            language="hindi",
            detail_level="detailed",
            include_key_terms=True,
            include_examples_formulas=False,
            include_questions=True,
            include_flashcards=False,
        )
        self.assertIn("Hindi", instr_hindi)
        self.assertIn("in-depth", instr_hindi.lower())

        instr_eng = build_system_instruction(
            language="english",
            detail_level="concise",
            include_key_terms=False,
            include_examples_formulas=True,
            include_questions=False,
            include_flashcards=True,
        )
        self.assertIn("English", instr_eng)
        self.assertIn("high-density", instr_eng.lower())

    def test_validate_audio_file_supported_formats(self):
        """Verify all supported audio extensions are accepted."""
        for ext in ALLOWED_AUDIO_EXTENSIONS.keys():
            valid, mime, err = validate_audio_file(f"recording{ext}")
            self.assertTrue(valid, f"Extension {ext} should be valid")
            self.assertTrue(len(mime) > 0)
            self.assertEqual(err, "")

    def test_validate_audio_file_unsupported_formats(self):
        """Verify unsupported formats return helpful validation error."""
        for bad_ext in [".exe", ".sh", ".py", ".mp4", ".pdf"]:
            valid, mime, err = validate_audio_file(f"file{bad_ext}")
            self.assertFalse(valid)
            self.assertIn("Unsupported audio format", err)

    def test_safe_pdf_text_escaping(self):
        """Verify XML characters and smart typography are safely escaped for ReportLab."""
        raw = '<b>Hello & "Welcome"</b> — 2026'
        safe = safe_pdf_text(raw)
        self.assertIn("&lt;b&gt;", safe)
        self.assertIn("&amp;", safe)
        self.assertNotIn("—", safe)  # Em-dash normalized to hyphen

    def test_pdf_generation_with_unicode_symbols(self):
        """Verify PDF builds without error even with Unicode quotes, dashes, and bullets."""
        notes = {
            "title": "Quantum Mechanics: Schrödinger's Equation & Wave-Particle Duality",
            "subject": "Physics 301",
            "overview": "Study of Planck's constant (h) and de Broglie wavelength λ.",
            "executive_summary": "“Subatomic particles exhibit both wave and particle characteristics.”",
            "structured_notes": [
                {
                    "heading": "Wavefunction Postulates",
                    "subheading": "Born Rule",
                    "content": "The square of the wavefunction magnitude represents probability density: |ψ|².",
                    "bullet_points": ["Normalization condition", "Orthogonality of eigenstates"]
                }
            ],
            "key_concepts": [{"concept": "Superposition", "simple_explanation": "Coexistence of states"}],
            "key_terms": [{"term": "Eigenvalue", "definition": "Observable measurement outcome"}],
            "examples_and_formulas": [
                {
                    "title": "Schrödinger Equation",
                    "type": "formula",
                    "content": "i * h_bar * d(psi)/dt = H * psi",
                    "explanation": "Fundamental equation of quantum evolution."
                }
            ],
            "important_facts": ["Heisenberg Uncertainty: Δx * Δp >= h_bar / 2"],
            "revision_summary": "Memorize operator eigenvalues and commutation relations.",
            "exam_questions": [
                {
                    "question": "What is the physical significance of |ψ|²?",
                    "answer": "Probability density of finding a particle at a given position.",
                    "difficulty": "Easy"
                }
            ],
            "flashcards": [
                {
                    "front": "State Heisenberg Uncertainty Principle",
                    "back": "Position and momentum cannot be simultaneously measured with arbitrary precision.",
                    "category": "Quantum Foundations"
                }
            ]
        }

        pdf_bytes = export_to_pdf(notes)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 2000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
