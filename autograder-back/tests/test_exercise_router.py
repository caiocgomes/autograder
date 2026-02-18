"""Tests for exercise and submission endpoints (Task 16.3)"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from app.models.user import User, UserRole
from app.models.exercise import Exercise, TestCase, ExerciseList, ExerciseListItem, SubmissionType, GradingMode


def _add_exercise_defaults(mock_exercise):
    """Add default values for new exercise fields to a mock."""
    mock_exercise.submission_type = SubmissionType.CODE
    mock_exercise.grading_mode = GradingMode.TEST_FIRST
    mock_exercise.rubric_dimensions = []


class TestCreateExercise:
    def test_create_exercise(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_db.refresh = Mock(side_effect=lambda e: (
            setattr(e, 'id', 1),
            setattr(e, 'created_by', professor.id),
        ))

        response = client.post("/exercises", json={
            "title": "Add Two Numbers",
            "description": "Write a function that adds two numbers",
            "has_tests": True,
            "llm_grading_enabled": False,
            "test_weight": 1.0,
            "llm_weight": 0.0,
        })
        assert response.status_code == 201
        mock_db.add.assert_called_once()

    def test_create_exercise_as_student_forbidden(self, client_with_student):
        client, mock_db, student = client_with_student
        response = client.post("/exercises", json={
            "title": "Test",
            "description": "Test",
            "has_tests": True,
            "llm_grading_enabled": False,
            "test_weight": 1.0,
            "llm_weight": 0.0,
        })
        assert response.status_code == 403

    def test_create_exercise_invalid_weights(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        response = client.post("/exercises", json={
            "title": "Test",
            "description": "Test",
            "has_tests": True,
            "llm_grading_enabled": True,
            "test_weight": 0.5,
            "llm_weight": 0.3,  # doesn't sum to 1.0
        })
        assert response.status_code == 422


class TestListExercises:
    def test_list_exercises(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_exercise = Mock(spec=Exercise)
        mock_exercise.id = 1
        mock_exercise.title = "Test Exercise"
        mock_exercise.description = "Description"
        mock_exercise.template_code = None
        mock_exercise.language = "python"
        mock_exercise.max_submissions = None
        mock_exercise.timeout_seconds = 30
        mock_exercise.memory_limit_mb = 512
        mock_exercise.has_tests = True
        mock_exercise.llm_grading_enabled = False
        mock_exercise.test_weight = 1.0
        mock_exercise.llm_weight = 0.0
        mock_exercise.llm_grading_criteria = None
        mock_exercise.created_by = professor.id
        mock_exercise.published = True
        mock_exercise.tags = "test"
        mock_exercise.test_cases = []
        _add_exercise_defaults(mock_exercise)

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_exercise]

        response = client.get("/exercises")
        assert response.status_code == 200


class TestGetExercise:
    def test_get_exercise(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_exercise = Mock(spec=Exercise)
        mock_exercise.id = 1
        mock_exercise.title = "Test"
        mock_exercise.description = "Desc"
        mock_exercise.template_code = None
        mock_exercise.language = "python"
        mock_exercise.max_submissions = None
        mock_exercise.timeout_seconds = 30
        mock_exercise.memory_limit_mb = 512
        mock_exercise.has_tests = True
        mock_exercise.llm_grading_enabled = False
        mock_exercise.test_weight = 1.0
        mock_exercise.llm_weight = 0.0
        mock_exercise.llm_grading_criteria = None
        mock_exercise.created_by = professor.id
        mock_exercise.published = True
        mock_exercise.tags = None
        mock_exercise.test_cases = []
        _add_exercise_defaults(mock_exercise)

        mock_db.query.return_value.filter.return_value.first.return_value = mock_exercise

        response = client.get("/exercises/1")
        assert response.status_code == 200

    def test_get_nonexistent_exercise(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/exercises/999")
        assert response.status_code == 404


class TestAddTestCase:
    def test_add_test_case(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_exercise = Mock(spec=Exercise)
        mock_exercise.id = 1
        mock_exercise.created_by = professor.id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_exercise
        mock_db.refresh = Mock(side_effect=lambda tc: setattr(tc, 'id', 1))

        response = client.post("/exercises/1/tests", json={
            "name": "test_add",
            "input_data": "add(1, 2)",
            "expected_output": "3",
            "hidden": False,
        })
        assert response.status_code == 201


class TestPublishExercise:
    def test_toggle_publish(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_exercise = Mock(spec=Exercise)
        mock_exercise.id = 1
        mock_exercise.title = "Test"
        mock_exercise.description = "Desc"
        mock_exercise.template_code = None
        mock_exercise.language = "python"
        mock_exercise.max_submissions = None
        mock_exercise.timeout_seconds = 30
        mock_exercise.memory_limit_mb = 512
        mock_exercise.has_tests = True
        mock_exercise.llm_grading_enabled = False
        mock_exercise.test_weight = 1.0
        mock_exercise.llm_weight = 0.0
        mock_exercise.llm_grading_criteria = None
        mock_exercise.created_by = professor.id
        mock_exercise.published = False
        mock_exercise.tags = None
        mock_exercise.test_cases = []
        _add_exercise_defaults(mock_exercise)

        mock_db.query.return_value.filter.return_value.first.return_value = mock_exercise

        response = client.patch("/exercises/1/publish?published=true")
        assert response.status_code == 200
