"""Integration tests for the grade_llm_first Celery task."""
import json
import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock

from app.models.submission import Submission, SubmissionStatus, RubricScore
from app.models.submission import LLMEvaluation
from app.models.exercise import Exercise, RubricDimension, GradingMode
from app.models.submission import Grade


def _mock_dim(id, name, weight, exercise_id=1, position=1, description=None):
    d = Mock(spec=RubricDimension)
    d.id = id
    d.name = name
    d.weight = weight
    d.exercise_id = exercise_id
    d.position = position
    d.description = description
    return d


def _make_llm_response(dimensions, overall_feedback="Good"):
    return json.dumps({
        "dimensions": dimensions,
        "overall_feedback": overall_feedback,
    })


class TestGradeLLMFirst:
    def _setup_db(self, submission, exercise, rubric_dims, cached_eval=None, cached_scores=None):
        """Create a mock DB session with side_effect-based query routing."""
        db = MagicMock()

        def query_side_effect(model):
            q = MagicMock()
            q.join.return_value = q
            q.filter.return_value = q
            q.order_by.return_value = q
            q.first.return_value = None
            q.all.return_value = []

            if model is Submission:
                q.filter.return_value.first.return_value = submission
            elif model is Exercise:
                q.filter.return_value.first.return_value = exercise
            elif model is RubricDimension:
                q.filter.return_value.order_by.return_value.all.return_value = rubric_dims
            elif model is LLMEvaluation:
                q.join.return_value.filter.return_value.first.return_value = cached_eval
            elif model is RubricScore:
                q.filter.return_value.all.return_value = cached_scores or []
            return q

        db.query.side_effect = query_side_effect
        return db

    @patch("app.tasks._call_llm")
    @patch("app.tasks.SessionLocal")
    def test_successful_grading(self, MockSessionLocal, mock_call_llm):
        """Full pipeline: mock LLM returns valid rubric, verify scores persisted."""
        submission = Mock(spec=Submission)
        submission.id = 1
        submission.exercise_id = 1
        submission.content_hash = "abc123"
        submission.file_path = None
        submission.content_type = None
        submission.code = "print('hello world')"
        submission.status = SubmissionStatus.QUEUED

        exercise = Mock(spec=Exercise)
        exercise.id = 1
        exercise.title = "Test Exercise"
        exercise.description = "Test description"
        exercise.grading_mode = GradingMode.LLM_FIRST
        exercise.llm_grading_criteria = None

        dims = [
            _mock_dim(10, "Methodology", 0.6),
            _mock_dim(11, "Clarity", 0.4),
        ]

        db = self._setup_db(submission, exercise, dims)
        MockSessionLocal.return_value = db

        mock_call_llm.return_value = _make_llm_response([
            {"name": "Methodology", "score": 80, "feedback": "Good approach"},
            {"name": "Clarity", "score": 90, "feedback": "Very clear"},
        ], "Solid work overall")

        from app.tasks import grade_llm_first
        result = grade_llm_first(1, late_penalty=0.0)

        assert result["cached"] is False
        expected_score = 0.6 * 80 + 0.4 * 90  # 84.0
        assert result["final_score"] == expected_score
        assert result["dimensions"] == 2

        # Verify RubricScore records were added
        add_calls = db.add.call_args_list
        rubric_score_adds = [c for c in add_calls if hasattr(c[0][0], 'dimension_id') or isinstance(c[0][0], RubricScore)]
        assert len(rubric_score_adds) >= 2

    @patch("app.tasks._call_llm")
    @patch("app.tasks.SessionLocal")
    def test_cache_hit_on_duplicate_hash(self, MockSessionLocal, mock_call_llm):
        """When content_hash matches an existing evaluation, reuse cached scores."""
        submission = Mock(spec=Submission)
        submission.id = 2
        submission.exercise_id = 1
        submission.content_hash = "same_hash"
        submission.file_path = None
        submission.content_type = None
        submission.code = "same code"
        submission.status = SubmissionStatus.QUEUED

        exercise = Mock(spec=Exercise)
        exercise.id = 1
        exercise.title = "Test Exercise"
        exercise.description = "Test"
        exercise.grading_mode = GradingMode.LLM_FIRST

        dims = [_mock_dim(10, "Quality", 1.0)]

        # Set up cached evaluation
        cached_eval = Mock(spec=LLMEvaluation)
        cached_eval.submission_id = 1
        cached_eval.content_hash = "same_hash"
        cached_eval.feedback = "Cached feedback"
        cached_eval.score = 85.0

        cached_score = Mock(spec=RubricScore)
        cached_score.dimension_id = 10
        cached_score.score = 85.0
        cached_score.feedback = "Cached score feedback"

        db = self._setup_db(submission, exercise, dims, cached_eval=cached_eval, cached_scores=[cached_score])
        MockSessionLocal.return_value = db

        from app.tasks import grade_llm_first
        result = grade_llm_first(2, late_penalty=0.0)

        assert result["cached"] is True
        assert result["final_score"] == 85.0
        mock_call_llm.assert_not_called()

    @patch("app.tasks._call_llm")
    @patch("app.tasks.SessionLocal")
    def test_late_penalty_applied(self, MockSessionLocal, mock_call_llm):
        """Late penalty reduces final_score but not llm_score."""
        submission = Mock(spec=Submission)
        submission.id = 3
        submission.exercise_id = 1
        submission.content_hash = "hash3"
        submission.file_path = None
        submission.content_type = None
        submission.code = "code"
        submission.status = SubmissionStatus.QUEUED

        exercise = Mock(spec=Exercise)
        exercise.id = 1
        exercise.title = "Ex"
        exercise.description = "Desc"
        exercise.grading_mode = GradingMode.LLM_FIRST
        exercise.llm_grading_criteria = None

        dims = [_mock_dim(10, "All", 1.0)]

        db = self._setup_db(submission, exercise, dims)
        MockSessionLocal.return_value = db

        mock_call_llm.return_value = _make_llm_response([
            {"name": "All", "score": 90, "feedback": "Good"},
        ])

        from app.tasks import grade_llm_first
        result = grade_llm_first(3, late_penalty=10.0)

        assert result["final_score"] == 80.0  # 90 - 10

    @patch("app.tasks._call_llm")
    @patch("app.tasks.SessionLocal")
    def test_malformed_response_retry(self, MockSessionLocal, mock_call_llm):
        """First LLM call returns bad JSON, retry succeeds."""
        submission = Mock(spec=Submission)
        submission.id = 4
        submission.exercise_id = 1
        submission.content_hash = "hash4"
        submission.file_path = None
        submission.content_type = None
        submission.code = "code"
        submission.status = SubmissionStatus.QUEUED

        exercise = Mock(spec=Exercise)
        exercise.id = 1
        exercise.title = "Ex"
        exercise.description = "Desc"
        exercise.grading_mode = GradingMode.LLM_FIRST
        exercise.llm_grading_criteria = None

        dims = [_mock_dim(10, "Quality", 1.0)]

        db = self._setup_db(submission, exercise, dims)
        MockSessionLocal.return_value = db

        good_response = _make_llm_response([
            {"name": "Quality", "score": 75, "feedback": "Decent"},
        ])

        mock_call_llm.side_effect = ["Not JSON at all", good_response]

        from app.tasks import grade_llm_first
        result = grade_llm_first(4, late_penalty=0.0)

        assert result["final_score"] == 75.0
        assert mock_call_llm.call_count == 2

    @patch("app.tasks._call_llm")
    @patch("app.tasks.SessionLocal")
    def test_submission_not_found(self, MockSessionLocal, mock_call_llm):
        """Missing submission returns error."""
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value.first.return_value = None
        db.query.return_value = q
        MockSessionLocal.return_value = db

        from app.tasks import grade_llm_first
        result = grade_llm_first(999, late_penalty=0.0)

        assert "error" in result
        mock_call_llm.assert_not_called()
