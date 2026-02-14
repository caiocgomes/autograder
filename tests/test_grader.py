import pytest
from unittest.mock import Mock, patch, MagicMock

from services.grader import Grader, GradeResult, TestResult
from services.llm_validator import ValidationResult
from services.sandbox import ExecutionResult


class TestTestResult:
    def test_test_result_passed(self):
        result = TestResult(input="add(1,2)", expected="3", actual="3", passed=True)
        assert result.passed is True
        assert result.error is None

    def test_test_result_failed(self):
        result = TestResult(input="add(1,2)", expected="3", actual="5", passed=False)
        assert result.passed is False

    def test_test_result_with_error(self):
        result = TestResult(input="add(1,2)", expected="3", actual="", passed=False, error="Runtime error")
        assert result.error == "Runtime error"


class TestGradeResult:
    def test_grade_result_all_passed(self):
        validation = ValidationResult(valid=True, feedback="OK")
        test_results = [
            TestResult(input="add(1,2)", expected="3", actual="3", passed=True),
        ]
        result = GradeResult(passed=True, score=100.0, llm_validation=validation, test_results=test_results)
        assert result.passed is True
        assert result.score == 100.0


class TestGrader:
    @patch("services.grader.Sandbox")
    @patch("services.grader.LLMValidator")
    def test_grade_all_tests_pass(self, mock_validator_class, mock_sandbox_class, sample_code, sample_requirements, sample_test_cases):
        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationResult(valid=True, feedback="Good")
        mock_validator_class.return_value = mock_validator

        mock_sandbox = Mock()
        mock_sandbox.execute.side_effect = [
            ExecutionResult(output="3", error=None, timed_out=False, exit_code=0),
            ExecutionResult(output="0", error=None, timed_out=False, exit_code=0),
        ]
        mock_sandbox_class.return_value = mock_sandbox

        grader = Grader(api_key="test-key")
        result = grader.grade(sample_code, sample_requirements, sample_test_cases)

        assert result.passed is True
        assert result.score == 100.0
        assert len(result.test_results) == 2
        assert all(tr.passed for tr in result.test_results)

    @patch("services.grader.Sandbox")
    @patch("services.grader.LLMValidator")
    def test_grade_validation_fails(self, mock_validator_class, mock_sandbox_class, sample_code, sample_requirements, sample_test_cases):
        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationResult(valid=False, feedback="Code has bugs")
        mock_validator_class.return_value = mock_validator

        mock_sandbox = Mock()
        mock_sandbox_class.return_value = mock_sandbox

        grader = Grader(api_key="test-key")
        result = grader.grade(sample_code, sample_requirements, sample_test_cases)

        assert result.passed is False
        assert result.score == 0.0
        assert all(tr.error == "Code validation failed" for tr in result.test_results)
        mock_sandbox.execute.assert_not_called()

    @patch("services.grader.Sandbox")
    @patch("services.grader.LLMValidator")
    def test_grade_some_tests_fail(self, mock_validator_class, mock_sandbox_class, sample_code, sample_requirements, sample_test_cases):
        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationResult(valid=True, feedback="OK")
        mock_validator_class.return_value = mock_validator

        mock_sandbox = Mock()
        mock_sandbox.execute.side_effect = [
            ExecutionResult(output="3", error=None, timed_out=False, exit_code=0),
            ExecutionResult(output="2", error=None, timed_out=False, exit_code=0),  # Wrong output
        ]
        mock_sandbox_class.return_value = mock_sandbox

        grader = Grader(api_key="test-key")
        result = grader.grade(sample_code, sample_requirements, sample_test_cases)

        assert result.passed is False
        assert result.score == 50.0
        assert result.test_results[0].passed is True
        assert result.test_results[1].passed is False

    @patch("services.grader.Sandbox")
    @patch("services.grader.LLMValidator")
    def test_grade_execution_error(self, mock_validator_class, mock_sandbox_class, sample_code, sample_requirements):
        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationResult(valid=True, feedback="OK")
        mock_validator_class.return_value = mock_validator

        mock_sandbox = Mock()
        mock_sandbox.execute.return_value = ExecutionResult(
            output="", error="NameError: undefined", timed_out=False, exit_code=1
        )
        mock_sandbox_class.return_value = mock_sandbox

        grader = Grader(api_key="test-key")
        result = grader.grade(sample_code, sample_requirements, [{"input": "foo()", "expected": "1"}])

        assert result.passed is False
        assert result.test_results[0].error == "NameError: undefined"

    @patch("services.grader.Sandbox")
    @patch("services.grader.LLMValidator")
    def test_grade_empty_test_cases(self, mock_validator_class, mock_sandbox_class, sample_code, sample_requirements):
        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationResult(valid=True, feedback="OK")
        mock_validator_class.return_value = mock_validator

        mock_sandbox = Mock()
        mock_sandbox_class.return_value = mock_sandbox

        grader = Grader(api_key="test-key")
        result = grader.grade(sample_code, sample_requirements, [])

        assert result.passed is True
        assert result.score == 0.0
        assert len(result.test_results) == 0
