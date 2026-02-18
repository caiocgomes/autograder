import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.services.content_extractor import extract_content, _truncate, MAX_CONTENT_LENGTH


class TestExtractContent:
    def test_pdf_extraction(self, tmp_path):
        """Test PDF text extraction using pdfplumber."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"dummy")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 content"
        mock_page.extract_tables.return_value = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = lambda s: mock_pdf
        mock_pdf.__exit__ = MagicMock(return_value=False)

        mock_plumber = MagicMock()
        mock_plumber.open.return_value = mock_pdf

        # pdfplumber is imported locally inside _extract_pdf, so patch the import itself
        with patch.dict("sys.modules", {"pdfplumber": mock_plumber}):
            result = extract_content(str(pdf_path), "application/pdf")

        assert "Page 1 content" in result

    def test_pdf_with_tables(self, tmp_path):
        """Test PDF extraction preserves table structure."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"dummy")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Some text"
        mock_page.extract_tables.return_value = [
            [["Header1", "Header2"], ["val1", "val2"]]
        ]

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = lambda s: mock_pdf
        mock_pdf.__exit__ = MagicMock(return_value=False)

        mock_plumber = MagicMock()
        mock_plumber.open.return_value = mock_pdf

        with patch.dict("sys.modules", {"pdfplumber": mock_plumber}):
            result = extract_content(str(pdf_path), "application/pdf")

        assert "Header1" in result
        assert "val1" in result

    def test_xlsx_extraction(self, tmp_path):
        """Test XLSX extraction serializes sheets as markdown tables."""
        xlsx_path = tmp_path / "test.xlsx"
        xlsx_path.write_bytes(b"dummy")

        mock_ws = MagicMock()
        mock_ws.title = "Sheet1"
        mock_ws.iter_rows.return_value = [
            ("A", "B"),
            (1, 2),
        ]

        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1"]
        mock_wb.__getitem__ = lambda s, k: mock_ws

        # openpyxl.load_workbook is imported locally inside _extract_xlsx
        mock_openpyxl = MagicMock()
        mock_openpyxl.load_workbook.return_value = mock_wb

        with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
            result = extract_content(
                str(xlsx_path),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        assert "Sheet1" in result
        assert "A" in result

    def test_image_raises_for_extraction(self, tmp_path):
        """Test that image content types raise ValueError."""
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"dummy")

        with pytest.raises(ValueError, match="image"):
            extract_content(str(img_path), "image/png")

    def test_unsupported_content_type(self, tmp_path):
        """Test unsupported content type raises."""
        path = tmp_path / "test.xyz"
        path.write_bytes(b"dummy")

        with pytest.raises(ValueError):
            extract_content(str(path), "application/octet-stream")


class TestTruncation:
    def test_no_truncation_under_limit(self):
        text = "Short text"
        result = _truncate(text)
        assert result == text

    def test_truncation_at_limit(self):
        text = "x" * (MAX_CONTENT_LENGTH + 10000)
        result = _truncate(text)
        assert "[TRUNCATED]" in result.upper() or "[Content truncated" in result
        assert len(result) < len(text)

    def test_truncation_preserves_beginning(self):
        text = "BEGINNING" + "x" * (MAX_CONTENT_LENGTH + 10000)
        result = _truncate(text)
        assert result.startswith("BEGINNING")
