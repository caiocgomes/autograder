"""
Celery tasks for async processing

Tasks:
- execute_submission: Run student code in Docker sandbox
- process_hotmart_event: Parse webhook and trigger lifecycle transition
- execute_side_effect: Re-execute a failed side-effect with retry
- grade_submission: Calculate test scores and trigger LLM grading
- llm_evaluate: Call LLM API for qualitative feedback
"""
import json
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
    suffix = "\n... [Output truncated]"
    return text[:max_size - len(suffix)] + suffix


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
            LLMEvaluation.content_hash == submission.content_hash
        ).first()

        if cached_eval:
            # Use cached evaluation
            new_eval = LLMEvaluation(
                submission_id=submission.id,
                content_hash=submission.content_hash,
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
        from app.services.settings import get_llm_api_key
        import anthropic
        import openai
        import json

        prompt = create_llm_prompt(exercise, submission.code)

        try:
            if settings.llm_provider == "anthropic":
                api_key = get_llm_api_key("anthropic", db)
                client = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                response_text = message.content[0].text

            elif settings.llm_provider == "openai":
                api_key = get_llm_api_key("openai", db)
                client = openai.OpenAI(api_key=api_key)
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
                content_hash=submission.content_hash,
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


# ── LLM-first grading pipeline ──────────────────────────────────────────


def create_rubric_prompt(exercise, rubric_dimensions, content, is_image=False):
    """
    Build prompt for rubric-based LLM evaluation.

    Args:
        exercise: Exercise ORM object
        rubric_dimensions: List of RubricDimension objects
        content: Extracted text content (or None if image)
        is_image: If True, returns list for multimodal input

    Returns:
        str prompt for text, or list of content blocks for multimodal
    """
    dims_text = "\n".join(
        f"- {d.name} (peso: {d.weight}): {d.description or 'Sem descrição adicional'}"
        for d in rubric_dimensions
    )

    dim_names_json = ", ".join(f'"{d.name}"' for d in rubric_dimensions)

    base_prompt = f"""Você está avaliando uma submissão de aluno.

**Exercício:** {exercise.title}

**Descrição:**
{exercise.description}

**Rubrica de avaliação:**
{dims_text}

Avalie a submissão em cada dimensão da rubrica.
Responda SOMENTE com JSON válido no formato:
{{
  "dimensions": [
    {{"name": "<nome da dimensão>", "score": <0-100>, "feedback": "<feedback>"}},
    ...
  ],
  "overall_feedback": "<feedback geral>"
}}

As dimensões DEVEM ser exatamente: [{dim_names_json}]"""

    if is_image:
        return [
            {"type": "text", "text": base_prompt + "\n\nA submissão é a imagem anexada."},
        ]

    return base_prompt + f"\n\n**Submissão do aluno:**\n{content}"


def parse_rubric_response(response_text, expected_dimensions):
    """
    Parse and validate LLM rubric response.

    Args:
        response_text: Raw LLM response text
        expected_dimensions: List of RubricDimension objects

    Returns:
        dict with 'dimensions' list and 'overall_feedback'

    Raises:
        ValueError: If response is malformed or dimensions don't match
    """
    import json as _json

    text = response_text.strip()
    # Extract JSON from markdown code blocks if present
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()

    result = _json.loads(text)

    if "dimensions" not in result:
        raise ValueError("Response missing 'dimensions' key")

    expected_names = {d.name for d in expected_dimensions}
    response_names = {d["name"] for d in result["dimensions"]}

    missing = expected_names - response_names
    if missing:
        raise ValueError(f"Missing dimensions in response: {missing}")

    # Clamp scores to 0-100
    for dim in result["dimensions"]:
        dim["score"] = max(0, min(100, float(dim["score"])))
        dim["feedback"] = dim.get("feedback", "")

    result["overall_feedback"] = result.get("overall_feedback", "")
    return result


def _call_llm(prompt, image_path=None, db=None):
    """
    Call configured LLM provider. Returns response text.

    Args:
        prompt: Text prompt or list of content blocks (multimodal)
        image_path: Path to image file for multimodal input (Anthropic)
        db: Database session for resolving API key from system settings
    """
    from app.config import settings
    from app.services.settings import get_llm_api_key
    import anthropic
    import openai

    if settings.llm_provider == "anthropic":
        api_key = get_llm_api_key("anthropic", db) if db else settings.anthropic_api_key
        client = anthropic.Anthropic(api_key=api_key)

        if image_path:
            import base64
            import mimetypes
            media_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
            image_data = Path(image_path).read_bytes()
            b64 = base64.b64encode(image_data).decode("utf-8")

            messages_content = [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            ]
            if isinstance(prompt, list):
                messages_content.extend(prompt)
            else:
                messages_content.append({"type": "text", "text": prompt})

            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                messages=[{"role": "user", "content": messages_content}]
            )
        else:
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt if isinstance(prompt, str) else prompt}]
            )
        return message.content[0].text

    elif settings.llm_provider == "openai":
        api_key = get_llm_api_key("openai", db) if db else settings.openai_api_key
        client = openai.OpenAI(api_key=api_key)

        messages_content = []
        if image_path:
            import base64
            import mimetypes
            media_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
            image_data = Path(image_path).read_bytes()
            b64 = base64.b64encode(image_data).decode("utf-8")

            if isinstance(prompt, list):
                for block in prompt:
                    messages_content.append(block)
            else:
                messages_content.append({"type": "text", "text": prompt})
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{b64}"}
            })
        else:
            if isinstance(prompt, str):
                messages_content = prompt
            else:
                messages_content = prompt

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a grading assistant."},
                {"role": "user", "content": messages_content}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content

    else:
        raise ValueError("No LLM API key configured")


