from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import ast
import hashlib
import difflib
from datetime import datetime, timezone

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.exercise import Exercise, ExerciseList, ExerciseListItem, SubmissionType, GradingMode
from app.models.class_models import ClassEnrollment
from app.models.submission import Submission, SubmissionStatus, RubricScore
from app.schemas.submissions import (
    SubmissionCreate,
    SubmissionResponse,
    SubmissionListResponse,
    SubmissionDetailResponse,
    TestResultResponse,
    LLMEvaluationResponse,
    GradeResponse,
    RubricScoreResponse,
)
from app.celery_app import celery_app
from app.config import settings

router = APIRouter(prefix="/submissions", tags=["submissions"])

MAX_FILE_SIZE = settings.max_submission_file_size_mb * 1024 * 1024

ALLOWED_FILE_EXTENSIONS = {".pdf", ".xlsx", ".png", ".jpg", ".jpeg"}
EXTENSION_TO_CONTENT_TYPE = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def validate_python_syntax(code: str) -> Optional[str]:
    """
    Validate Python syntax without executing code.
    Returns error message if invalid, None if valid.
    """
    if not code or not code.strip():
        return "Code cannot be empty"

    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return f"Invalid Python code: {str(e)}"


def calculate_code_hash(code: str) -> str:
    """Calculate SHA256 hash of code for caching"""
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def check_submission_limit(db: Session, exercise: Exercise, student_id: int) -> None:
    """
    Check if student has exceeded submission limit.
    Raises HTTPException if limit exceeded.
    """
    if exercise.max_submissions is None:
        return

    submission_count = db.query(Submission).filter(
        Submission.exercise_id == exercise.id,
        Submission.student_id == student_id
    ).count()

    if submission_count >= exercise.max_submissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You have reached the maximum of {exercise.max_submissions} submissions"
        )


def check_deadline(db: Session, exercise_id: int, student_id: int) -> Optional[float]:
    """
    Check if submission is after deadline.
    Returns late penalty percentage to apply, or raises HTTPException if late submissions not allowed.
    Returns None if before deadline.
    """
    exercise_list_item = db.query(ExerciseListItem).join(ExerciseList).join(ClassEnrollment).filter(
        ExerciseListItem.exercise_id == exercise_id,
        ClassEnrollment.student_id == student_id
    ).first()

    if not exercise_list_item:
        return None

    exercise_list = exercise_list_item.exercise_list
    if not exercise_list.closes_at:
        return None

    now = datetime.now(timezone.utc)
    if now <= exercise_list.closes_at:
        return None

    if exercise_list.late_penalty_per_day is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deadline has passed"
        )

    days_late = (now - exercise_list.closes_at).total_seconds() / (24 * 3600)
    penalty = exercise_list.late_penalty_per_day * days_late
    return min(penalty, 100.0)


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    exercise_id: int = Form(...),
    code: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new submission (student only).
    Accepts either code as text or uploaded file, depending on exercise submission_type.
    """
    # Only students can submit
    if current_user.role not in [UserRole.STUDENT, UserRole.TA]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit"
        )

    # Validate exercise exists
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )

    # Check submission limit
    check_submission_limit(db, exercise, current_user.id)

    # Check deadline
    late_penalty = check_deadline(db, exercise_id, current_user.id)

    # Branch based on exercise submission_type
    if exercise.submission_type == SubmissionType.FILE_UPLOAD:
        # File upload submission
        if code and not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This exercise requires file upload, not code text"
            )
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File upload required for this exercise"
            )

        # Validate extension
        import os
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Accepted: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
            )

        # Read content
        file_content = await file.read()

        # Validate size
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds {settings.max_submission_file_size_mb}MB limit"
            )

        content_hash = hashlib.sha256(file_content).hexdigest()
        content_type = EXTENSION_TO_CONTENT_TYPE.get(ext, "application/octet-stream")

        # Create submission first to get ID
        submission = Submission(
            exercise_id=exercise_id,
            student_id=current_user.id,
            code=None,
            content_hash=content_hash,
            file_name=file.filename,
            file_size=len(file_content),
            content_type=content_type,
            status=SubmissionStatus.QUEUED,
        )
        db.add(submission)
        db.flush()  # Get ID

        # Save file to disk
        from app.services.file_storage import save_submission_file
        relative_path, _ = save_submission_file(exercise_id, submission.id, file, file_content)
        submission.file_path = relative_path

        db.commit()
        db.refresh(submission)

    else:
        # Code submission (existing behavior)
        if file and not code:
            # Allow .py file upload for code exercises (existing behavior)
            if not file.filename or not file.filename.endswith('.py'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This exercise requires code submission. Only .py files accepted."
                )
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File exceeds {settings.max_submission_file_size_mb}MB limit"
                )
            code = content.decode('utf-8')

        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code is required for this exercise"
            )

        # Validate Python syntax
        syntax_error = validate_python_syntax(code)
        if syntax_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=syntax_error
            )

        content_hash = calculate_code_hash(code)

        submission = Submission(
            exercise_id=exercise_id,
            student_id=current_user.id,
            code=code,
            content_hash=content_hash,
            status=SubmissionStatus.QUEUED,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

    # Dispatch to correct Celery task based on grading_mode
    if exercise.grading_mode == GradingMode.LLM_FIRST:
        celery_app.send_task(
            'app.tasks.grade_llm_first',
            args=[submission.id],
            kwargs={'late_penalty': late_penalty or 0.0}
        )
    else:
        celery_app.send_task(
            'app.tasks.execute_submission',
            args=[submission.id],
            kwargs={'late_penalty': late_penalty or 0.0}
        )

    return submission


@router.get("", response_model=List[SubmissionListResponse])
def list_submissions(
    exercise_id: Optional[int] = None,
    student_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List submissions with optional filtering.
    Students can only see their own submissions.
    Professors can see all submissions.
    """
    query = db.query(Submission)

    # Students can only see their own submissions
    if current_user.role == UserRole.STUDENT:
        query = query.filter(Submission.student_id == current_user.id)

    # Apply filters
    if exercise_id:
        query = query.filter(Submission.exercise_id == exercise_id)

    if student_id:
        if current_user.role not in [UserRole.PROFESSOR, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view other students' submissions"
            )
        query = query.filter(Submission.student_id == student_id)

    query = query.order_by(Submission.submitted_at.desc())

    return query.all()


