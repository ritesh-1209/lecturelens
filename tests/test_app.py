"""
Automated Test Suite for LectureLens Flask Application.
Tests routing, input validation, audio transcription mock, Gemini notes mock, and exports.
"""

import io
import json
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure we test with clean test configuration
os.environ["FLASK_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test_secret_key"
os.environ["GEMINI_API_KEY"] = "fake_test_key_for_testing"

from app import app
from services.export_service import sanitize_filename, export_to_markdown, export_to_text, export_to_pdf


class LectureLensTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Sample structured notes payload
        self.sample_notes = {
            "title": "Introduction to Operating Systems",
            "subject": "Computer Science 101",
            "overview": "An overview of operating system architectures and processes.",
            "executive_summary": "The operating system manages hardware resources and provides abstractions for user applications.",
            "structured_notes": [
                {
                    "heading": "Process Management",
                    "subheading": "Process Control Block",
                    "content": "A process is a program in execution.",
                    "bullet_points": ["State transitions", "Context switching overhead"]
                }
            ],
            "key_concepts": [
                {
                    "concept": "Virtual Memory",
                    "simple_explanation": "An abstraction that gives each program the illusion of dedicated physical memory."
                }
            ],
            "key_terms": [
                {
                    "term": "Deadlock",
                    "definition": "A condition where two or more processes are unable to proceed because each is waiting for the other."
                }
            ],
            "examples_and_formulas": [
                {
                    "title": "CPU Utilization Formula",
                    "type": "formula",
                    "content": "U = 1 - p^n",
                    "explanation": "Formula for CPU utilization with n concurrent processes."
                }
            ],
            "important_facts": [
                "Context switching involves saving and restoring process CPU registers."
            ],
            "revision_summary": "Review scheduling algorithms and synchronization primitives for the midterm exam.",
            "exam_questions": [
                {
                    "question": "What is the primary difference between a process and a thread?",
                    "answer": "A process has its own isolated address space, whereas threads share the memory of their parent process.",
                    "difficulty": "Medium"
                }
            ],
            "flashcards": [
                {
                    "front": "What does PCB stand for in OS design?",
                    "back": "Process Control Block",
                    "category": "Processes"
                }
            ]
        }

    # -----------------------------------------------------------------
    # Baseline Route Tests
    # -----------------------------------------------------------------

    def test_homepage_loads(self):
        """Verify homepage renders with 200 OK and expected HTML tags."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"LectureLens", response.data)
        self.assertIn(b"Turn lectures into", response.data)
        self.assertIn(b"Studio", response.data)

    def test_health_check(self):
        """Verify health check endpoint returns JSON healthy status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "LectureLens")
        self.assertIn("notes_model", data)

    # -----------------------------------------------------------------
    # /api/notes Validation Tests
    # -----------------------------------------------------------------

    def test_notes_empty_request_body(self):
        """Reject request when JSON body is missing."""
        response = self.client.post("/api/notes", data="")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("JSON body required", data["error"])

    def test_notes_empty_transcript(self):
        """Reject request when transcript is empty string."""
        response = self.client.post(
            "/api/notes",
            json={"transcript": "   "}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("empty", data["error"].lower())

    def test_notes_too_short_transcript(self):
        """Reject request when transcript is shorter than minimum threshold."""
        response = self.client.post(
            "/api/notes",
            json={"transcript": "Too brief lecture"}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("too short", data["error"].lower())

    @patch("services.gemini_service.get_gemini_client")
    def test_notes_missing_api_key_handled(self, mock_client):
        """Verify helpful error is returned when API key is missing."""
        mock_client.side_effect = ValueError("GEMINI_API_KEY is not configured on the server.")
        response = self.client.post(
            "/api/notes",
            json={"transcript": "A sufficiently long valid academic lecture transcript for testing purposes."}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("GEMINI_API_KEY", data["error"])

    @patch("app.generate_notes_from_transcript")
    def test_notes_successful_generation_mocked(self, mock_generate):
        """Verify successful generation flow when Gemini service returns structured notes."""
        mock_generate.return_value = self.sample_notes
        response = self.client.post(
            "/api/notes",
            json={
                "transcript": "A valid lecture about operating systems and thread synchronization.",
                "title": "Intro to OS",
                "subject": "CS 101",
                "language": "english",
                "detail_level": "standard",
            }
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["notes"]["title"], "Introduction to Operating Systems")
        self.assertEqual(len(data["notes"]["flashcards"]), 1)
        self.assertEqual(len(data["notes"]["exam_questions"]), 1)

    # -----------------------------------------------------------------
    # /api/transcribe Audio Tests
    # -----------------------------------------------------------------

    def test_transcribe_missing_file_key(self):
        """Reject request when no audio file is provided."""
        response = self.client.post("/api/transcribe", data={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("No audio file provided", data["error"])

    def test_transcribe_unsupported_audio_extension(self):
        """Reject request when file extension is not an allowed audio format."""
        data = {
            "audio_file": (io.BytesIO(b"fake video data"), "lecture_video.mp4")
        }
        response = self.client.post(
            "/api/transcribe",
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(response.status_code, 400)
        res_json = json.loads(response.data)
        self.assertFalse(res_json["success"])
        self.assertIn("Unsupported audio format", res_json["error"])

    @patch("app.transcribe_audio_file")
    def test_transcribe_successful_mocked(self, mock_transcribe):
        """Verify audio transcription endpoint returns transcript text and word count."""
        mock_transcribe.return_value = {
            "transcript": "Welcome to class. Today we discuss process scheduling and memory management.",
            "word_count": 11,
            "model_used": "gemini-2.5-flash",
            "file_size_bytes": 1024,
        }

        data = {
            "audio_file": (io.BytesIO(b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00"), "test_lecture.wav")
        }
        response = self.client.post(
            "/api/transcribe",
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(response.status_code, 200)
        res_json = json.loads(response.data)
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["word_count"], 11)
        self.assertIn("scheduling", res_json["transcript"])

    # -----------------------------------------------------------------
    # /api/export Endpoint Tests
    # -----------------------------------------------------------------

    def test_export_markdown(self):
        """Verify Markdown export returns text/markdown and sanitized filename."""
        response = self.client.post(
            "/api/export",
            json={"notes": self.sample_notes, "format": "md"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/markdown", response.headers["Content-Type"])
        self.assertIn("lecture_notes_introduction_to_operating_systems.md", response.headers["Content-Disposition"])
        self.assertIn(b"# Introduction to Operating Systems", response.data)

    def test_export_plain_text(self):
        """Verify Plain Text export returns text/plain and structured text."""
        response = self.client.post(
            "/api/export",
            json={"notes": self.sample_notes, "format": "txt"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response.headers["Content-Type"])
        self.assertIn("lecture_notes_introduction_to_operating_systems.txt", response.headers["Content-Disposition"])
        self.assertIn(b"LECTURELENS STUDY NOTES:", response.data)

    def test_export_pdf(self):
        """Verify PDF export returns valid application/pdf binary."""
        response = self.client.post(
            "/api/export",
            json={"notes": self.sample_notes, "format": "pdf"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertIn("lecture_notes_introduction_to_operating_systems.pdf", response.headers["Content-Disposition"])
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_export_invalid_format(self):
        """Reject unsupported export format."""
        response = self.client.post(
            "/api/export",
            json={"notes": self.sample_notes, "format": "docx"}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Unsupported export format", data["error"])

    def test_export_missing_notes_data(self):
        """Reject export when notes payload is empty."""
        response = self.client.post(
            "/api/export",
            json={"notes": None, "format": "pdf"}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])

    # -----------------------------------------------------------------
    # Unit Tests for Helper Functions
    # -----------------------------------------------------------------

    def test_sanitize_filename(self):
        """Verify title sanitization strips special characters and sets correct extension."""
        self.assertEqual(
            sanitize_filename("Lecture 1: Intro to Operating Systems (CS101) & Concurrency!", "pdf"),
            "lecture_notes_lecture_1_intro_to_operating_systems_cs101_concurrency.pdf"
        )
        self.assertEqual(
            sanitize_filename("", "txt"),
            "lecture_notes_lecture_notes.txt"
        )
        self.assertEqual(
            sanitize_filename("   A / B \\ C : D * E ? F \" G < H > I | J   ", "md"),
            "lecture_notes_a_b_c_d_e_f_g_h_i_j.md"
        )

    def test_export_generators_direct(self):
        """Verify direct Python exports contain all sections."""
        md = export_to_markdown(self.sample_notes)
        self.assertIn("# Introduction to Operating Systems", md)
        self.assertIn("## 📌 Overview", md)
        self.assertIn("## 📝 Executive Summary", md)
        self.assertIn("## 📖 Key Terms & Definitions", md)
        self.assertIn("## 🃏 Study Flashcards", md)

        txt = export_to_text(self.sample_notes)
        self.assertIn("LECTURELENS STUDY NOTES: INTRODUCTION TO OPERATING SYSTEMS", txt)
        self.assertIn("[STRUCTURED LECTURE NOTES]", txt)
        self.assertIn("[KEY TERMS AND DEFINITIONS]", txt)

        pdf_bytes = export_to_pdf(self.sample_notes)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
