import pytest
from unittest.mock import Mock, MagicMock, patch

from services.sandbox import Sandbox, ExecutionResult
import docker.errors


class TestExecutionResult:
    def test_execution_result_success(self):
        result = ExecutionResult(output="42", error=None, timed_out=False, exit_code=0)
        assert result.output == "42"
        assert result.error is None
        assert result.timed_out is False
        assert result.exit_code == 0

    def test_execution_result_error(self):
        result = ExecutionResult(output="", error="NameError", timed_out=False, exit_code=1)
        assert result.output == ""
        assert result.error == "NameError"
        assert result.exit_code == 1

    def test_execution_result_timeout(self):
        result = ExecutionResult(output="", error="Execution timed out", timed_out=True, exit_code=-1)
        assert result.timed_out is True


class TestSandbox:
    @patch("services.sandbox.docker")
    def test_execute_success(self, mock_docker, sample_code):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"3"
        mock_client.containers.run.return_value = mock_container
        mock_docker.from_env.return_value = mock_client

        sandbox = Sandbox()
        result = sandbox.execute(sample_code, "add(1, 2)")

        assert result.output == "3"
        assert result.error is None
        assert result.timed_out is False
        assert result.exit_code == 0
        mock_container.remove.assert_called_once_with(force=True)

    @patch("services.sandbox.docker")
    def test_execute_with_error(self, mock_docker):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.return_value = b"NameError: name 'undefined' is not defined"
        mock_client.containers.run.return_value = mock_container
        mock_docker.from_env.return_value = mock_client

        sandbox = Sandbox()
        result = sandbox.execute("print(undefined)", "None")

        assert result.output == ""
        assert "NameError" in result.error
        assert result.exit_code == 1

    @patch("services.sandbox.docker")
    def test_execute_timeout(self, mock_docker):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.wait.side_effect = Exception("timed out waiting for container")
        mock_client.containers.run.return_value = mock_container
        mock_docker.from_env.return_value = mock_client

        sandbox = Sandbox()
        result = sandbox.execute("while True: pass", "None")

        assert result.timed_out is True
        assert result.error == "Execution timed out"
        assert result.exit_code == -1
        mock_container.kill.assert_called_once()

    @patch("services.sandbox.docker")
    def test_execute_image_not_found(self, mock_docker):
        mock_client = MagicMock()
        mock_client.containers.run.side_effect = docker.errors.ImageNotFound("not found")
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors = docker.errors

        sandbox = Sandbox()
        result = sandbox.execute("print(1)", "None")

        assert "not found" in result.error.lower()
        assert result.exit_code == -1

    @patch("services.sandbox.docker")
    def test_execute_container_config(self, mock_docker):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"ok"
        mock_client.containers.run.return_value = mock_container
        mock_docker.from_env.return_value = mock_client

        sandbox = Sandbox()
        sandbox.execute("print('ok')", "None")

        call_kwargs = mock_client.containers.run.call_args[1]
        assert call_kwargs["network_mode"] == "none"
        assert call_kwargs["mem_limit"] == "256m"
        assert call_kwargs["read_only"] is True
        assert call_kwargs["user"] == "nobody"
        assert call_kwargs["detach"] is True
