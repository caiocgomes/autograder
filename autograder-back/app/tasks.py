"""
Celery tasks for async processing

Tasks:
- execute_submission: Run student code in Docker sandbox
- grade_submission: Calculate test scores and trigger LLM grading
- llm_evaluate: Call LLM API for qualitative feedback
"""
import os
import tempfile
import docker
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.submission import Submission, SubmissionStatus, TestResult, Grade
from app.models.exercise import Exercise, TestCase


MAX_OUTPUT_SIZE = 100 * 1024  # 100KB


@celery_app.task(name="app.tasks.health_check")
def health_check():
    """Simple health check task for testing Celery setup"""
    return {"status": "ok", "message": "Celery is working"}


def get_docker_client():
    """Get Docker client with fallback to macOS socket"""
    try:
        return docker.from_env()
    except docker.errors.DockerException:
        home = os.path.expanduser("~")
        docker_socket = f"unix://{home}/.docker/run/docker.sock"
        return docker.DockerClient(base_url=docker_socket)


def truncate_output(text: str, max_size: int = MAX_OUTPUT_SIZE) -> str:
    """Truncate output if it exceeds max size"""
    if len(text) <= max_size:
        return text
    return text[:max_size] + "\n... [Output truncated]"


def create_test_harness(test_cases: List[TestCase], student_code: str) -> str:
    """
    Create a Python test harness that imports student code and runs test cases.
    Returns the harness code as a string.
    """
    harness = """
import sys
import json
import traceback
from io import StringIO

# Student code is available in 'student_code' module
student_code = '''
{student_code}
'''

# Execute student code in a namespace
student_namespace = {{}}
try:
    exec(student_code, student_namespace)
except Exception as e:
    print(json.dumps({{
        'error': 'Failed to load student code',
        'message': str(e),
        'traceback': traceback.format_exc()
    }}))
    sys.exit(1)

# Test cases
test_cases = {test_cases_json}

results = []

for test_case in test_cases:
    test_name = test_case['name']
    test_input = test_case['input']
    expected_output = test_case['expected']

    try:
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        # Execute test input in student namespace
        try:
            result = eval(test_input, student_namespace)
        finally:
            sys.stdout = old_stdout

        stdout = captured_output.getvalue()

        # Compare result
        passed = str(result).strip() == str(expected_output).strip()

        results.append({{
            'name': test_name,
            'passed': passed,
            'message': f'Expected: {{expected_output}}, Got: {{result}}' if not passed else 'Test passed',
            'stdout': stdout,
            'stderr': ''
        }})
    except Exception as e:
        results.append({{
            'name': test_name,
            'passed': False,
            'message': str(e),
            'stdout': '',
            'stderr': traceback.format_exc()
        }})

# Print results as JSON
print(json.dumps(results))
""".format(
        student_code=student_code.replace("'''", "\\'\\'\\'"),
        test_cases_json=json.dumps([
            {
                'name': tc.name,
                'input': tc.input_data,
                'expected': tc.expected_output
            }
            for tc in test_cases
        ])
    )

    return harness


