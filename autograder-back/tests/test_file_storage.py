import pytest
import hashlib
from unittest.mock import MagicMock, patch
from pathlib import Path

from app.services.file_storage import save_submission_file, get_absolute_path


class TestSaveSubmissionFile:
    def test_saves_file_to_correct_path(self, tmp_path):
        """Test file is saved under {exercise_id}/{submission_id}/{filename}."""
        upload = MagicMock()
        upload.filename = "report.pdf"
        file_content = b"PDF content here"

        with patch("app.services.file_storage.settings") as mock_settings:
            mock_settings.upload_base_dir = tmp_path

            relative_path, content_hash = save_submission_file(
                exercise_id=10,
                submission_id=42,
                upload_file=upload,
                file_content=file_content,
            )

        expected_path = tmp_path / "10" / "42" / "report.pdf"
        assert expected_path.exists()
        assert expected_path.read_bytes() == file_content
        assert relative_path == "10/42/report.pdf"

    def test_returns_correct_sha256_hash(self, tmp_path):
        """Test content hash matches SHA256 of file bytes."""
        upload = MagicMock()
        upload.filename = "data.xlsx"
        file_content = b"spreadsheet data"
        expected_hash = hashlib.sha256(file_content).hexdigest()

        with patch("app.services.file_storage.settings") as mock_settings:
            mock_settings.upload_base_dir = tmp_path

            _, content_hash = save_submission_file(
                exercise_id=1,
                submission_id=1,
                upload_file=upload,
                file_content=file_content,
            )

        assert content_hash == expected_hash

    def test_creates_directory_structure(self, tmp_path):
        """Test parent directories are created if they don't exist."""
        upload = MagicMock()
        upload.filename = "image.png"
        file_content = b"PNG data"

        with patch("app.services.file_storage.settings") as mock_settings:
            mock_settings.upload_base_dir = tmp_path

            save_submission_file(
                exercise_id=99,
                submission_id=7,
                upload_file=upload,
                file_content=file_content,
            )

        assert (tmp_path / "99" / "7").is_dir()


class TestGetAbsolutePath:
    def test_resolves_relative_path(self, tmp_path):
        """Test absolute path resolution."""
        with patch("app.services.file_storage.settings") as mock_settings:
            mock_settings.upload_base_dir = tmp_path

            result = get_absolute_path("10/42/report.pdf")

        assert result == tmp_path / "10" / "42" / "report.pdf"