@celery_app.task(
    name="app.tasks.grade_llm_first",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def grade_llm_first(self, submission_id: int, late_penalty: float = 0.0):
    """
    Grade submission using LLM with rubric (llm-first mode).
    No sandbox, no Docker, no test harness.
    """
    import json as _json

    db: Session = SessionLocal()

    try:
        from app.models.submission import LLMEvaluation, RubricScore
        from app.models.exercise import RubricDimension
        from app.services.file_storage import get_absolute_path

        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return {"error": "Submission not found"}

        submission.status = SubmissionStatus.RUNNING
        db.commit()

        exercise = db.query(Exercise).filter(Exercise.id == submission.exercise_id).first()
        if not exercise:
            submission.status = SubmissionStatus.FAILED
            submission.error_message = "Exercise not found"
            db.commit()
            return {"error": "Exercise not found"}

        rubric_dims = (
            db.query(RubricDimension)
            .filter(RubricDimension.exercise_id == exercise.id)
            .order_by(RubricDimension.position)
            .all()
        )

        if not rubric_dims:
            submission.status = SubmissionStatus.FAILED
            submission.error_message = "No rubric dimensions configured"
            db.commit()
            return {"error": "No rubric dimensions"}

        # Check cache: same content_hash AND same exercise (rubric may differ between exercises)
        cached_eval = (
            db.query(LLMEvaluation)
            .join(Submission, LLMEvaluation.submission_id == Submission.id)
            .filter(
                LLMEvaluation.content_hash == submission.content_hash,
                Submission.exercise_id == exercise.id,
                LLMEvaluation.submission_id != submission.id,
            )
            .first()
        )

        if cached_eval:
            # Copy cached rubric scores
            cached_scores = (
                db.query(RubricScore)
                .filter(RubricScore.submission_id == cached_eval.submission_id)
                .all()
            )

            for cs in cached_scores:
                new_score = RubricScore(
                    submission_id=submission.id,
                    dimension_id=cs.dimension_id,
                    score=cs.score,
                    feedback=cs.feedback,
                )
                db.add(new_score)

            new_eval = LLMEvaluation(
                submission_id=submission.id,
                content_hash=submission.content_hash,
                feedback=cached_eval.feedback,
                score=cached_eval.score,
                cached=True,
            )
            db.add(new_eval)

            # Calculate weighted score
            final_score = sum(
                cs.score * next(d.weight for d in rubric_dims if d.id == cs.dimension_id)
                for cs in cached_scores
            )

            grade = Grade(
                submission_id=submission.id,
                llm_score=final_score,
                final_score=max(0, final_score - late_penalty),
                late_penalty_applied=late_penalty,
                published=False,
            )
            db.add(grade)
            submission.status = SubmissionStatus.COMPLETED
            db.commit()

            return {"submission_id": submission.id, "cached": True, "final_score": grade.final_score}

        # Determine content and whether it's an image
        is_image = False
        image_path = None
        content = None

        if submission.file_path and submission.content_type:
            abs_path = get_absolute_path(submission.file_path)
            if submission.content_type.startswith("image/"):
                is_image = True
                image_path = abs_path
            else:
                from app.services.content_extractor import extract_content
                content = extract_content(str(abs_path), submission.content_type)
        else:
            # Code submission with llm-first grading
            content = submission.code

        # Build prompt
        prompt = create_rubric_prompt(exercise, rubric_dims, content, is_image=is_image)

        # Call LLM (with retry on malformed response)
        parsed = None
        for attempt in range(2):
            try:
                response_text = _call_llm(
                    prompt if not is_image else prompt,
                    image_path=image_path if is_image else None,
                    db=db,
                )
                parsed = parse_rubric_response(response_text, rubric_dims)
                break
            except (ValueError, _json.JSONDecodeError) as parse_err:
                if attempt == 0:
                    # Retry with corrective prompt
                    if isinstance(prompt, list):
                        prompt.append({
                            "type": "text",
                            "text": f"\n\nSua resposta anterior não era JSON válido. Erro: {parse_err}. Tente novamente com JSON válido."
                        })
                    else:
                        prompt += f"\n\nSua resposta anterior não era JSON válido. Erro: {parse_err}. Tente novamente com JSON válido."
                    continue
                else:
                    submission.status = SubmissionStatus.FAILED
                    submission.error_message = f"LLM returned invalid response after retry: {parse_err}"
                    db.commit()
                    return {"error": str(parse_err)}

        if not parsed:
            submission.status = SubmissionStatus.FAILED
            submission.error_message = "Failed to parse LLM response"
            db.commit()
            return {"error": "Parse failure"}

        # Persist rubric scores
        dim_by_name = {d.name: d for d in rubric_dims}
        for dim_result in parsed["dimensions"]:
            dim_obj = dim_by_name.get(dim_result["name"])
            if not dim_obj:
                continue
            rs = RubricScore(
                submission_id=submission.id,
                dimension_id=dim_obj.id,
                score=dim_result["score"],
                feedback=dim_result["feedback"],
            )
            db.add(rs)

        # Calculate weighted final score
        final_score = sum(
            dim_by_name[d["name"]].weight * d["score"]
            for d in parsed["dimensions"]
            if d["name"] in dim_by_name
        )

        # Persist LLM evaluation
        llm_eval = LLMEvaluation(
            submission_id=submission.id,
            content_hash=submission.content_hash,
            feedback=parsed["overall_feedback"],
            score=final_score,
            cached=False,
        )
        db.add(llm_eval)

        # Create grade
        grade = Grade(
            submission_id=submission.id,
            llm_score=final_score,
            final_score=max(0, final_score - late_penalty),
            late_penalty_applied=late_penalty,
            published=False,
        )
        db.add(grade)

        submission.status = SubmissionStatus.COMPLETED
        db.commit()

        return {
            "submission_id": submission.id,
            "cached": False,
            "final_score": grade.final_score,
            "dimensions": len(parsed["dimensions"]),
        }

    except Exception as e:
        import anthropic
        import openai

        if isinstance(e, (anthropic.RateLimitError,)):
            raise self.retry(exc=e, countdown=120)

        if isinstance(e, (anthropic.APIError, openai.APIError)):
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e)

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = SubmissionStatus.FAILED
            submission.error_message = f"LLM grading failed after {self.max_retries} retries: {str(e)}"
            db.commit()

        return {"error": str(e)}

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Course Orchestrator Tasks
# ---------------------------------------------------------------------------


