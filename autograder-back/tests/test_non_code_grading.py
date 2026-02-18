"""Router and integration tests for non-code grading features."""
import pytest
import io
from unittest.mock import Mock, MagicMock, patch

from fastapi.testclient import TestClient
from main import app
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.exercise import Exercise, SubmissionType, GradingMode, RubricDimension
from app.models.submission import Submission, SubmissionStatus, RubricScore


# --- Fixtures ---

@pytest.fixture
def mock_db():
    """Mock database session that handles chained queries properly."""
    db = MagicMock()

    # Make chained query calls return queryable mocks
    # db.query(Model).join(...).filter(...).first() etc.
    query_mock = MagicMock()
    query_mock.join.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.first.return_value = None
    query_mock.all.return_value = []
    query_mock.count.return_value = 0

    db.query.return_value = query_mock
    db._query_mock = query_mock  # expose for per-test customization
    return db


@pytest.fixture
def mock_professor():
    user = Mock(spec=User)
    user.id = 1
    user.email = "professor@test.com"
    user.role = UserRole.PROFESSOR
    return user


@pytest.fixture
def mock_student():
    user = Mock(spec=User)
    user.id = 2
    user.email = "student@test.com"
    user.role = UserRole.STUDENT
    return user


@pytest.fixture
def professor_client(mock_db, mock_professor):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_professor
    client = TestClient(app)
    yield client, mock_db, mock_professor
    app.dependency_overrides.clear()


@pytest.fixture
def student_client(mock_db, mock_student):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_student
    client = TestClient(app)
    yield client, mock_db, mock_student
    app.dependency_overrides.clear()


def make_exercise_obj(**overrides):
    """Create a mock Exercise with all attributes needed by ExerciseResponse."""
    ex = Mock(spec=Exercise)
    ex.id = overrides.get("id", 1)
    ex.title = overrides.get("title", "Test Exercise")
    ex.description = overrides.get("description", "Description")
    ex.template_code = overrides.get("template_code", None)
    ex.language = overrides.get("language", "python")
    ex.submission_type = overrides.get("submission_type", SubmissionType.CODE)
    ex.grading_mode = overrides.get("grading_mode", GradingMode.TEST_FIRST)
    ex.max_submissions = overrides.get("max_submissions", None)
    ex.timeout_seconds = overrides.get("timeout_seconds", 30)
    ex.memory_limit_mb = overrides.get("memory_limit_mb", 512)
    ex.has_tests = overrides.get("has_tests", True)
    ex.llm_grading_enabled = overrides.get("llm_grading_enabled", False)
    ex.test_weight = overrides.get("test_weight", 0.7)
    ex.llm_weight = overrides.get("llm_weight", 0.3)
    ex.llm_grading_criteria = overrides.get("llm_grading_criteria", None)
    ex.created_by = overrides.get("created_by", 1)
    ex.published = overrides.get("published", True)
    ex.tags = overrides.get("tags", None)
    ex.rubric_dimensions = overrides.get("rubric_dimensions", [])
    ex.test_cases = overrides.get("test_cases", None)
    return ex


# --- Exercise Creation Tests ---

class TestExerciseCreationWithNewFields:
    def test_create_llm_first_exercise_with_rubric(self, professor_client):
        """Create exercise with grading_mode=llm_first and rubric dimensions."""
        client, mock_db, _ = professor_client

        created = make_exercise_obj(
            submission_type=SubmissionType.FILE_UPLOAD,
            grading_mode=GradingMode.LLM_FIRST,
        )

        with patch("app.routers.exercises.Exercise", return_value=created):
            with patch("app.routers.exercises.RubricDimension") as MockDim:
                response = client.post("/exercises", json={
                    "title": "ML Analysis",
                    "description": "Analyze the dataset",
                    "submission_type": "file_upload",
                    "grading_mode": "llm_first",
                    "rubric_dimensions": [
                        {"name": "Methodology", "description": "Approach", "weight": 0.5, "position": 1},
                        {"name": "Clarity", "description": "Presentation", "weight": 0.5, "position": 2},
                    ],
                })

        assert response.status_code == 201

    def test_create_llm_first_without_rubric_fails(self, professor_client):
        """LLM-first exercise without rubric dimensions should fail validation."""
        client, mock_db, _ = professor_client

        response = client.post("/exercises", json={
            "title": "Missing Rubric",
            "description": "No rubric",
            "submission_type": "file_upload",
            "grading_mode": "llm_first",
            "rubric_dimensions": [],
        })

        assert response.status_code == 422  # Pydantic validation error

    def test_rubric_weights_must_sum_to_one(self, professor_client):
        """Rubric dimension weights must sum to 1.0 for llm_first."""
        client, mock_db, _ = professor_client

        response = client.post("/exercises", json={
            "title": "Bad Weights",
            "description": "Weights don't add up",
            "submission_type": "file_upload",
            "grading_mode": "llm_first",
            "rubric_dimensions": [
                {"name": "A", "weight": 0.3, "position": 1},
                {"name": "B", "weight": 0.3, "position": 2},
            ],
        })

        assert response.status_code == 422


# --- Submission Tests ---

