import pytest
from unittest.mock import Mock, patch

from services.llm_validator import LLMValidator, ValidationResult


class TestValidationResult:
    def test_validation_result_creation(self):
        result = ValidationResult(valid=True, feedback="Good code")
        assert result.valid is True
        assert result.feedback == "Good code"

    def test_validation_result_invalid(self):
        result = ValidationResult(valid=False, feedback="Syntax error")
        assert result.valid is False
        assert result.feedback == "Syntax error"


class TestLLMValidator:
    @patch("services.llm_validator.Anthropic")
    def test_validate_valid_code(self, mock_anthropic_class, sample_code, sample_requirements):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="VALID: true\nFEEDBACK: Code correctly implements addition")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        validator = LLMValidator(api_key="test-key")
        result = validator.validate(sample_code, sample_requirements)

        assert result.valid is True
        assert "addition" in result.feedback.lower()
        mock_client.messages.create.assert_called_once()

    @patch("services.llm_validator.Anthropic")
    def test_validate_invalid_code(self, mock_anthropic_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="VALID: false\nFEEDBACK: Function subtracts instead of adds")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        validator = LLMValidator(api_key="test-key")
        result = validator.validate("def add(a, b): return a - b", "Add two numbers")

        assert result.valid is False
        assert "subtract" in result.feedback.lower()

    @patch("services.llm_validator.Anthropic")
    def test_validate_unparseable_response(self, mock_anthropic_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Some unexpected response format")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        validator = LLMValidator(api_key="test-key")
        result = validator.validate("def foo(): pass", "Do something")

        assert result.valid is False
        assert "unable to parse" in result.feedback.lower()

    @patch("services.llm_validator.Anthropic")
    def test_validate_uses_correct_model(self, mock_anthropic_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="VALID: true\nFEEDBACK: OK")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        validator = LLMValidator(api_key="test-key")
        validator.validate("def foo(): pass", "Do something")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_kwargs["max_tokens"] == 256
