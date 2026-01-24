import pytest
from unittest.mock import patch, Mock

from services.llm_validator import ValidationResult
from services.sandbox import ExecutionResult
from services.grader import GradeResult, TestResult


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestGradeEndpoint:
    @patch("main.Grader")
    def test_grade_success(self, mock_grader_class, client, sample_code, sample_requirements, sample_test_cases):
        mock_grader = Mock()
        mock_grader.grade.return_value = GradeResult(
            passed=True,
            score=100.0,
            llm_validation=ValidationResult(valid=True, feedback="Good code"),
            test_results=[
                TestResult(input="add(1, 2)", expected="3", actual="3", passed=True),
                TestResult(input="add(-1, 1)", expected="0", actual="0", passed=True),
            ],
        )
        mock_grader_class.return_value = mock_grader

        response = client.post(
            "/grade",
            json={
                "code": sample_code,
                "requirements": sample_requirements,
                "test_cases": sample_test_cases,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is True
        assert data["score"] == 100.0
        assert data["llm_validation"]["valid"] is True
        assert len(data["test_results"]) == 2

    @patch("main.Grader")
    def test_grade_failure(self, mock_grader_class, client, sample_code, sample_requirements, sample_test_cases):
        mock_grader = Mock()
        mock_grader.grade.return_value = GradeResult(
            passed=False,
            score=0.0,
            llm_validation=ValidationResult(valid=False, feedback="Code has errors"),
            test_results=[
                TestResult(input="add(1, 2)", expected="3", actual="", passed=False, error="Validation failed"),
            ],
        )
        mock_grader_class.return_value = mock_grader

        response = client.post(
            "/grade",
            json={
                "code": "def add(a, b): return a - b",
                "requirements": sample_requirements,
                "test_cases": [{"input": "add(1, 2)", "expected": "3"}],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is False
        assert data["score"] == 0.0
        assert data["llm_validation"]["valid"] is False

    def test_grade_invalid_request_missing_code(self, client):
        response = client.post(
            "/grade",
            json={
                "requirements": "Add numbers",
                "test_cases": [{"input": "add(1, 2)", "expected": "3"}],
            },
        )
        assert response.status_code == 422

    def test_grade_invalid_request_missing_test_cases(self, client):
        response = client.post(
            "/grade",
            json={
                "code": "def add(a, b): return a + b",
                "requirements": "Add numbers",
            },
        )
        assert response.status_code == 422

    def test_grade_invalid_request_bad_test_case_format(self, client):
        response = client.post(
            "/grade",
            json={
                "code": "def add(a, b): return a + b",
                "requirements": "Add numbers",
                "test_cases": [{"input": "add(1, 2)"}],  # Missing expected
            },
        )
        assert response.status_code == 422

    @patch("main.Grader")
    def test_grade_internal_error(self, mock_grader_class, client, sample_code, sample_requirements, sample_test_cases):
        mock_grader = Mock()
        mock_grader.grade.side_effect = Exception("Something went wrong")
        mock_grader_class.return_value = mock_grader

        response = client.post(
            "/grade",
            json={
                "code": sample_code,
                "requirements": sample_requirements,
                "test_cases": sample_test_cases,
            },
        )

        assert response.status_code == 500
        assert "Something went wrong" in response.json()["detail"]

    @patch("main.Grader")
    def test_grade_partial_success(self, mock_grader_class, client, sample_code, sample_requirements):
        mock_grader = Mock()
        mock_grader.grade.return_value = GradeResult(
            passed=False,
            score=50.0,
            llm_validation=ValidationResult(valid=True, feedback="OK"),
            test_results=[
                TestResult(input="add(1, 2)", expected="3", actual="3", passed=True),
                TestResult(input="add(5, 5)", expected="10", actual="9", passed=False),
            ],
        )
        mock_grader_class.return_value = mock_grader

        response = client.post(
            "/grade",
            json={
                "code": sample_code,
                "requirements": sample_requirements,
                "test_cases": [
                    {"input": "add(1, 2)", "expected": "3"},
                    {"input": "add(5, 5)", "expected": "10"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is False
        assert data["score"] == 50.0
        assert data["test_results"][0]["passed"] is True
        assert data["test_results"][1]["passed"] is False