class TestFileUploadSubmission:
    def _setup_exercise_query(self, mock_db, exercise):
        """Configure mock_db so query(Exercise).filter().first() returns exercise."""
        def query_side_effect(model):
            q = MagicMock()
            q.join.return_value = q
            q.filter.return_value = q
            q.first.return_value = None
            q.all.return_value = []
            q.count.return_value = 0

            if model is Exercise:
                q.filter.return_value.first.return_value = exercise
            return q

        mock_db.query.side_effect = query_side_effect

    def test_file_upload_valid_pdf(self, student_client):
        """Submit a PDF to a file_upload exercise."""
        client, mock_db, student = student_client

        exercise = make_exercise_obj(
            submission_type=SubmissionType.FILE_UPLOAD,
            grading_mode=GradingMode.LLM_FIRST,
        )
        self._setup_exercise_query(mock_db, exercise)

        submission = Mock(spec=Submission)
        submission.id = 1
        submission.exercise_id = 1
        submission.student_id = 2
        submission.code = None
        submission.content_hash = "abc123"
        submission.file_name = "report.pdf"
        submission.file_size = 1024
        submission.content_type = "application/pdf"
        submission.file_path = "1/1/report.pdf"
        submission.status = SubmissionStatus.QUEUED
        submission.submitted_at = "2024-01-01T00:00:00"
        submission.error_message = None

        with patch("app.routers.submissions.Submission", return_value=submission):
            with patch("app.services.file_storage.save_submission_file", return_value=("1/1/report.pdf", "abc123")):
                with patch("app.routers.submissions.celery_app"):
                    pdf_content = b"%PDF-1.4 fake pdf content"
                    response = client.post(
                        "/submissions",
                        data={"exercise_id": "1"},
                        files={"file": ("report.pdf", io.BytesIO(pdf_content), "application/pdf")},
                    )

        assert response.status_code == 201

    def test_reject_invalid_extension(self, student_client):
        """Reject files with non-allowed extensions."""
        client, mock_db, student = student_client

        exercise = make_exercise_obj(
            submission_type=SubmissionType.FILE_UPLOAD,
            grading_mode=GradingMode.LLM_FIRST,
        )
        self._setup_exercise_query(mock_db, exercise)

        response = client.post(
            "/submissions",
            data={"exercise_id": "1"},
            files={"file": ("script.sh", io.BytesIO(b"#!/bin/bash"), "application/x-sh")},
        )

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    def test_reject_code_to_file_exercise(self, student_client):
        """Reject text code submission to a file_upload exercise."""
        client, mock_db, student = student_client

        exercise = make_exercise_obj(
            submission_type=SubmissionType.FILE_UPLOAD,
            grading_mode=GradingMode.LLM_FIRST,
        )
        self._setup_exercise_query(mock_db, exercise)

        response = client.post(
            "/submissions",
            data={"exercise_id": "1", "code": "print('hello')"},
        )

        assert response.status_code == 400
        assert "file upload" in response.json()["detail"].lower()

    def test_reject_non_py_file_to_code_exercise(self, student_client):
        """Reject non-.py file upload to a code exercise."""
        client, mock_db, student = student_client

        exercise = make_exercise_obj(
            submission_type=SubmissionType.CODE,
            grading_mode=GradingMode.TEST_FIRST,
        )
        self._setup_exercise_query(mock_db, exercise)

        response = client.post(
            "/submissions",
            data={"exercise_id": "1"},
            files={"file": ("report.pdf", io.BytesIO(b"fake"), "application/pdf")},
        )

        assert response.status_code == 400


class TestSubmissionResultsWithRubric:
    def test_results_include_rubric_scores(self, student_client):
        """GET /submissions/{id}/results returns rubric_scores for llm_first."""
        client, mock_db, student = student_client

        exercise = make_exercise_obj(
            grading_mode=GradingMode.LLM_FIRST,
        )

        submission = Mock(spec=Submission)
        submission.id = 1
        submission.exercise_id = 1
        submission.student_id = 2
        submission.code = None
        submission.file_name = "report.pdf"
        submission.file_size = 2048
        submission.content_type = "application/pdf"
        submission.status = SubmissionStatus.COMPLETED
        submission.submitted_at = "2024-01-01T00:00:00"
        submission.error_message = None
        submission.test_results = []
        submission.llm_evaluation = Mock(feedback="Good work", score=85, cached=False, created_at="2024-01-01", id=1)
        submission.grade = Mock(id=1, test_score=None, llm_score=85, final_score=85, late_penalty_applied=0, published=True)

        dim = Mock(spec=RubricDimension)
        dim.name = "Analysis"
        dim.weight = 1.0

        rs = Mock(spec=RubricScore)
        rs.score = 85
        rs.feedback = "Thorough analysis"
        rs.dimension = dim

        def mock_query_side_effect(model):
            q = MagicMock()
            q.join.return_value = q
            q.filter.return_value = q
            q.first.return_value = None
            q.all.return_value = []
            q.count.return_value = 0

            if model == Submission:
                q.filter.return_value.first.return_value = submission
            elif model == Exercise:
                q.filter.return_value.first.return_value = exercise
            elif model == RubricScore:
                q.filter.return_value.all.return_value = [rs]
            return q

        mock_db.query.side_effect = mock_query_side_effect

        response = client.get("/submissions/1/results")

        assert response.status_code == 200
        data = response.json()
        assert data["rubric_scores"] is not None
        assert len(data["rubric_scores"]) == 1
        assert data["rubric_scores"][0]["dimension_name"] == "Analysis"
        assert data["rubric_scores"][0]["score"] == 85
        assert data["overall_feedback"] == "Good work"
