import os
import docker
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    output: str
    error: str | None
    timed_out: bool
    exit_code: int


class Sandbox:
    IMAGE_NAME = "autograder-sandbox"
    TIMEOUT_SECONDS = 30
    MEMORY_LIMIT = "256m"
    CPU_LIMIT = 1.0

    def __init__(self):
        self.client = self._get_docker_client()

    def _get_docker_client(self):
        try:
            return docker.from_env()
        except docker.errors.DockerException:
            # Try Docker Desktop socket on macOS
            home = os.path.expanduser("~")
            docker_socket = f"unix://{home}/.docker/run/docker.sock"
            return docker.DockerClient(base_url=docker_socket)

    def execute(self, code: str, test_input: str) -> ExecutionResult:
        full_code = f"""{code}

# Execute test
result = {test_input}
print(result)
"""
        try:
            container = self.client.containers.run(
                self.IMAGE_NAME,
                command=["python", "-c", full_code],
                detach=True,
                network_mode="none",
                mem_limit=self.MEMORY_LIMIT,
                cpu_period=100000,
                cpu_quota=int(100000 * self.CPU_LIMIT),
                read_only=True,
                user="nobody",
                tmpfs={"/tmp": "size=10m,mode=1777"},
            )

            try:
                result = container.wait(timeout=self.TIMEOUT_SECONDS)
                exit_code = result["StatusCode"]
                logs = container.logs(stdout=True, stderr=True).decode("utf-8")

                if exit_code == 0:
                    return ExecutionResult(
                        output=logs.strip(),
                        error=None,
                        timed_out=False,
                        exit_code=exit_code,
                    )
                else:
                    return ExecutionResult(
                        output="",
                        error=logs.strip(),
                        timed_out=False,
                        exit_code=exit_code,
                    )
            except Exception as e:
                if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                    container.kill()
                    return ExecutionResult(
                        output="",
                        error="Execution timed out",
                        timed_out=True,
                        exit_code=-1,
                    )
                raise
            finally:
                container.remove(force=True)

        except docker.errors.ImageNotFound:
            return ExecutionResult(
                output="",
                error=f"Sandbox image '{self.IMAGE_NAME}' not found. Build it with: docker build -f Dockerfile.sandbox -t {self.IMAGE_NAME} .",
                timed_out=False,
                exit_code=-1,
            )
        except docker.errors.APIError as e:
            return ExecutionResult(
                output="",
                error=f"Docker API error: {str(e)}",
                timed_out=False,
                exit_code=-1,
            )
