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
from app.models.exercise import Exercise, ExerciseList, ExerciseListItem
from app.models.class_models import ClassEnrollment
from app.models.submission import Submission, SubmissionStatus
from app.schemas.submissions import (
    SubmissionCreate,
    SubmissionResponse,
    SubmissionListResponse,
    SubmissionDetailResponse,
    TestResultResponse,
    LLMEvaluationResponse,
    GradeResponse,
)
from app.celery_app import celery_app

router = APIRouter(prefix="/submissions", tags=["submissions"])

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB


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
    # Find the exercise list containing this exercise for the student
    exercise_list_item = db.query(ExerciseListItem).join(ExerciseList).join(ClassEnrollment).filter(
        ExerciseListItem.exercise_id == exercise_id,
        ClassEnrollment.student_id == student_id
    ).first()

    if not exercise_list_item:
        # Exercise not in any list, no deadline check
        return None

    exercise_list = exercise_list_item.exercise_list
    if not exercise_list.closes_at:
        # No deadline set
        return None

    now = datetime.now(timezone.utc)
    if now <= exercise_list.closes_at:
        # Before deadline
        return None

    # After deadline
    if exercise_list.late_penalty_per_day is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deadline has passed"
        )

    # Calculate days late
    days_late = (now - exercise_list.closes_at).total_seconds() / (24 * 3600)
    penalty = exercise_list.late_penalty_per_day * days_late
    return min(penalty, 100.0)  # Cap at 100%


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
    Accepts either code as text or uploaded file.
    """
    # Only students can submit
    if current_user.role not in [UserRole.STUDENT, UserRole.TA]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit code"
        )

    # Validate input: must provide either code or file
    if not code and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either code text or file upload"
        )

    if code and file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either code text or file upload, not both"
        )

    # Read code from file if provided
    if file:
        # Validate file extension
        if not file.filename.endswith('.py'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .py files accepted"
            )

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File exceeds 1MB limit"
            )

        code = content.decode('utf-8')

    # Validate exercise exists
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )

    # Validate Python syntax
    syntax_error = validate_python_syntax(code)
    if syntax_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=syntax_error
        )

    # Check submission limit
    check_submission_limit(db, exercise, current_user.id)

    # Check deadline and calculate penalty if applicable
    late_penalty = check_deadline(db, exercise_id, current_user.id)

    # Calculate code hash for LLM caching
    code_hash = calculate_code_hash(code)

    # Create submission record
    submission = Submission(
        exercise_id=exercise_id,
        student_id=current_user.id,
        code=code,
        code_hash=code_hash,
        status=SubmissionStatus.QUEUED
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Enqueue submission task to Celery
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
        # Only professors can filter by student_id
        if current_user.role not in [UserRole.PROFESSOR, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view other students' submissions"
            )
        query = query.filter(Submission.student_id == student_id)

    # Order by most recent first
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

    # Check authorization
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
    """Get submission with test results and feedback"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    # Check authorization
    if current_user.role == UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this submission"
        )

    return SubmissionDetailResponse(
        submission=submission,
        test_results=[TestResultResponse.model_validate(tr) for tr in submission.test_results],
        llm_evaluation=LLMEvaluationResponse.model_validate(submission.llm_evaluation) if submission.llm_evaluation else None,
        grade=GradeResponse.model_validate(submission.grade) if submission.grade else None
    )


@router.get("/{submission_id}/status")
def get_submission_status(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Poll submission status for real-time updates.
    Returns lightweight status response for polling.
    """
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    # Check authorization
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
    """
    Compare two submissions and return a unified diff.
    Both submissions must belong to the current user (for students).
    """
    # Get both submissions
    submission1 = db.query(Submission).filter(Submission.id == submission_id).first()
    submission2 = db.query(Submission).filter(Submission.id == comparison_submission_id).first()

    if not submission1 or not submission2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both submissions not found"
        )

    # Check authorization
    if current_user.role == UserRole.STUDENT:
        if submission1.student_id != current_user.id or submission2.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view these submissions"
            )

    # Generate unified diff
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
