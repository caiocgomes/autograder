"""
File storage service for submission uploads.

Stores files on local disk under UPLOAD_BASE_DIR/{exercise_id}/{submission_id}/{filename}.
Returns relative path (for DB) and SHA256 content hash (for LLM cache).
"""
import hashlib
from pathlib import Path

from fastapi import UploadFile

from app.config import settings


def save_submission_file(
    exercise_id: int,
    submission_id: int,
    upload_file: UploadFile,
    file_content: bytes,
) -> tuple[str, str]:
    """
    Save uploaded file to disk and compute content hash.

    Args:
        exercise_id: Exercise ID for directory structure
        submission_id: Submission ID for directory structure
        upload_file: FastAPI UploadFile with filename metadata
        file_content: Raw bytes already read from the upload

    Returns:
        Tuple of (relative_path, content_hash)
    """
    base_dir = Path(settings.upload_base_dir)
    rel_dir = Path(str(exercise_id)) / str(submission_id)
    full_dir = base_dir / rel_dir
    full_dir.mkdir(parents=True, exist_ok=True)

    filename = upload_file.filename or f"submission_{submission_id}"
    file_path = full_dir / filename
    file_path.write_bytes(file_content)

    relative_path = str(rel_dir / filename)
    content_hash = hashlib.sha256(file_content).hexdigest()

    return relative_path, content_hash


def get_absolute_path(relative_path: str) -> Path:
    """Resolve a relative file path to absolute using UPLOAD_BASE_DIR."""
    return Path(settings.upload_base_dir) / relative_path
