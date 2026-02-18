from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
import os
import hashlib
from pathlib import Path

from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.exercise import Exercise, TestCase, ProgrammingLanguage, RubricDimension, GradingMode
from app.models.submission import Submission
from app.schemas.exercises import (
    ExerciseCreate,
    ExerciseUpdate,
    ExerciseResponse,
    TestCaseCreate,
    TestCaseResponse,
    DatasetUploadResponse,
)
from app.config import settings

router = APIRouter(prefix="/exercises", tags=["exercises"])

# File storage configuration
DATASETS_DIR = Path(settings.base_dir) / "datasets"
DATASETS_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
def create_exercise(
    exercise_data: ExerciseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Create a new exercise (professor only)"""
    # Create exercise
    new_exercise = Exercise(
        title=exercise_data.title,
        description=exercise_data.description,
        template_code=exercise_data.template_code,
        language=exercise_data.language,
        submission_type=exercise_data.submission_type,
        grading_mode=exercise_data.grading_mode,
        max_submissions=exercise_data.max_submissions,
        timeout_seconds=exercise_data.timeout_seconds,
        memory_limit_mb=exercise_data.memory_limit_mb,
        has_tests=exercise_data.has_tests,
        llm_grading_enabled=exercise_data.llm_grading_enabled,
        test_weight=exercise_data.test_weight,
        llm_weight=exercise_data.llm_weight,
        llm_grading_criteria=exercise_data.llm_grading_criteria,
        created_by=current_user.id,
        published=exercise_data.published,
        tags=exercise_data.tags
    )
    db.add(new_exercise)
    db.flush()  # Get ID before creating rubric dimensions

    # Create rubric dimensions for llm-first exercises
    if exercise_data.grading_mode == "llm_first" and exercise_data.rubric_dimensions:
        for dim_data in exercise_data.rubric_dimensions:
            dim = RubricDimension(
                exercise_id=new_exercise.id,
                name=dim_data.name,
                description=dim_data.description,
                weight=dim_data.weight,
                position=dim_data.position,
            )
            db.add(dim)

    db.commit()
    db.refresh(new_exercise)

    return new_exercise


@router.patch("/{exercise_id}", response_model=ExerciseResponse)
def update_exercise(
    exercise_id: int,
    exercise_data: ExerciseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Update an exercise (professor only)"""
    # Find exercise
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Check authorization
    if exercise.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to edit this exercise")

    # Check for existing submissions and warn (in production, this would be logged)
    submission_count = db.query(Submission).filter(
        Submission.exercise_id == exercise_id
    ).count()

    # Note: In a production system, we might return a warning in response headers
    # For now, we just proceed with the update

    # Update fields (exclude rubric_dimensions from direct setattr)
    update_data = exercise_data.model_dump(exclude_unset=True)
    rubric_dims_data = update_data.pop("rubric_dimensions", None)

    for field, value in update_data.items():
        setattr(exercise, field, value)

    # Validate grading configuration based on mode
    if exercise.grading_mode == GradingMode.TEST_FIRST:
        if 'has_tests' in update_data or 'llm_grading_enabled' in update_data:
            if not exercise.has_tests and not exercise.llm_grading_enabled:
                raise HTTPException(
                    status_code=400,
                    detail="At least one grading method required"
                )

        if 'test_weight' in update_data or 'llm_weight' in update_data:
            if abs(exercise.test_weight + exercise.llm_weight - 1.0) > 0.01:
                raise HTTPException(
                    status_code=400,
                    detail="Test weight and LLM weight must sum to 1.0"
                )

    # Handle rubric dimension updates (only if no submissions exist)
    if rubric_dims_data is not None and exercise.grading_mode == GradingMode.LLM_FIRST:
        if submission_count > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot modify rubric after submissions exist. Create a new exercise instead."
            )

        # Replace existing dimensions
        db.query(RubricDimension).filter(
            RubricDimension.exercise_id == exercise_id
        ).delete()

        for dim_data in rubric_dims_data:
            dim = RubricDimension(
                exercise_id=exercise_id,
                name=dim_data["name"],
                description=dim_data.get("description"),
                weight=dim_data["weight"],
                position=dim_data["position"],
            )
            db.add(dim)

    db.commit()
    db.refresh(exercise)

    return exercise


