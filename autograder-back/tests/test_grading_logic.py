"""Tests for grading logic (Task 16.5)"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestTestScoreCalculation:
    """Test score = passed / total * 100"""

    def test_all_passed(self):
        from app.services.grading import calculate_test_score
        results = [
            {"passed": True},
            {"passed": True},
            {"passed": True},
        ]
        assert calculate_test_score(results) == 100.0

    def test_none_passed(self):
        from app.services.grading import calculate_test_score
        results = [
            {"passed": False},
            {"passed": False},
        ]
        assert calculate_test_score(results) == 0.0

    def test_partial(self):
        from app.services.grading import calculate_test_score
        results = [
            {"passed": True},
            {"passed": False},
            {"passed": True},
            {"passed": False},
        ]
        assert calculate_test_score(results) == 50.0

    def test_empty_results(self):
        from app.services.grading import calculate_test_score
        assert calculate_test_score([]) == 0.0


class TestCompositeScore:
    """Composite = test_weight * test_score + llm_weight * llm_score"""

    def test_tests_only(self):
        from app.services.grading import calculate_composite_score
        score = calculate_composite_score(
            test_score=80.0,
            llm_score=None,
            test_weight=1.0,
            llm_weight=0.0,
        )
        assert score == 80.0

    def test_mixed_weights(self):
        from app.services.grading import calculate_composite_score
        score = calculate_composite_score(
            test_score=80.0,
            llm_score=90.0,
            test_weight=0.7,
            llm_weight=0.3,
        )
        assert abs(score - 83.0) < 0.01

    def test_llm_only(self):
        from app.services.grading import calculate_composite_score
        score = calculate_composite_score(
            test_score=None,
            llm_score=75.0,
            test_weight=0.0,
            llm_weight=1.0,
        )
        assert score == 75.0

    def test_with_late_penalty(self):
        from app.services.grading import calculate_composite_score
        score = calculate_composite_score(
            test_score=100.0,
            llm_score=100.0,
            test_weight=0.5,
            llm_weight=0.5,
            late_penalty=10.0,
        )
        assert score == 90.0

    def test_penalty_cant_go_below_zero(self):
        from app.services.grading import calculate_composite_score
        score = calculate_composite_score(
            test_score=20.0,
            llm_score=None,
            test_weight=1.0,
            llm_weight=0.0,
            late_penalty=50.0,
        )
        assert score == 0.0
