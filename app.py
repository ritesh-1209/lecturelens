"""
LectureLens — Smart Notes Generator from Lecture Transcripts.
Main Flask Application.
"""

import io
import os
import time
import logging
import tempfile
from datetime import datetime
from collections import defaultdict
from typing import Dict, Tuple

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    Response,
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge, BadRequest

from services.gemini_service import generate_notes_from_transcript
from services.transcription_service import (
    validate_audio_file,
    transcribe_audio_file,
    ALLOWED_AUDIO_EXTENSIONS,
)
from services.export_service import export_notes

# Load local environment variables from .env if present
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lecturelens")

# Initialize Flask application
app = Flask(__name__)

# Security & App Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "lecturelens_dev_key_2026_change_in_prod")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_SIZE_MB", 30)) * 1024 * 1024  # 30MB default

# In-memory rate limiting (IP-based sliding cooldown)
# Keeps last request timestamps per IP to prevent accidental or automated spam
_request_history: Dict[str, list] = defaultdict(list)
RATE_LIMIT_COOLDOWN_SECONDS = 1.5   # Cooldown between sequential generation calls
RATE_LIMIT_MAX_PER_MINUTE = 30      # Max requests per minute per IP


from datetime import datetime, timezone

def check_rate_limit(client_ip: str) -> Tuple[bool, str]:
    """Simple in-memory rate limiting check. Bypassed during test suite execution."""
    if app.config.get("TESTING"):
        return True, ""

    now = time.time()
    history = _request_history[client_ip]

    # Clean entries older than 60 seconds
    _request_history[client_ip] = [ts for ts in history if now - ts < 60]
    history = _request_history[client_ip]

    if history and (now - history[-1]) < RATE_LIMIT_COOLDOWN_SECONDS:
        return False, "Please wait a moment before sending another request."

    if len(history) >= RATE_LIMIT_MAX_PER_MINUTE:
        return False, "Rate limit reached (max 30 requests per minute). Please try again later."

    _request_history[client_ip].append(now)
    return True, ""


