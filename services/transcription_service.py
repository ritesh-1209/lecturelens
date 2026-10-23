"""
Transcription Service for LectureLens.
Processes lecture audio files using Google Gemini API audio capabilities.
"""

import os
import logging
from typing import Dict, Any, Tuple
from google.genai import types
from google.genai.errors import APIError

from services.gemini_service import get_gemini_client

logger = logging.getLogger(__name__)

# Supported audio extensions and corresponding MIME types
ALLOWED_AUDIO_EXTENSIONS = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/m4a",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".webm": "audio/webm",
}

# Permitted MIME types
ALLOWED_MIME_TYPES = {
    "audio/mp3",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4",
    "audio/aac",
    "audio/flac",
    "audio/x-flac",
    "audio/ogg",
    "audio/webm",
}


def get_transcription_model() -> str:
    """Return configured model for audio transcription."""
    return os.getenv("GEMINI_TRANSCRIPTION_MODEL", "gemini-3.5-transcribe").strip()


def validate_audio_file(filename: str, mime_type: str = "") -> Tuple[bool, str, str]:
    """
    Validate filename extension and determine standard MIME type.
    Returns (is_valid, resolved_mime_type, error_message).
    """
    if not filename:
        return False, "", "No audio file was selected."

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        supported = ", ".join(ALLOWED_AUDIO_EXTENSIONS.keys())
        return False, "", f"Unsupported audio format '{ext}'. Allowed formats: {supported}"

    resolved_mime = ALLOWED_AUDIO_EXTENSIONS[ext]
    if mime_type and mime_type.lower() in ALLOWED_MIME_TYPES:
        resolved_mime = mime_type.lower()

    return True, resolved_mime, ""


def transcribe_audio_file(file_path: str, mime_type: str) -> Dict[str, Any]:
    """
    Upload audio file to Gemini Files API, generate transcript, and cleanup remote resource.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found at {file_path}")

    file_size_bytes = os.path.getsize(file_path)
    if file_size_bytes == 0:
        raise ValueError("The uploaded audio file is empty (0 bytes).")

    client = get_gemini_client()
    model_name = get_transcription_model()

    logger.info("Uploading audio file for transcription: %s (%d bytes)", file_path, file_size_bytes)
    uploaded_file = None

    try:
        # Upload audio to Gemini file store
        upload_config = types.UploadFileConfig(mime_type=mime_type)
        uploaded_file = client.files.upload(file=file_path, config=upload_config)
        logger.info("Audio uploaded successfully to Gemini File API as: %s", uploaded_file.name)

        prompt = (
            "You are a precise academic transcriber. Transcribe the following lecture recording verbatim and with high fidelity. "
            "Guidelines:\n"
            "1. Accurately transcribe scientific, mathematical, medical, computational, and humanities terminology.\n"
            "2. Organize the transcript into clean, readable paragraphs with natural thematic or speaker transitions.\n"
            "3. Omit coughs, mic static, and prolonged dead air, but preserve the substantive lecture discourse.\n"
            "4. Output ONLY the raw lecture transcript text. Do not include markdown meta-commentary, introductory remarks, or summary bullets."
        )

        response = client.models.generate_content(
            model=model_name,
            contents=[uploaded_file, prompt],
        )

        if not response or not response.text:
            raise ValueError("Gemini returned an empty transcription for this audio.")

        transcript_text = response.text.strip()
        word_count = len(transcript_text.split())

        return {
            "transcript": transcript_text,
            "word_count": word_count,
            "model_used": model_name,
            "file_size_bytes": file_size_bytes,
        }

    except APIError as api_err:
        logger.error("Gemini Transcription API error: %s", api_err)
        msg = str(api_err)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg.upper():
            raise RuntimeError("Gemini API transcription quota exceeded. Please wait a moment or check quota.")
        elif "403" in msg or "PERMISSION_DENIED" in msg.upper():
            raise RuntimeError("Gemini API key is invalid or lacks audio processing permissions.")
        elif "404" in msg or "NOT_FOUND" in msg.upper():
            raise RuntimeError(f"Configured transcription model '{model_name}' was not found. Please verify GEMINI_TRANSCRIPTION_MODEL.")
        else:
            raise RuntimeError(f"Audio transcription failed: {msg}")
    except Exception as exc:
        if isinstance(exc, (ValueError, RuntimeError)):
            raise
        logger.exception("Unexpected error during transcription")
        raise RuntimeError(f"Failed to transcribe audio recording: {str(exc)}")
    finally:
        # Best-effort cleanup of remote Gemini file resource
        if uploaded_file and hasattr(uploaded_file, "name"):
            try:
                logger.info("Cleaning up Gemini remote file: %s", uploaded_file.name)
                client.files.delete(name=uploaded_file.name)
            except Exception as cleanup_err:
                logger.warning("Failed to delete remote file %s: %s", uploaded_file.name, cleanup_err)