@router.get("", response_model=List[ExerciseResponse])
def list_exercises(
    professor_id: Optional[int] = None,
    tags: Optional[str] = None,
    published: Optional[bool] = None,
    language: Optional[ProgrammingLanguage] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List exercises with filtering"""
    query = db.query(Exercise)

    # Apply filters
    if professor_id is not None:
        query = query.filter(Exercise.created_by == professor_id)

    if tags is not None:
        # Simple tag search - in production, consider using array field or separate table
        tag_filters = [Exercise.tags.contains(tag.strip()) for tag in tags.split(',')]
        query = query.filter(or_(*tag_filters))

    if published is not None:
        query = query.filter(Exercise.published == published)
    elif current_user.role == UserRole.STUDENT:
        # Students only see published exercises
        query = query.filter(Exercise.published == True)

    if language is not None:
        query = query.filter(Exercise.language == language)

    # Professors can see all their exercises, students see only published
    if current_user.role == UserRole.STUDENT:
        query = query.filter(Exercise.published == True)

    exercises = query.order_by(Exercise.id.desc()).all()
    return exercises


@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(
    exercise_id: int,
    include_tests: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get exercise details"""
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Check access
    if current_user.role == UserRole.STUDENT and not exercise.published:
        raise HTTPException(status_code=403, detail="Exercise not available")

    # Include test cases if requested (non-hidden for students)
    if include_tests:
        if current_user.role == UserRole.STUDENT:
            # Students see non-hidden tests only
            test_cases = db.query(TestCase).filter(
                TestCase.exercise_id == exercise_id,
                TestCase.hidden == False
            ).all()
        else:
            # Professors see all tests
            test_cases = db.query(TestCase).filter(
                TestCase.exercise_id == exercise_id
            ).all()

        exercise.test_cases = test_cases

    return exercise


@router.post("/{exercise_id}/tests", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def add_test_case(
    exercise_id: int,
    test_data: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Add a test case to an exercise (professor only)"""
    # Check exercise exists and user is authorized
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    if exercise.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to edit this exercise")

    # Create test case
    test_case = TestCase(
        exercise_id=exercise_id,
        name=test_data.name,
        input_data=test_data.input_data,
        expected_output=test_data.expected_output,
        hidden=test_data.hidden
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    return test_case


@router.post("/{exercise_id}/datasets", response_model=DatasetUploadResponse)
async def upload_dataset(
    exercise_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Upload a dataset file for an exercise (professor only)"""
    # Check exercise exists and user is authorized
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    if exercise.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to edit this exercise")

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds {MAX_FILE_SIZE / (1024 * 1024):.0f}MB limit"
        )

    # Generate unique filename using hash
    file_hash = hashlib.sha256(content).hexdigest()[:16]
    file_extension = Path(file.filename).suffix
    unique_filename = f"exercise_{exercise_id}_{file_hash}{file_extension}"

    # Create exercise directory
    exercise_dir = DATASETS_DIR / f"exercise_{exercise_id}"
    exercise_dir.mkdir(exist_ok=True)

    # Save file
    file_path = exercise_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(content)

    # Generate URL (in production, this would be S3 URL or similar)
    file_url = f"/datasets/exercise_{exercise_id}/{unique_filename}"

    return DatasetUploadResponse(
        filename=unique_filename,
        file_url=file_url,
        size_bytes=file_size
    )


@router.patch("/{exercise_id}/publish", response_model=ExerciseResponse)
def toggle_publish(
    exercise_id: int,
    published: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Toggle exercise visibility (professor only)"""
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    if exercise.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to edit this exercise")

    exercise.published = published
    db.commit()
    db.refresh(exercise)

    return exercise