@app.after_request
def add_security_headers(response: Response) -> Response:
    """Add baseline HTTP security headers."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# -------------------------------------------------------------
# Web & API Routes
# -------------------------------------------------------------

@app.route("/")
def index():
    """Render the homepage & studio workspace."""
    load_dotenv(override=True)
    has_api_key = bool(os.getenv("GEMINI_API_KEY", "").strip() and os.getenv("GEMINI_API_KEY") != "your_gemini_api_key_here")
    return render_template(
        "index.html",
        has_api_key=has_api_key,
        allowed_extensions=list(ALLOWED_AUDIO_EXTENSIONS.keys()),
        max_upload_mb=app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
    )


@app.route("/health", methods=["GET"])
def health_check():
    """Deployment and uptime health check."""
    load_dotenv(override=True)
    has_api_key = bool(os.getenv("GEMINI_API_KEY", "").strip() and os.getenv("GEMINI_API_KEY") != "your_gemini_api_key_here")
    return jsonify({
        "status": "healthy",
        "service": "LectureLens",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gemini_configured": has_api_key,
        "notes_model": os.getenv("GEMINI_NOTES_MODEL", "gemini-2.5-flash"),
        "transcription_model": os.getenv("GEMINI_TRANSCRIPTION_MODEL", "gemini-2.5-flash"),
    }), 200


@app.route("/api/notes", methods=["POST"])
def api_generate_notes():
    """
    Generate structured academic study notes from a lecture transcript.
    Expects JSON: { transcript, title, subject, language, detail_level, preferences }
    """
    client_ip = request.remote_addr or "unknown"
    allowed, err_msg = check_rate_limit(client_ip)
    if not allowed:
        return jsonify({"success": False, "error": err_msg}), 429

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid request: JSON body required."}), 400

    transcript = data.get("transcript", "").strip()
    if not transcript:
        return jsonify({"success": False, "error": "Lecture transcript is empty. Please paste or upload lecture text."}), 400

    if len(transcript) < 20:
        return jsonify({"success": False, "error": "Lecture transcript is too short. Please provide at least 20 characters."}), 400

    if len(transcript) > 150000:
        return jsonify({"success": False, "error": "Transcript exceeds maximum length (150,000 characters). Please split long recordings."}), 400

    title = data.get("title", "").strip()[:150]
    subject = data.get("subject", "").strip()[:100]
    language = data.get("language", "auto").strip().lower()
    detail_level = data.get("detail_level", "standard").strip().lower()
    preferences = data.get("preferences", {})

    # Validate language & detail choices
    if language not in ["auto", "english", "hindi"]:
        language = "auto"
    if detail_level not in ["concise", "standard", "detailed"]:
        detail_level = "standard"

    try:
        notes = generate_notes_from_transcript(
            transcript=transcript,
            title=title,
            subject=subject,
            language=language,
            detail_level=detail_level,
            preferences=preferences,
        )
        return jsonify({"success": True, "notes": notes}), 200

    except ValueError as ve:
        logger.warning("Validation error in /api/notes: %s", ve)
        return jsonify({"success": False, "error": str(ve)}), 400
    except RuntimeError as re:
        logger.error("Runtime error in /api/notes: %s", re)
        return jsonify({"success": False, "error": str(re)}), 500
    except Exception as exc:
        logger.exception("Unexpected exception in /api/notes")
        return jsonify({"success": False, "error": "Failed to generate notes. Please try again or check API configuration."}), 500


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe_audio():
    """
    Transcribe uploaded lecture audio using Gemini API.
    Expects multipart form file under 'audio_file'.
    """
    client_ip = request.remote_addr or "unknown"
    allowed, err_msg = check_rate_limit(client_ip)
    if not allowed:
        return jsonify({"success": False, "error": err_msg}), 429

    if "audio_file" not in request.files:
        return jsonify({"success": False, "error": "No audio file provided in request."}), 400

    file = request.files["audio_file"]
    if not file or not file.filename:
        return jsonify({"success": False, "error": "No file selected."}), 400

    original_filename = secure_filename(file.filename)
    is_valid, resolved_mime, err_msg = validate_audio_file(original_filename, file.mimetype)
    if not is_valid:
        return jsonify({"success": False, "error": err_msg}), 400

    # Write file to secure temporary location
    ext = os.path.splitext(original_filename)[1].lower()
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tf:
            temp_path = tf.name
            file.save(tf)

        logger.info("Saved temporary audio upload to: %s (%s)", temp_path, resolved_mime)
        result = transcribe_audio_file(temp_path, resolved_mime)

        return jsonify({
            "success": True,
            "transcript": result["transcript"],
            "word_count": result["word_count"],
            "model_used": result["model_used"],
            "original_filename": original_filename,
        }), 200

    except ValueError as ve:
        logger.warning("Validation error in /api/transcribe: %s", ve)
        return jsonify({"success": False, "error": str(ve)}), 400
    except RuntimeError as re:
        logger.error("Runtime error in /api/transcribe: %s", re)
        return jsonify({"success": False, "error": str(re)}), 500
    except Exception as exc:
        logger.exception("Unexpected error in /api/transcribe")
        return jsonify({"success": False, "error": "Audio transcription failed. Please verify the file and your Gemini API credentials."}), 500
    finally:
        # Guarantee local temporary file cleanup
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info("Cleaned up temporary upload file: %s", temp_path)
            except Exception as rm_err:
                logger.warning("Could not remove temp file %s: %s", temp_path, rm_err)


@app.route("/api/export", methods=["POST"])
def api_export_notes():
    """
    Export generated study notes to Markdown (.md), Plain Text (.txt), or PDF (.pdf).
    Expects JSON: { notes: {...}, format: 'md' | 'txt' | 'pdf' }
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid request: JSON body required."}), 400

    notes = data.get("notes")
    if not notes or not isinstance(notes, dict):
        return jsonify({"success": False, "error": "No valid notes data provided for export."}), 400

    export_format = data.get("format", "md").strip().lower()

    try:
        data_bytes, mime_type, filename = export_notes(notes, export_format)
        return send_file(
            io.BytesIO(data_bytes),
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename,
        )
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as exc:
        logger.exception("Error during note export")
        return jsonify({"success": False, "error": f"Failed to export notes: {str(exc)}"}), 500


# -------------------------------------------------------------
# Error Handlers
# -------------------------------------------------------------

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return jsonify({
        "success": False,
        "error": f"File is too large! Maximum allowed upload size is {max_mb}MB."
    }), 413


@app.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify({
        "success": False,
        "error": f"Bad Request: {str(e.description if hasattr(e, 'description') else e)}"
    }), 400


@app.errorhandler(404)
def handle_not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Requested API endpoint not found."}), 404
    return render_template("index.html", error="Page not found. Redirected to home."), 404


@app.errorhandler(500)
def handle_internal_error(e):
    logger.exception("Internal Server Error: %s", e)
    return jsonify({
        "success": False,
        "error": "An internal server error occurred. Please try again later."
    }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    print(f"[INFO] LectureLens starting on http://localhost:{port}")
    print(f"Environment: {'Development (Debug ON)' if debug else 'Production (Debug OFF)'}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
