"""Grading calculation utilities"""
from typing import Optional, List, Dict, Any


def calculate_test_score(results: List[Dict[str, Any]]) -> float:
    """Calculate test score as percentage of passed tests."""
    if not results:
        return 0.0
    passed = sum(1 for r in results if r.get("passed"))
    return (passed / len(results)) * 100.0


def calculate_composite_score(
    test_score: Optional[float],
    llm_score: Optional[float],
    test_weight: float,
    llm_weight: float,
    late_penalty: float = 0.0,
) -> float:
    """Calculate composite score from test and LLM scores with optional late penalty."""
    composite = (
        test_weight * (test_score or 0) +
        llm_weight * (llm_score or 0)
    )
    return max(0.0, composite - late_penalty)
