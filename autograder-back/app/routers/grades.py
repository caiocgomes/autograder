from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional, List
import csv
import io
from datetime import datetime

from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.submission import Submission, Grade, LLMEvaluation, TestResult
from app.models.exercise import Exercise
from app.models.class_models import Class, ClassEnrollment

router = APIRouter(prefix="/grades", tags=["grades"])


@router.get("")
def list_grades(
    class_id: Optional[int] = None,
    exercise_id: Optional[int] = None,
    student_id: Optional[int] = None,
    published_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN, UserRole.TA]))
):
    """
    List grades with optional filtering (professor/admin only).

    Args:
        class_id: Filter by class
        exercise_id: Filter by exercise
        student_id: Filter by student
        published_only: Only show published grades
    """
    # Build query joining grades with submissions
    query = db.query(
        Grade,
        Submission.student_id,
        Submission.exercise_id,
        Submission.submitted_at
    ).join(Submission)

    # Apply filters
    if class_id:
        # Join through exercise lists to filter by class
        # For now, just filter by exercise_id if provided
        pass

    if exercise_id:
        query = query.filter(Submission.exercise_id == exercise_id)

    if student_id:
        query = query.filter(Submission.student_id == student_id)

    if published_only:
        query = query.filter(Grade.published == True)

    # Order by most recent first
    query = query.order_by(Submission.submitted_at.desc())

    results = query.all()

    return [
        {
            "grade_id": grade.id,
            "submission_id": grade.submission_id,
            "student_id": student_id,
            "exercise_id": exercise_id,
            "test_score": grade.test_score,
            "llm_score": grade.llm_score,
            "final_score": grade.final_score,
            "late_penalty_applied": grade.late_penalty_applied,
            "published": grade.published,
            "submitted_at": submitted_at
        }
        for grade, student_id, exercise_id, submitted_at in results
    ]


@router.get("/me")
def get_my_grades(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get grades for the current user (students only see their own published grades).
    """
    query = db.query(
        Grade,
        Submission.exercise_id,
        Exercise.title,
        Submission.submitted_at
    ).join(Submission).join(Exercise).filter(
        Submission.student_id == current_user.id
    )

    # Students only see published grades
    if current_user.role == UserRole.STUDENT:
        query = query.filter(Grade.published == True)

    # Order by most recent first
    query = query.order_by(Submission.submitted_at.desc())

    results = query.all()

    return [
        {
            "grade_id": grade.id,
            "submission_id": grade.submission_id,
            "exercise_id": exercise_id,
            "exercise_title": title,
            "test_score": grade.test_score,
            "llm_score": grade.llm_score,
            "final_score": grade.final_score,
            "late_penalty_applied": grade.late_penalty_applied,
            "published": grade.published,
            "submitted_at": submitted_at
        }
        for grade, exercise_id, title, submitted_at in results
    ]


@router.post("/{grade_id}/publish")
def publish_grade(
    grade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """
    Manually publish a grade (professor only).
    Makes the grade visible to the student.
    """
    grade = db.query(Grade).filter(Grade.id == grade_id).first()

    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade not found"
        )

    # Check authorization (professor must own the exercise)
    submission = db.query(Submission).filter(Submission.id == grade.submission_id).first()
    exercise = db.query(Exercise).filter(Exercise.id == submission.exercise_id).first()

    if current_user.role == UserRole.PROFESSOR and exercise.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to publish this grade"
        )

    grade.published = True
    db.commit()

    return {
        "grade_id": grade.id,
        "published": grade.published,
        "message": "Grade published successfully"
    }


@router.patch("/{grade_id}")
def update_grade(
    grade_id: int,
    llm_score: Optional[float] = None,
    llm_feedback: Optional[str] = None,
    published: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """
    Edit grade details (professor only).
    Can modify LLM score/feedback and publishing status.
    """
    grade = db.query(Grade).filter(Grade.id == grade_id).first()

    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade not found"
        )

    # Check authorization
    submission = db.query(Submission).filter(Submission.id == grade.submission_id).first()
    exercise = db.query(Exercise).filter(Exercise.id == submission.exercise_id).first()

    if current_user.role == UserRole.PROFESSOR and exercise.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this grade"
        )

    # Update LLM score if provided
    if llm_score is not None:
        if llm_score < 0 or llm_score > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Score must be between 0 and 100"
            )

        grade.llm_score = llm_score

        # Recalculate final score
        composite_score = (
            exercise.test_weight * (grade.test_score or 0) +
            exercise.llm_weight * llm_score
        )
        grade.final_score = max(0, composite_score - grade.late_penalty_applied)

    # Update LLM feedback if provided
    if llm_feedback is not None:
        llm_eval = db.query(LLMEvaluation).filter(
            LLMEvaluation.submission_id == grade.submission_id
        ).first()

        if llm_eval:
            llm_eval.feedback = llm_feedback
        else:
            # Create new LLM evaluation record
            llm_eval = LLMEvaluation(
                submission_id=grade.submission_id,
                code_hash=submission.code_hash,
                feedback=llm_feedback,
                score=llm_score or 0,
                cached=False
            )
            db.add(llm_eval)

    # Update published status if provided
    if published is not None:
        grade.published = published

    db.commit()
    db.refresh(grade)

    return {
        "grade_id": grade.id,
        "test_score": grade.test_score,
        "llm_score": grade.llm_score,
        "final_score": grade.final_score,
        "published": grade.published
    }


@router.get("/export/class/{class_id}")
def export_class_grades(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """
    Export class grades as CSV (professor only).

    Returns a CSV file with student grades for all exercises in the class.
    """
    # Check class exists and professor has access
    class_obj = db.query(Class).filter(Class.id == class_id).first()

    if not class_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found"
        )

    if current_user.role == UserRole.PROFESSOR and class_obj.professor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to export grades for this class"
        )

    # Get all students in class
    students = db.query(User).join(ClassEnrollment).filter(
        ClassEnrollment.class_id == class_id
    ).all()

    # Get all exercises for the class (via exercise lists)
    # For now, get all published exercises
    # TODO: Filter by exercise lists assigned to this class

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Student ID", "Student Email", "Student Name", "Exercise ID", "Exercise Title", "Final Score", "Test Score", "LLM Score", "Late Penalty", "Submitted At"])

    # Get grades for each student
    for student in students:
        # Get best submission per exercise for this student
        submissions = db.query(
            Submission,
            Exercise,
            Grade
        ).join(Exercise).outerjoin(Grade).filter(
            Submission.student_id == student.id,
            Grade.published == True
        ).all()

        for submission, exercise, grade in submissions:
            if grade:
                writer.writerow([
                    student.id,
                    student.email,
                    student.email.split('@')[0],  # Simple name extraction
                    exercise.id,
                    exercise.title,
                    grade.final_score,
                    grade.test_score or "",
                    grade.llm_score or "",
                    grade.late_penalty_applied,
                    submission.submitted_at.isoformat()
                ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=class_{class_id}_grades_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )
