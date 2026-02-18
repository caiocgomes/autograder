import pytest
import json
from unittest.mock import Mock, MagicMock, patch

from app.tasks import create_rubric_prompt, parse_rubric_response


def _dim(name, description=None, weight=1.0):
    """Create a mock RubricDimension with .name attribute."""
    d = Mock()
    d.name = name
    d.description = description
    d.weight = weight
    return d


class TestParseRubricResponse:
    def test_valid_json_response(self):
        """Parse well-formed rubric JSON response."""
        response = json.dumps({
            "dimensions": [
                {"name": "Methodology", "score": 85, "feedback": "Good approach"},
                {"name": "Clarity", "score": 70, "feedback": "Could be clearer"},
            ],
            "overall_feedback": "Solid work overall"
        })
        expected_dims = [_dim("Methodology"), _dim("Clarity")]

        result = parse_rubric_response(response, expected_dims)

        assert result["dimensions"][0]["name"] == "Methodology"
        assert result["dimensions"][0]["score"] == 85
        assert result["dimensions"][1]["score"] == 70
        assert "overall_feedback" in result

    def test_malformed_json_raises(self):
        """Non-JSON response raises ValueError."""
        with pytest.raises((ValueError, json.JSONDecodeError)):
            parse_rubric_response("This is not JSON", [_dim("Dim1")])

    def test_missing_dimensions_raises(self):
        """Response missing expected dimensions raises ValueError."""
        response = json.dumps({
            "dimensions": [
                {"name": "Methodology", "score": 80, "feedback": "OK"},
            ],
            "overall_feedback": "OK"
        })
        with pytest.raises(ValueError):
            parse_rubric_response(response, [_dim("Methodology"), _dim("Clarity")])

    def test_score_clamping(self):
        """Scores outside 0-100 are clamped."""
        response = json.dumps({
            "dimensions": [
                {"name": "Quality", "score": 150, "feedback": "Perfect"},
                {"name": "Style", "score": -10, "feedback": "Needs work"},
            ],
            "overall_feedback": "Mixed"
        })
        result = parse_rubric_response(response, [_dim("Quality"), _dim("Style")])

        assert result["dimensions"][0]["score"] == 100  # Clamped down
        assert result["dimensions"][1]["score"] == 0    # Clamped up

    def test_json_with_markdown_wrapper(self):
        """Parse JSON wrapped in markdown code blocks."""
        inner = json.dumps({
            "dimensions": [
                {"name": "Analysis", "score": 90, "feedback": "Thorough"},
            ],
            "overall_feedback": "Great"
        })
        response = f"```json\n{inner}\n```"
        result = parse_rubric_response(response, [_dim("Analysis")])

        assert result["dimensions"][0]["score"] == 90


class TestCreateRubricPrompt:
    def test_text_prompt_includes_dimensions(self):
        """Verify prompt includes dimension names and weights."""
        exercise = Mock()
        exercise.title = "Analyze the dataset"
        exercise.description = "Analyze the dataset"
        exercise.llm_grading_criteria = "Focus on methodology"

        dims = [
            _dim("Methodology", "Evaluate the approach", 0.6),
            _dim("Presentation", "Evaluate clarity", 0.4),
        ]

        result = create_rubric_prompt(exercise, dims, "Student submission content")

        assert isinstance(result, str)
        assert "Methodology" in result
        assert "Presentation" in result
        assert "0.6" in result or "60" in result
        assert "Student submission content" in result

    def test_image_prompt_returns_list(self):
        """Image submissions return a list with text block for multimodal input."""
        exercise = Mock()
        exercise.title = "Analyze the chart"
        exercise.description = "Analyze the chart"
        exercise.llm_grading_criteria = None

        dims = [
            _dim("Accuracy", "Data reading", 1.0),
        ]

        result = create_rubric_prompt(exercise, dims, None, is_image=True)

        assert isinstance(result, list)
        # Should contain a text block (image is added by _call_llm, not here)
        has_text = any(isinstance(p, dict) and p.get("type") == "text" for p in result)
        assert has_text
        assert len(result) >= 1
