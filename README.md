# LectureLens — Smart Notes Generator from Lecture Transcripts

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Framework](https://img.shields.io/badge/Backend-Flask-lightgrey?logo=flask)
![AI](https://img.shields.io/badge/AI-Google%20Gemini%20API-4285F4?logo=google)
![SDK](https://img.shields.io/badge/SDK-google--genai%20v2.25.0-success)
![Export](https://img.shields.io/badge/Export-PDF%20%7C%20Markdown%20%7C%20TXT-indigo)
![Tests](https://img.shields.io/badge/Tests-25%20Passing-brightgreen)

> **Turn lectures into learning.**  
> LectureLens is an AI-powered academic study companion that transforms dense lecture transcripts and audio recordings into structured, easy-to-revise notes, key concept breakdowns, interactive 3D flashcards, and exam revision questions using the official Google Gemini API (`google-genai` SDK).

---

## Table of Contents

1. [Key Features](#key-features)
2. [Application Architecture](#application-architecture)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Local Setup & Windows Quickstart](#local-setup--windows-quickstart)
6. [Obtaining a Google Gemini API Key](#obtaining-a-google-gemini-api-key)
7. [Environment Configuration](#environment-configuration)
8. [Testing the Core Workflows](#testing-the-core-workflows)
9. [Running Automated Tests](#running-automated-tests)
10. [Export Formats (PDF, Markdown, Text)](#export-formats-pdf-markdown-text)
11. [Deployment Guide (Render & Alternative Platforms)](#deployment-guide-render--alternative-platforms)
12. [Security, Privacy & Responsible AI](#security-privacy--responsible-ai)
13. [Troubleshooting & FAQ](#troubleshooting--faq)

---

## Key Features

- **Three Flexible Input Methods:**
  - **Option 1: Paste Transcript:** Large, responsive text area with live character and word counters, clear button, and a built-in **"Load Sample Lecture"** button for instant one-click testing.
  - **Option 2: Upload Text File:** Drag-and-drop or file picker for `.txt` files with UTF-8 decoding, file size display, and replace/remove controls.
  - **Option 3: Upload Lecture Audio:** Direct support for `MP3`, `WAV`, `M4A`, `AAC`, `FLAC`, and `OGG` recordings up to 30MB. Audio is transcribed via Google Gemini speech models, displayed in an editable review box, and converted into study notes.
- **Pedagogical Note Synthesis:**
  - Structured hierarchical topics with clear headings, subheadings, and key bullet points.
  - Executive summary and lecture overview callouts.
  - Key concepts explained in intuitive, beginner-accessible language.
  - Key terms and definitions glossary in a clean table view.
  - Important formulas, calculations, and code snippets (extracted strictly when present in the lecture).
  - Crucial memorization facts list.
  - Final exam-eve revision summary.
- **Interactive Active Recall Tools:**
  - **Interactive 3D Flip Flashcards:** Flip cards in carousel view (with keyboard navigation: Space/Enter to flip, Left/Right arrows) or switch to all-cards grid view.
  - **Practice Exam Questions:** Realistic exam-level questions with difficulty badges and click-to-reveal model answers.
- **Universal Multi-Format Export:**
  - **Markdown (`.md`):** Formatted for Obsidian, Notion, or GitHub.
  - **Plain Text (`.txt`):** Clean ASCII-bordered notes for quick reading in any editor.
  - **Formatted PDF (`.pdf`):** Multi-page document generated via ReportLab with running headers, "Page X of Y" footers, callout cards, and clean typography.
- **Strict Anti-Hallucination Design:**
  - System instructions tell Gemini to preserve academic terminology, clearly separate inferences from explicit lecture statements, mark unclear passages, and never fabricate fake code or equations.

---

## Application Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend UI                           │
│  (HTML5, Custom Vanilla CSS, Vanilla JavaScript Controller) │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
         POST /api/notes               POST /api/transcribe
               │                              │
┌──────────────▼──────────────────────────────▼───────────────┐
│                      Flask Backend                          │
│          (app.py - Validation, Rate-Limiting, CORS)         │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼─────────────┐ ┌──────────────▼───────────────┐
│       gemini_service       │ │     transcription_service    │
│  - Structured JSON Prompt  │ │  - client.files.upload()     │
│  - System Instructions     │ │  - Gemini Speech Model       │
│  - Fallback Text Parser    │ │  - Automatic Remote Cleanup  │
└──────────────┬─────────────┘ └──────────────────────────────┘
               │
┌──────────────▼─────────────┐
│       export_service       │
│  - ReportLab PDF Canvas    │
│  - Markdown Serializer     │
│  - ASCII Plain Text        │
└────────────────────────────┘
```

---

## Project Structure

```
lecturelens/
├── app.py                     # Main Flask application and API routes
├── requirements.txt           # Production and testing Python dependencies
├── .env.example               # Template for environment configuration
├── .gitignore                 # Excludes .env, virtual environments, cache, uploads
├── Procfile                   # Gunicorn process definition for Render deployment
├── README.md                  # Comprehensive setup and deployment documentation
├── services/
│   ├── __init__.py            # Services package marker
│   ├── gemini_service.py      # Google Gen AI client, system prompts, JSON parsing
│   ├── transcription_service.py # Audio upload, Gemini transcription, remote cleanup
│   └── export_service.py      # ReportLab PDF, Markdown, and Plain Text generators
├── templates/
│   ├── index.html             # Homepage layout, hero, workspace, and disclosures
│   └── components/
│       └── notes.html         # Structured notes, 3D flashcards, questions component
├── static/
│   ├── css/
│   │   └── style.css          # Modern design system, responsive styles, 3D card flips
│   ├── js/
│   │   └── app.js             # Vanilla JS client logic, tabs, AJAX, and modals
│   └── images/                # Static image assets and logo icons
└── tests/
    ├── __init__.py            # Tests package marker
    ├── test_app.py            # Route, validation, mock Gemini, and export tests
    └── test_services.py       # Unit tests for prompt building, fallbacks, and PDF Unicode
```

---

## Prerequisites

- **Python:** 3.10, 3.11, 3.12, 3.13, or 3.14.
- **Git:** Installed on your computer.
- **Google Gemini API Key:** Free tier or paid key from [Google AI Studio](https://aistudio.google.com/).

---

## Local Setup & Windows Quickstart

Follow these step-by-step instructions in **Windows PowerShell**:

### Step 1: Open Terminal in Project Directory
```powershell
cd D:\Projects\lecturelens
```

### Step 2: Create a Virtual Environment
```powershell
python -m venv .venv
```

### Step 3: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell displays an execution policy error, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and then run the activation script again).*

### Step 4: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 5: Configure Your Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Open `.env` in Notepad or your editor and paste your Gemini API key:
```ini
GEMINI_API_KEY=AIzaSy...your_actual_key_here
GEMINI_NOTES_MODEL=gemini-2.5-flash
GEMINI_TRANSCRIPTION_MODEL=gemini-2.5-flash
PORT=5000
```

### Step 6: Start the LectureLens Server
```powershell
python app.py
```
You will see:
```text
[INFO] LectureLens starting on http://localhost:5000
Environment: Development (Debug OFF)
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

### Step 7: Open the Application
Navigate to `http://localhost:5000` in any web browser.

---

## Obtaining a Google Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google Account.
3. Click **"Get API key"** in the top navigation.
4. Click **"Create API key"** (you can create a key in a new or existing Google Cloud project).
5. Copy the generated key string (starts with `AIzaSy...`).
6. Paste the key into your local `.env` file under `GEMINI_API_KEY=`.

> **Note:** Never commit `.env` or share your API key publicly. LectureLens reads the key strictly server-side and never passes it to the browser.

---

## Environment Configuration

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *(Required)* | Google Gemini API secret key. |
| `GEMINI_NOTES_MODEL` | `gemini-2.5-flash` | Gemini model used for note generation (`gemini-2.5-flash`, `gemini-1.5-flash`). |
| `GEMINI_TRANSCRIPTION_MODEL`| `gemini-2.5-flash` | Gemini model used for audio speech-to-text. |
| `PORT` | `5000` | Port for local server and cloud host binding. |
| `FLASK_DEBUG` | `False` | Enable or disable Flask debug reload mode. |
| `SECRET_KEY` | *(Random string)* | Flask session protection key. |
| `MAX_UPLOAD_SIZE_MB` | `30` | Maximum permitted file upload size in megabytes. |

---

## Testing the Core Workflows

### 1. Test Transcript Input with the Sample Lecture
1. On the homepage, click **"Try Sample Lecture"** or click **"Load Sample Lecture"** above the textarea.
2. The transcript for *Distributed Systems: CAP Theorem & Consistency Models* will load into the editor.
3. Select your desired preferences:
   - **Language:** English, Hindi, or Auto.
   - **Detail Level:** Concise, Standard, or Detailed.
   - **Toggles:** Key Terms, Formulas, Questions, Flashcards.
4. Click **"Generate Smart Notes"**.
5. The synthesized notes will display with collapsible topics, glossary tables, interactive 3D flashcards, and exam questions with toggleable answers.

### 2. Test Audio Transcription
1. Click the **"Option 3: Upload Lecture Audio"** tab.
2. Drag and drop any lecture recording (`.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`).
3. Click **"Transcribe with Gemini"**.
4. The transcription will appear in an editable review box.
5. Click **"Use This Transcript for Notes"** to load it into the generator and synthesize notes.

### 3. Test Export Downloads
- Click **"Markdown (.md)"** to download the structured `.md` file.
- Click **"Text (.txt)"** to download clean ASCII-formatted plain text.
- Click **"Download PDF"** to download the styled ReportLab PDF with page numbers and callout boxes.

---

## Running Automated Tests

LectureLens includes a test suite covering routes, input validations, security headers, file formats, filename sanitizers, and mocked Gemini API responses.

To execute tests:
```powershell
python -m pytest tests/ -v
```

Expected output:
```text
tests/test_app.py::LectureLensTestCase::test_export_generators_direct PASSED
tests/test_app.py::LectureLensTestCase::test_export_invalid_format PASSED
tests/test_app.py::LectureLensTestCase::test_export_markdown PASSED
tests/test_app.py::LectureLensTestCase::test_export_missing_notes_data PASSED
tests/test_app.py::LectureLensTestCase::test_export_pdf PASSED
tests/test_app.py::LectureLensTestCase::test_export_plain_text PASSED
tests/test_app.py::LectureLensTestCase::test_health_check PASSED
tests/test_app.py::LectureLensTestCase::test_homepage_loads PASSED
tests/test_app.py::LectureLensTestCase::test_notes_empty_request_body PASSED
tests/test_app.py::LectureLensTestCase::test_notes_empty_transcript PASSED
tests/test_app.py::LectureLensTestCase::test_notes_missing_api_key_handled PASSED
tests/test_app.py::LectureLensTestCase::test_notes_successful_generation_mocked PASSED
tests/test_app.py::LectureLensTestCase::test_notes_too_short_transcript PASSED
tests/test_app.py::LectureLensTestCase::test_sanitize_filename PASSED
tests/test_app.py::LectureLensTestCase::test_transcribe_missing_file_key PASSED
tests/test_app.py::LectureLensTestCase::test_transcribe_successful_mocked PASSED
tests/test_app.py::LectureLensTestCase::test_transcribe_unsupported_audio_extension PASSED
tests/test_services.py::ServicesTestCase::test_build_system_instruction_preferences PASSED
tests/test_services.py::ServicesTestCase::test_clean_json_text_finds_nested_json PASSED
tests/test_services.py::ServicesTestCase::test_clean_json_text_strips_markdown_code_fences PASSED
tests/test_services.py::ServicesTestCase::test_fallback_structured_notes_structure PASSED
tests/test_services.py::ServicesTestCase::test_pdf_generation_with_unicode_symbols PASSED
tests/test_services.py::ServicesTestCase::test_safe_pdf_text_escaping PASSED
tests/test_services.py::ServicesTestCase::test_validate_audio_file_supported_formats PASSED
tests/test_services.py::ServicesTestCase::test_validate_audio_file_unsupported_formats PASSED

======================== 25 passed in 0.81s ========================
```

---

## Deployment Guide (Render & Alternative Platforms)

### Deploying to Render (Step-by-Step)

1. **Push your code to GitHub:**
   ```powershell
   git add .
   git commit -m "Initial commit of LectureLens"
   git remote add origin https://github.com/<your-username>/lecturelens.git
   git branch -M main
   git push -u origin main
   ```
   *(Ensure `.env` is NOT committed; verify `.gitignore` is present).*

2. **Create a Web Service on Render:**
   - Log in to your [Render Dashboard](https://dashboard.render.com/).
   - Click **"New +"** → **"Web Service"**.
   - Connect your `lecturelens` GitHub repository.

3. **Configure the Service Settings:**
   - **Name:** `lecturelens`
   - **Environment:** `Python 3`
   - **Region:** Any close region (e.g., Oregon, Frankfurt).
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Plan:** Free or Starter.

4. **Set Environment Variables in Render:**
   Under **Environment Variables**, add:
   - `GEMINI_API_KEY`: *(Your Google AI Studio API key)*
   - `GEMINI_NOTES_MODEL`: `gemini-2.5-flash`
   - `GEMINI_TRANSCRIPTION_MODEL`: `gemini-2.5-flash`
   - `SECRET_KEY`: *(A random 32-character string)*
   - `FLASK_DEBUG`: `False`

5. **Deploy & Verify:**
   - Click **"Create Web Service"**.
   - Monitor the deploy logs until you see `Gunicorn running on http://0.0.0.0:...`.
   - Open your public Render URL (e.g., `https://lecturelens.onrender.com`).
   - Test the `/health` endpoint: `https://lecturelens.onrender.com/health` should return `{"status": "healthy"}`.

---

## Security, Privacy & Responsible AI

- **Zero Local Retention:** Transcripts and uploaded audio files are **never** persisted to a database or local disk. Audio files are saved to a temporary path only for the duration of the transcription API call, with guaranteed deletion in a `finally:` block.
- **Remote Resource Cleanup:** When audio is uploaded to the Google Gemini File API, the remote file is deleted via `client.files.delete()` immediately upon transcription completion.
- **Server-Side API Key:** The Gemini API key is never rendered into templates, passed to JavaScript, or returned in API responses.
- **Sanitized Exports:** Filenames generated for PDF, Markdown, and TXT downloads are sanitized using strict regular expressions to avoid directory traversal or illegal filesystem characters.
- **In-Memory Rate Limiting:** Sliding-window request tracking prevents automated spam and accidental duplicate submissions.
- **Academic Disclaimer:** AI-generated notes are designed as study aids. Students are advised to verify notes against primary lecture recordings and course textbooks.

---

## Troubleshooting & FAQ

#### Q: I get a 400 error: "GEMINI_API_KEY is not configured on the server."
**Fix:** Ensure you have created a `.env` file from `.env.example` and set `GEMINI_API_KEY=your_actual_key`. On Render, verify that the environment variable is configured in the Render Dashboard.

#### Q: How do I change the Gemini model?
**Fix:** Set `GEMINI_NOTES_MODEL=gemini-1.5-flash` or another supported model in your `.env` file without changing any application code.

#### Q: What audio formats are supported?
**Fix:** LectureLens supports `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`, and `.webm` up to 30MB. For larger recordings, compress the audio or paste the text transcript directly.

#### Q: How does Hindi output work?
**Fix:** Selecting **Hindi** in the Output Language dropdown prompts Gemini to synthesize notes and definitions in clean Devanagari Hindi while preserving standard English technical terminology in parentheses. Markdown and TXT exports preserve full UTF-8 Devanagari text.

---

## License & Credits

Built as a modern, student-focused educational tool with Flask, Google Gemini SDK (`google-genai`), and ReportLab. Released under the MIT License.