@celery_app.task(
    name="app.tasks.execute_submission",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def execute_submission(self, submission_id: int, late_penalty: float = 0.0):
    """
    Execute student code in sandboxed Docker container.

    Args:
        submission_id: ID of submission to execute
        late_penalty: Late penalty percentage to apply (0-100)
    """
    db: Session = SessionLocal()

    try:
        # Get submission
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return {"error": "Submission not found"}

        # Update status to running
        submission.status = SubmissionStatus.RUNNING
        db.commit()

        # Get exercise and test cases
        exercise = db.query(Exercise).filter(Exercise.id == submission.exercise_id).first()
        if not exercise:
            submission.status = SubmissionStatus.FAILED
            submission.error_message = "Exercise not found"
            db.commit()
            return {"error": "Exercise not found"}

        test_cases = db.query(TestCase).filter(TestCase.exercise_id == exercise.id).all()

        if not test_cases and exercise.has_tests:
            submission.status = SubmissionStatus.FAILED
            submission.error_message = "No test cases configured for this exercise"
            db.commit()
            return {"error": "No test cases configured"}

        # Create Docker client
        docker_client = get_docker_client()

        # Create test harness
        test_harness_code = create_test_harness(test_cases, submission.code)

        # Create temporary directory for code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write test harness to file
            harness_path = Path(tmpdir) / "test_harness.py"
            harness_path.write_text(test_harness_code)

            # TODO: Mount datasets if exercise has them (task 9.6)
            # For now, we'll just mount the test harness

            try:
                # Create and run container
                container = docker_client.containers.run(
                    "autograder-sandbox",
                    command=["python", "/workspace/test_harness.py"],
                    detach=True,
                    network_mode="none",
                    mem_limit=f"{exercise.memory_limit_mb}m",
                    cpu_period=100000,
                    cpu_quota=100000,  # 1 core
                    read_only=True,
                    user="nobody",
                    cap_drop=["ALL"],  # Drop all capabilities
                    security_opt=["no-new-privileges"],
                    pids_limit=256,  # Prevent fork bombs
                    tmpfs={"/tmp": "size=50m,mode=1777"},
                    volumes={
                        str(harness_path.absolute()): {
                            'bind': '/workspace/test_harness.py',
                            'mode': 'ro'
                        }
                    }
                )

                # Wait for container with timeout
                try:
                    result = container.wait(timeout=exercise.timeout_seconds)
                    exit_code = result["StatusCode"]

                    # Get logs
                    logs = container.logs(stdout=True, stderr=True).decode("utf-8")
                    logs = truncate_output(logs)

                except Exception as e:
                    if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                        container.kill()
                        submission.status = SubmissionStatus.FAILED
                        submission.error_message = "Execution timed out"
                        db.commit()
                        return {"error": "Timeout"}
                    raise

                finally:
                    # Always destroy container
                    container.remove(force=True)

                # Parse test results
                import json
                try:
                    test_results_data = json.loads(logs)

                    # Save test results to database
                    for result_data in test_results_data:
                        test_result = TestResult(
                            submission_id=submission.id,
                            test_name=result_data['name'],
                            passed=result_data['passed'],
                            message=truncate_output(result_data.get('message', '')),
                            stdout=truncate_output(result_data.get('stdout', '')),
                            stderr=truncate_output(result_data.get('stderr', ''))
                        )
                        db.add(test_result)

                    # Calculate test score
                    total_tests = len(test_results_data)
                    passed_tests = sum(1 for r in test_results_data if r['passed'])
                    test_score = (passed_tests / total_tests * 100) if total_tests > 0 else 0

                    # Create grade record
                    grade = Grade(
                        submission_id=submission.id,
                        test_score=test_score,
                        final_score=test_score,  # Will be updated if LLM grading is enabled
                        late_penalty_applied=late_penalty,
                        published=exercise.auto_publish_grades if hasattr(exercise, 'auto_publish_grades') else False
                    )
                    db.add(grade)

                    # Update submission status
                    submission.status = SubmissionStatus.COMPLETED
                    db.commit()

                    # Trigger LLM grading if enabled
                    if exercise.llm_grading_enabled:
                        llm_evaluate_submission.delay(submission.id)

                    return {
                        "submission_id": submission.id,
                        "status": "completed",
                        "test_score": test_score,
                        "passed": passed_tests,
                        "total": total_tests
                    }

                except json.JSONDecodeError:
                    # Test harness failed to return valid JSON
                    submission.status = SubmissionStatus.FAILED
                    submission.error_message = f"Test execution error: {logs}"
                    db.commit()
                    return {"error": "Test execution failed", "logs": logs}

            except docker.errors.ImageNotFound:
                submission.status = SubmissionStatus.FAILED
                submission.error_message = "Sandbox image not found. Contact administrator."
                db.commit()
                raise
            except docker.errors.APIError as e:
                submission.status = SubmissionStatus.FAILED
                submission.error_message = f"Docker error: {str(e)}"
                db.commit()
                raise

    except Exception as e:
        # Retry on infrastructure failures
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        # Max retries reached
        submission.status = SubmissionStatus.FAILED
        submission.error_message = f"Execution failed after {self.max_retries} retries: {str(e)}"
        db.commit()
        return {"error": str(e)}

    finally:
        db.close()


def create_llm_prompt(exercise: Exercise, code: str) -> str:
    """
    Create prompt for LLM evaluation.

    Args:
        exercise: Exercise object with description and criteria
        code: Student code to evaluate

    Returns:
        Formatted prompt string
    """
    prompt = f"""You are evaluating student code for a programming exercise.

**Exercise:**
{exercise.title}

**Description:**
{exercise.description}

**Student Code:**
```python
{code}
```

**Grading Criteria:**
{exercise.llm_grading_criteria if exercise.llm_grading_criteria else "Code quality, readability, efficiency, and correctness."}

Please provide:
1. A detailed feedback paragraph explaining strengths and areas for improvement
2. A numerical score from 0-100

Format your response as JSON:
{{
  "feedback": "Your detailed feedback here...",
  "score": 85
}}
"""
    return prompt


@celery_app.task(
    name="app.tasks.llm_evaluate_submission",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def llm_evaluate_submission(self, submission_id: int):
    """
    Evaluate submission using LLM for qualitative feedback.

    Args:
        submission_id: ID of submission to evaluate

    Returns:
        dict with evaluation results
    """
    db: Session = SessionLocal()

    try:
        # Get submission and exercise
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return {"error": "Submission not found"}

        exercise = db.query(Exercise).filter(Exercise.id == submission.exercise_id).first()
        if not exercise or not exercise.llm_grading_enabled:
            return {"error": "LLM grading not enabled for this exercise"}

        # Check cache first
        from app.models.submission import LLMEvaluation
        cached_eval = db.query(LLMEvaluation).filter(
            LLMEvaluation.code_hash == submission.code_hash
        ).first()

        if cached_eval:
            # Use cached evaluation
            new_eval = LLMEvaluation(
                submission_id=submission.id,
                code_hash=submission.code_hash,
                feedback=cached_eval.feedback,
                score=cached_eval.score,
                cached=True
            )
            db.add(new_eval)

            # Update grade with composite score
            grade = db.query(Grade).filter(Grade.submission_id == submission.id).first()
            if grade:
                composite_score = (
                    exercise.test_weight * (grade.test_score or 0) +
                    exercise.llm_weight * new_eval.score
                )
                grade.llm_score = new_eval.score
                grade.final_score = max(0, composite_score - grade.late_penalty_applied)

            db.commit()
            return {
                "submission_id": submission.id,
                "cached": True,
                "score": new_eval.score
            }

        # Call LLM API
        from app.config import settings
        import anthropic
        import openai
        import json

        prompt = create_llm_prompt(exercise, submission.code)

        try:
            if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
                # Use Anthropic Claude
                client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                response_text = message.content[0].text

            elif settings.llm_provider == "openai" and settings.openai_api_key:
                # Use OpenAI GPT
                client = openai.OpenAI(api_key=settings.openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a code grading assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                response_text = response.choices[0].message.content

            else:
                raise ValueError("No LLM API key configured")

            # Parse response
            try:
                # Try to extract JSON from markdown code block if present
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

                result = json.loads(response_text)
                feedback = result.get("feedback", "")
                score = float(result.get("score", 0))

                # Validate score range
                score = max(0, min(100, score))

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                # Fallback: use raw response as feedback with default score
                feedback = response_text
                score = 70.0  # Default score if parsing fails

            # Save evaluation
            llm_eval = LLMEvaluation(
                submission_id=submission.id,
                code_hash=submission.code_hash,
                feedback=feedback,
                score=score,
                cached=False
            )
            db.add(llm_eval)

            # Update grade with composite score
            grade = db.query(Grade).filter(Grade.submission_id == submission.id).first()
            if grade:
                composite_score = (
                    exercise.test_weight * (grade.test_score or 0) +
                    exercise.llm_weight * score
                )
                grade.llm_score = score
                grade.final_score = max(0, composite_score - grade.late_penalty_applied)

            db.commit()

            return {
                "submission_id": submission.id,
                "cached": False,
                "score": score,
                "feedback_length": len(feedback)
            }

        except anthropic.RateLimitError as e:
            # Rate limit hit, retry later
            raise self.retry(exc=e, countdown=120)

        except (anthropic.APIError, openai.APIError) as e:
            # API error - fallback to tests-only grading
            grade = db.query(Grade).filter(Grade.submission_id == submission.id).first()
            if grade and grade.test_score is not None:
                grade.final_score = max(0, grade.test_score - grade.late_penalty_applied)
                db.commit()

            return {
                "submission_id": submission.id,
                "error": "LLM API failed, using tests-only score",
                "fallback": True
            }

    except Exception as e:
        # Retry on unexpected errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        # Max retries - fallback to tests-only
        grade = db.query(Grade).filter(Grade.submission_id == submission.id).first()
        if grade and grade.test_score is not None:
            grade.final_score = max(0, grade.test_score - grade.late_penalty_applied)
            db.commit()

        return {"error": str(e), "fallback": True}

    finally:
        db.close()