@celery_app.task(name="app.tasks.process_hotmart_event", bind=True, max_retries=1)
def process_hotmart_event(self, event_id: int, payload: dict):
    """
    Parse a Hotmart webhook event and trigger the appropriate lifecycle transition.
    Runs async to keep the webhook endpoint fast.
    """
    from app.integrations.hotmart import parse_payload, PURCHASE_APPROVED, PURCHASE_DELAYED, PURCHASE_REFUNDED, SUBSCRIPTION_CANCELLATION
    from app.models.event import Event, EventStatus
    from app.models.user import User, UserRole, LifecycleStatus
    from app.services.lifecycle import transition
    import secrets

    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"error": f"Event {event_id} not found"}

        parsed = parse_payload(payload)
        if not parsed:
            event.status = EventStatus.FAILED
            event.error_message = "Failed to parse Hotmart payload"
            db.commit()
            return {"error": "parse_failure"}

        # Resolve or create student
        user = db.query(User).filter(User.hotmart_id == parsed.buyer_email).first()
        if not user:
            user = db.query(User).filter(User.email == parsed.buyer_email).first()

        trigger_map = {
            PURCHASE_APPROVED: "purchase_approved",
            PURCHASE_DELAYED: "purchase_delayed",
            PURCHASE_REFUNDED: "purchase_refunded",
            SUBSCRIPTION_CANCELLATION: "subscription_cancelled",
        }
        trigger = trigger_map.get(parsed.event_type)
        if not trigger:
            event.status = EventStatus.IGNORED
            db.commit()
            return {"status": "ignored"}

        if not user and trigger in ("purchase_approved", "purchase_delayed"):
            # Auto-create student account
            from app.auth.security import hash_password
            user = User(
                email=parsed.buyer_email,
                password_hash=hash_password(secrets.token_urlsafe(16)),
                role=UserRole.STUDENT,
                hotmart_id=parsed.buyer_email,
                lifecycle_status=None,
            )
            db.add(user)
            db.flush()

        if not user:
            event.status = EventStatus.FAILED
            event.error_message = f"Student not found for email: {parsed.buyer_email}"
            db.commit()
            return {"error": "student_not_found"}

        result = transition(
            db,
            user,
            trigger=trigger,
            hotmart_product_id=parsed.hotmart_product_id,
        )

        if result is None:
            event.status = EventStatus.IGNORED
            event.error_message = f"No valid transition from {user.lifecycle_status} with trigger {trigger}"
        else:
            event.target_id = user.id
            event.status = EventStatus.PROCESSED

        db.commit()
        return {"status": str(result), "user_id": user.id}

    except Exception as e:
        db.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)
        # Mark event as failed
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            if event:
                event.status = EventStatus.FAILED
                event.error_message = str(e)
                db.commit()
        except Exception:
            pass
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(name="app.tasks.execute_side_effect", bind=True, max_retries=1)
def execute_side_effect(self, event_id: int):
    """
    Re-execute a failed side-effect identified by event_id.
    Used by the admin manual retry endpoint.
    """
    from app.models.event import Event, EventStatus
    from app.models.user import User

    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"error": f"Event {event_id} not found"}

        if event.status != EventStatus.FAILED:
            return {"status": "skipped", "reason": "Event not in failed state"}

        # Re-dispatch based on event type
        event_type = event.type
        payload = event.payload or {}
        target_user = db.query(User).filter(User.id == event.target_id).first() if event.target_id else None

        success = False

        if event_type == "discord.role_assigned" and target_user and target_user.discord_id:
            from app.integrations.discord import assign_role
            success = assign_role(target_user.discord_id, payload.get("role_id", ""))

        elif event_type == "discord.role_revoked" and target_user and target_user.discord_id:
            from app.integrations.discord import revoke_role
            success = revoke_role(target_user.discord_id, payload.get("role_id", ""))

        elif event_type == "evolution.message_sent" and target_user and target_user.whatsapp_number:
            from app.integrations.evolution import send_message
            text = payload.get("text", "")
            success = send_message(target_user.whatsapp_number, text)

        else:
            return {"status": "skipped", "reason": f"No handler for event type: {event_type}"}

        if success:
            event.status = EventStatus.PROCESSED
            event.error_message = None
            db.commit()
            return {"status": "success"}
        else:
            return {"status": "failed", "reason": "Side-effect returned False"}

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(name="sync_hotmart_students", bind=True, max_retries=0)
def sync_hotmart_students(self, product_id=None):
    """
    Reconcile active Hotmart buyers with local user records.

    Iterates active subscriptions and sales, creates missing users, and
    transitions each to the appropriate lifecycle state. Idempotent: users
    already active are silently skipped.
    """
    from app.integrations import hotmart
    from app.models.event import Event, EventStatus
    from app.models.user import User, UserRole
    from app.services.lifecycle import transition
    from app.auth.security import hash_password
    import secrets

    db = SessionLocal()
    try:
        # Collect all active buyers with phone numbers (from sales/users endpoint)
        phones: dict = {}  # email -> phone
        for item in hotmart.list_buyers_with_phone(product_id):
            email = item.get("email", "").lower().strip()
            phone = item.get("phone", "")
            if email and phone:
                phones[email] = phone

        # Collect all active buyers, deduplicated by email
        seen: dict = {}  # email -> hotmart_product_id (last one wins)

        for item in hotmart.list_active_subscriptions(product_id):
            email = item.get("email", "").lower().strip()
            if email:
                seen[email] = item.get("hotmart_product_id", "")

        for item in hotmart.list_active_sales(product_id):
            email = item.get("email", "").lower().strip()
            if email and email not in seen:
                seen[email] = item.get("hotmart_product_id", "")

        synced = 0
        created = 0
        already_active = 0

        for email, hpid in seen.items():
            try:
                user = db.query(User).filter(User.hotmart_id == email).first()
                if not user:
                    user = db.query(User).filter(User.email == email).first()

                if not user:
                    user = User(
                        email=email,
                        password_hash=hash_password(secrets.token_urlsafe(16)),
                        role=UserRole.STUDENT,
                        hotmart_id=email,
                        lifecycle_status=None,
                    )
                    db.add(user)
                    db.flush()
                    created += 1
                elif not user.hotmart_id:
                    user.hotmart_id = email

                # Populate whatsapp_number from Hotmart if not set
                phone = phones.get(email, "")
                if phone and not user.whatsapp_number:
                    user.whatsapp_number = phone

                result = transition(
                    db,
                    user,
                    trigger="purchase_approved",
                    hotmart_product_id=hpid,
                )

                if result is None:
                    already_active += 1
                else:
                    synced += 1

                db.commit()

            except Exception as e:
                db.rollback()
                import logging
                logging.getLogger(__name__).error(
                    "sync_hotmart_students: failed to process %s: %s", email, e
                )

        # Log completion event
        log_event = Event(
            type="hotmart.sync_completed",
            payload={
                "synced": synced,
                "created": created,
                "already_active": already_active,
                "total_fetched": len(seen),
                "product_id": product_id,
            },
            status=EventStatus.PROCESSED,
        )
        db.add(log_event)
        db.commit()

        return {
            "status": "ok",
            "synced": synced,
            "created": created,
            "already_active": already_active,
            "total_fetched": len(seen),
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()

# ---------------------------------------------------------------------------
# Student Course Status Sync Helpers
# ---------------------------------------------------------------------------

def _update_scd2(user_id: int, product_id: int, new_status: str, source: str, db) -> bool:
    """
    Update StudentCourseStatus SCD Type 2 for (user_id, product_id).
    Returns True if a status change occurred, False if no-op (same status).
    """
    from app.models.student_course_status import StudentCourseStatus
    import datetime as _dt

    now = _dt.datetime.now(_dt.timezone.utc)

    current = (
        db.query(StudentCourseStatus)
        .filter(
            StudentCourseStatus.user_id == user_id,
            StudentCourseStatus.product_id == product_id,
            StudentCourseStatus.is_current == True,
        )
        .first()
    )

    if current and current.status == new_status:
        return False

    if current:
        current.valid_to = now
        current.is_current = False

    db.add(StudentCourseStatus(
        user_id=user_id,
        product_id=product_id,
        status=new_status,
        valid_from=now,
        valid_to=None,
        is_current=True,
        source=source,
    ))
    return True


@celery_app.task(name="sync_student_course_status", bind=True, max_retries=0)
def sync_student_course_status(self, product_id=None):
    """
    Reconcile student_course_status SCD2 table for all (or one) Hotmart products.

    For each active product:
    1. Fetch buyer statuses from Hotmart (6-year history)
    2. Match to User records in DB
    3. Update student_course_status (SCD Type 2)
    """
    import logging as _logging
    from app.integrations import hotmart
    from app.models.event import Event, EventStatus
    from app.models.user import User
    from app.models.product import Product

    _log = _logging.getLogger(__name__)
    db = SessionLocal()

    try:
        query = db.query(Product).filter(Product.is_active == True)
        if product_id:
            query = query.filter(Product.id == product_id)
        products = query.all()

        counters = {
            "synced": 0,
            "status_changes": 0,
            "skipped_no_phone": 0,
            "skipped_error": 0,
        }

        for product in products:
            try:
                buyer_statuses = hotmart.get_buyer_statuses(str(product.hotmart_product_id))
            except Exception as e:
                _log.error("Failed to fetch buyer statuses for product %s: %s", product.id, e)
                continue

            for email, biz_status in buyer_statuses.items():
                try:
                    user = db.query(User).filter(
                        (User.hotmart_id == email) | (User.email == email)
                    ).first()
                    if not user:
                        continue

                    changed = _update_scd2(user.id, product.id, biz_status, "hotmart_sync", db)
                    if changed:
                        counters["status_changes"] += 1

                    if not user.whatsapp_number:
                        counters["skipped_no_phone"] += 1

                    counters["synced"] += 1
                    db.commit()

                except Exception as e:
                    db.rollback()
                    _log.error("sync_student_course_status: error for %s / product %s: %s",
                               email, product.id, e)
                    counters["skipped_error"] += 1

        db.add(Event(
            type="course_status.sync_completed",
            payload={**counters, "product_id": product_id},
            status=EventStatus.PROCESSED,
        ))
        db.commit()

        return {"status": "ok", **counters}

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Hotmart Buyer Snapshot Sync
# ---------------------------------------------------------------------------

@celery_app.task(name="sync_hotmart_buyers", bind=True, max_retries=0)
def sync_hotmart_buyers(self, product_id=None):
    """
    Snapshot de todos os compradores Hotmart no banco local.

    Para cada produto ativo:
    1. Busca statuses de compradores via API Hotmart
    2. Faz UPSERT em hotmart_buyers (por email + hotmart_product_id)
    3. Resolve user_id pelo email (NULL se não tem conta na plataforma)
    4. Registra evento com contadores ao final
    """
    import logging as _logging
    import datetime as _dt
    from app.integrations import hotmart
    from app.models.event import Event, EventStatus
    from app.models.user import User
    from app.models.product import Product
    from app.models.hotmart_buyer import HotmartBuyer

    _log = _logging.getLogger(__name__)
    db = SessionLocal()

    try:
        query = db.query(Product).filter(Product.is_active == True)
        if product_id:
            query = query.filter(Product.id == product_id)
        products = query.all()

        counters = {
            "inserted": 0,
            "updated": 0,
            "total": 0,
            "errors": 0,
        }

        now = _dt.datetime.now(_dt.timezone.utc)

        for product in products:
            try:
                buyer_statuses = hotmart.get_buyer_statuses(str(product.hotmart_product_id))
            except Exception as e:
                _log.error("sync_hotmart_buyers: failed to fetch for product %s: %s", product.id, e)
                counters["errors"] += 1
                continue

            # Fetch contact info (name + phone) from /sales/users.
            # May not cover all historical buyers — fields stay nullable for those.
            contact_info = {}
            try:
                for buyer in hotmart.list_buyers_with_phone(str(product.hotmart_product_id)):
                    email_key = buyer.get("email", "")
                    if email_key:
                        contact_info[email_key] = {
                            "name": buyer.get("name", ""),
                            "phone": buyer.get("phone", ""),
                        }
            except Exception as e:
                _log.warning("sync_hotmart_buyers: failed to fetch contact info for product %s: %s",
                             product.id, e)

            for email, status in buyer_statuses.items():
                try:
                    user = db.query(User).filter(User.email == email).first()
                    user_id = user.id if user else None

                    existing = (
                        db.query(HotmartBuyer)
                        .filter(
                            HotmartBuyer.email == email,
                            HotmartBuyer.hotmart_product_id == str(product.hotmart_product_id),
                        )
                        .first()
                    )

                    contact = contact_info.get(email, {})

                    if existing:
                        existing.status = status
                        existing.user_id = user_id
                        existing.last_synced_at = now
                        if contact.get("name"):
                            existing.name = contact["name"]
                        if contact.get("phone"):
                            existing.phone = contact["phone"]
                        counters["updated"] += 1
                    else:
                        db.add(HotmartBuyer(
                            email=email,
                            name=contact.get("name", "") or None,
                            phone=contact.get("phone", "") or None,
                            hotmart_product_id=str(product.hotmart_product_id),
                            status=status,
                            user_id=user_id,
                            last_synced_at=now,
                        ))
                        counters["inserted"] += 1

                    counters["total"] += 1
                    db.commit()

                except Exception as e:
                    db.rollback()
                    _log.error("sync_hotmart_buyers: error for %s / product %s: %s",
                               email, product.id, e)
                    counters["errors"] += 1

        db.add(Event(
            type="hotmart_buyers.sync_completed",
            payload={**counters, "product_id": product_id},
            status=EventStatus.PROCESSED,
        ))
        db.commit()

        return {"status": "ok", **counters}

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(name="onboard_historical_buyers", bind=True, max_retries=0)
def onboard_historical_buyers(self):
    """
    Onboarding em lote de compradores históricos ativos sem conta na plataforma.

    Para cada email único em hotmart_buyers (status=Ativo, user_id=NULL):
    1. Cria User se não existir (email, name, whatsapp_number)
    2. Dispara lifecycle.transition("purchase_approved") → gera token + envia WhatsApp
    3. Atualiza hotmart_buyers.user_id em todos os rows do email

    Idempotente: rows com user_id preenchido são ignorados.
    """
    import logging as _logging
    import secrets as _secrets
    from collections import defaultdict

    from app.auth.security import hash_password
    from app.models.hotmart_buyer import HotmartBuyer
    from app.models.user import User, UserRole
    from app.models.event import Event, EventStatus
    from app.services.lifecycle import transition

    _log = _logging.getLogger(__name__)
    db = SessionLocal()

    counters = {"created": 0, "skipped": 0, "errors": 0, "total": 0}

    try:
        eligible = (
            db.query(HotmartBuyer)
            .filter(
                HotmartBuyer.status == "Ativo",
                HotmartBuyer.user_id == None,
            )
            .all()
        )

        # Dedup by email — keep all rows per email for user_id backfill
        by_email = defaultdict(list)
        for row in eligible:
            by_email[row.email].append(row)

        for email, rows in by_email.items():
            try:
                counters["total"] += 1

                primary = rows[0]

                user = db.query(User).filter(User.email == email).first()

                if user:
                    for row in rows:
                        row.user_id = user.id
                    db.commit()
                    counters["skipped"] += 1
                    continue

                user = User(
                    email=email,
                    whatsapp_number=primary.phone or None,
                    password_hash=hash_password(_secrets.token_urlsafe(16)),
                    role=UserRole.STUDENT,
                    lifecycle_status=None,
                )
                db.add(user)
                db.flush()

                transition(
                    db,
                    user,
                    trigger="purchase_approved",
                    hotmart_product_id=str(primary.hotmart_product_id),
                )

                for row in rows:
                    row.user_id = user.id

                db.commit()
                counters["created"] += 1

            except Exception as e:
                db.rollback()
                _log.error("onboard_historical_buyers: error for %s: %s", email, e)
                counters["errors"] += 1

        db.add(Event(
            type="hotmart_buyers.historical_onboarding_completed",
            payload=counters,
            status=EventStatus.PROCESSED,
        ))
        db.commit()

        return counters

    except Exception as e:
        db.rollback()
        _log.error("onboard_historical_buyers: fatal error: %s", e)
        return {"error": str(e)}

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Bulk messaging
# ---------------------------------------------------------------------------

def resolve_template(template: str, variables: Dict[str, str]) -> str:
    """Replace {nome}, {primeiro_nome}, {email}, {turma} in template."""
    result = template
    for key, value in variables.items():
        result = result.replace("{" + key + "}", value)
    return result


@celery_app.task(name="app.tasks.send_bulk_messages", soft_time_limit=7200, time_limit=7500)
def send_bulk_messages(
    campaign_id: int,
    message_template: str,
    only_pending: bool = False,
    variations: Optional[List[str]] = None,
    throttle_min: Optional[float] = None,
    throttle_max: Optional[float] = None,
) -> Dict[str, int]:
    """
    Send WhatsApp messages for a campaign with throttling and progressive DB updates.

    Args:
        campaign_id: ID of the MessageCampaign to process
        message_template: message with {nome}, {primeiro_nome}, {email}, {turma} placeholders
        only_pending: if True, only process recipients with status=pending (used for retry)
        variations: optional list of approved message variations; when provided, each
            recipient gets a randomly chosen variation instead of the template

    Returns:
        dict with sent, failed, total counts
    """
    import time as _time
    import random as _random
    import logging as _logging
    import secrets as _secrets
    from datetime import datetime, timedelta, timezone
    from app.integrations import evolution as _evo
    from app.database import SessionLocal
    from app.models.user import User
    from app.models.message_campaign import (
        MessageCampaign,
        MessageRecipient,
        CampaignStatus,
        RecipientStatus,
    )

    _log = _logging.getLogger(__name__)
    db = SessionLocal()

    try:
        campaign = db.query(MessageCampaign).filter(MessageCampaign.id == campaign_id).first()
        if not campaign:
            _log.error("send_bulk_messages: campaign %d not found", campaign_id)
            return {"sent": 0, "failed": 0, "total": 0}

        pending_recipients = (
            db.query(MessageRecipient)
            .filter(
                MessageRecipient.campaign_id == campaign_id,
                MessageRecipient.status == RecipientStatus.PENDING,
            )
            .all()
        )

        if not pending_recipients:
            _log.warning("send_bulk_messages: no pending recipients for campaign %d", campaign_id)
            return {"sent": 0, "failed": 0, "total": 0}

        sent = 0
        failed = 0

        # Use variations if provided, otherwise fall back to message_template
        _use_variations = bool(variations)
        has_token_var = "{token}" in message_template

        for i, recipient in enumerate(pending_recipients):
            name = recipient.name or ""
            variables = {
                "nome": name,
                "primeiro_nome": name.split("@")[0].split()[0] if name else "",
                "email": "",
                "turma": campaign.course_name or "",
            }

            # Token auto-management: generate/regenerate if template uses {token}
            if has_token_var:
                user = db.query(User).filter(User.id == recipient.user_id).first()
                if user:
                    now_check = datetime.now(timezone.utc)
                    needs_new_token = (
                        user.onboarding_token is None
                        or (user.onboarding_token_expires_at and user.onboarding_token_expires_at < now_check)
                    )
                    if needs_new_token:
                        user.onboarding_token = _secrets.token_urlsafe(6)[:8].upper()
                        user.onboarding_token_expires_at = now_check + timedelta(days=7)
                    variables["token"] = user.onboarding_token

            if _use_variations:
                chosen_template = _random.choice(variations)
            else:
                chosen_template = message_template
            message = resolve_template(chosen_template, variables)

            recipient.resolved_message = message

            success = _evo.send_message(recipient.phone, message)
            now = datetime.now(timezone.utc)

            if success:
                recipient.status = RecipientStatus.SENT
                recipient.sent_at = now
                campaign.sent_count += 1
                sent += 1
            else:
                recipient.status = RecipientStatus.FAILED
                recipient.error_message = "send_message returned False"
                campaign.failed_count += 1
                failed += 1

            db.commit()

            # Throttle between sends (configurable per campaign, defaults 15-25s)
            if i < len(pending_recipients) - 1:
                _tmin = throttle_min if throttle_min is not None else 15.0
                _tmax = throttle_max if throttle_max is not None else 25.0
                delay = _random.uniform(_tmin, _tmax)
                _log.info(
                    "Throttle: waiting %.1fs before next send (%d/%d)",
                    delay, i + 1, len(pending_recipients),
                )
                _time.sleep(delay)

        # Set final campaign status
        now = datetime.now(timezone.utc)
        if campaign.failed_count == 0:
            campaign.status = CampaignStatus.COMPLETED
        elif campaign.sent_count > 0:
            campaign.status = CampaignStatus.PARTIAL_FAILURE
        else:
            campaign.status = CampaignStatus.FAILED
        campaign.completed_at = now
        db.commit()

        _log.info(
            "send_bulk_messages: campaign=%d sent=%d failed=%d total=%d status=%s",
            campaign_id, sent, failed, len(pending_recipients), campaign.status.value,
        )
        return {"sent": sent, "failed": failed, "total": len(pending_recipients)}

    except Exception as e:
        db.rollback()
        _log.error("send_bulk_messages: fatal error for campaign %d: %s", campaign_id, e)
        try:
            campaign = db.query(MessageCampaign).filter(MessageCampaign.id == campaign_id).first()
            if campaign:
                campaign.status = CampaignStatus.FAILED
                campaign.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            _log.error("send_bulk_messages: failed to mark campaign %d as failed", campaign_id)
        return {"sent": 0, "failed": 0, "total": 0, "error": str(e)}

    finally:
        db.close()