@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get submission details"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this submission"
        )

    return submission


@router.get("/{submission_id}/results", response_model=SubmissionDetailResponse)
def get_submission_results(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get submission with test results, LLM feedback, and rubric scores"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this submission"
        )

    # Build rubric scores for llm-first exercises
    rubric_scores = None
    overall_feedback = None
    exercise = db.query(Exercise).filter(Exercise.id == submission.exercise_id).first()

    if exercise and exercise.grading_mode == GradingMode.LLM_FIRST:
        raw_scores = (
            db.query(RubricScore)
            .filter(RubricScore.submission_id == submission.id)
            .all()
        )
        if raw_scores:
            rubric_scores = []
            for rs in raw_scores:
                dim = rs.dimension
                rubric_scores.append(RubricScoreResponse(
                    dimension_name=dim.name,
                    dimension_weight=dim.weight,
                    score=rs.score,
                    feedback=rs.feedback,
                ))
        if submission.llm_evaluation:
            overall_feedback = submission.llm_evaluation.feedback

    return SubmissionDetailResponse(
        submission=submission,
        test_results=[TestResultResponse.model_validate(tr) for tr in submission.test_results] if submission.test_results else None,
        llm_evaluation=LLMEvaluationResponse.model_validate(submission.llm_evaluation) if submission.llm_evaluation else None,
        grade=GradeResponse.model_validate(submission.grade) if submission.grade else None,
        rubric_scores=rubric_scores,
        overall_feedback=overall_feedback,
    )


@router.get("/{submission_id}/status")
def get_submission_status(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Poll submission status for real-time updates."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this submission"
        )

    return {
        "id": submission.id,
        "status": submission.status,
        "error_message": submission.error_message,
        "submitted_at": submission.submitted_at
    }


@router.get("/{submission_id}/diff/{comparison_submission_id}")
def compare_submissions(
    submission_id: int,
    comparison_submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compare two code submissions and return a unified diff."""
    submission1 = db.query(Submission).filter(Submission.id == submission_id).first()
    submission2 = db.query(Submission).filter(Submission.id == comparison_submission_id).first()

    if not submission1 or not submission2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both submissions not found"
        )

    if current_user.role == UserRole.STUDENT:
        if submission1.student_id != current_user.id or submission2.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view these submissions"
            )

    # Diff only works for code submissions
    if not submission1.code or not submission2.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Diff is only available for code submissions"
        )

    diff_lines = list(difflib.unified_diff(
        submission1.code.splitlines(keepends=True),
        submission2.code.splitlines(keepends=True),
        fromfile=f"Submission {submission1.id} ({submission1.submitted_at})",
        tofile=f"Submission {submission2.id} ({submission2.submitted_at})",
        lineterm=''
    ))

    return {
        "submission1_id": submission1.id,
        "submission2_id": submission2.id,
        "submission1_date": submission1.submitted_at,
        "submission2_date": submission2.submitted_at,
        "diff": ''.join(diff_lines),
        "diff_lines": diff_lines
    }
