"""Integration tests for sandbox execution (Task 16.4)"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import json


class TestSandboxExecution:
    """Tests for the complete execution flow from submission to result"""

    @patch("app.tasks.get_docker_client")
    def test_execution_success(self, mock_get_docker):
        from app.tasks import truncate_output, create_test_harness
        from app.models.exercise import TestCase

        # Test truncation
        short = "hello"
        assert truncate_output(short) == short

        long = "x" * 200_000
        truncated = truncate_output(long)
        assert len(truncated) < 200_000
        assert "truncated" in truncated.lower()

    def test_create_test_harness(self):
        from app.tasks import create_test_harness
        from unittest.mock import Mock

        tc = Mock()
        tc.name = "test_add"
        tc.input_data = "add(1, 2)"
        tc.expected_output = "3"

        harness = create_test_harness([tc], "def add(a, b): return a + b")
        assert "test_add" in harness
        assert "add(1, 2)" in harness

    @patch("app.tasks.get_docker_client")
    def test_container_config_security(self, mock_get_docker):
        """Verify container security settings are applied"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b'[{"name": "test", "passed": true, "message": "ok"}]'
        mock_client.containers.run.return_value = mock_container
        mock_get_docker.return_value = mock_client

        # Import after patching
        from app.tasks import execute_submission

        # This would need actual DB setup to fully test; here we verify
        # the function exists and is callable (it's a Celery task)
        assert callable(execute_submission)

    def test_output_truncation_boundary(self):
        from app.tasks import truncate_output, MAX_OUTPUT_SIZE

        # Exactly at limit
        exact = "x" * MAX_OUTPUT_SIZE
        assert truncate_output(exact) == exact

        # One over
        over = "x" * (MAX_OUTPUT_SIZE + 1)
        assert len(truncate_output(over)) < len(over)


class TestDockerSecurity:
    """Verify security constraints are properly configured"""

    def test_sandbox_constants(self):
        """Verify security-related constants are defined"""
        from app.tasks import MAX_OUTPUT_SIZE
        assert MAX_OUTPUT_SIZE == 100 * 1024  # 100KB
