from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional

from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.exercise import ExerciseList, ExerciseListItem, Exercise
from app.models.class_models import Class, ClassEnrollment, GroupMembership
from app.models.submission import Submission
from app.schemas.exercise_lists import (
    ExerciseListCreate,
    ExerciseListResponse,
    ExerciseListDetailResponse,
    AddExerciseToList,
    UpdateExercisePosition,
    RemoveExerciseConfirmation,
    ExerciseInList,
)

router = APIRouter(prefix="/exercise-lists", tags=["exercise-lists"])


@router.post("", response_model=ExerciseListResponse, status_code=status.HTTP_201_CREATED)
def create_exercise_list(
    list_data: ExerciseListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Create a new exercise list (professor only)"""
    # Verify class exists and user is professor
    class_ = db.query(Class).filter(Class.id == list_data.class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_.professor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to manage this class")

    # Verify group exists if specified
    if list_data.group_id is not None:
        from app.models.class_models import Group
        group = db.query(Group).filter(
            Group.id == list_data.group_id,
            Group.class_id == list_data.class_id
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found in this class")

    # Create list
    new_list = ExerciseList(
        title=list_data.title,
        class_id=list_data.class_id,
        group_id=list_data.group_id,
        opens_at=list_data.opens_at,
        closes_at=list_data.closes_at,
        late_penalty_percent_per_day=list_data.late_penalty_percent_per_day,
        auto_publish_grades=list_data.auto_publish_grades
    )
    db.add(new_list)
    db.commit()
    db.refresh(new_list)

    return new_list


@router.post("/{list_id}/exercises", response_model=ExerciseInList, status_code=status.HTTP_201_CREATED)
def add_exercise_to_list(
    list_id: int,
    exercise_data: AddExerciseToList,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Add an exercise to a list (professor only)"""
    # Get list and verify authorization
    exercise_list = db.query(ExerciseList).filter(ExerciseList.id == list_id).first()
    if not exercise_list:
        raise HTTPException(status_code=404, detail="Exercise list not found")

    class_ = db.query(Class).filter(Class.id == exercise_list.class_id).first()
    if class_.professor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to manage this list")

    # Verify exercise exists
    exercise = db.query(Exercise).filter(Exercise.id == exercise_data.exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Check if exercise already in list
    existing = db.query(ExerciseListItem).filter(
        ExerciseListItem.list_id == list_id,
        ExerciseListItem.exercise_id == exercise_data.exercise_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Exercise already in this list")

    # Adjust positions of existing items at or after the new position
    db.query(ExerciseListItem).filter(
        ExerciseListItem.list_id == list_id,
        ExerciseListItem.position >= exercise_data.position
    ).update({ExerciseListItem.position: ExerciseListItem.position + 1})

    # Create list item
    list_item = ExerciseListItem(
        list_id=list_id,
        exercise_id=exercise_data.exercise_id,
        position=exercise_data.position,
        weight=exercise_data.weight
    )
    db.add(list_item)
    db.commit()
    db.refresh(list_item)

    return ExerciseInList(
        list_item_id=list_item.id,
        exercise_id=exercise.id,
        exercise_title=exercise.title,
        position=list_item.position,
        weight=list_item.weight
    )


@router.patch("/{list_id}/exercises/{exercise_id}", response_model=ExerciseInList)
def reorder_exercise(
    list_id: int,
    exercise_id: int,
    position_data: UpdateExercisePosition,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Reorder an exercise within a list (professor only)"""
    # Get list and verify authorization
    exercise_list = db.query(ExerciseList).filter(ExerciseList.id == list_id).first()
    if not exercise_list:
        raise HTTPException(status_code=404, detail="Exercise list not found")

    class_ = db.query(Class).filter(Class.id == exercise_list.class_id).first()
    if class_.professor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to manage this list")

    # Get the list item
    list_item = db.query(ExerciseListItem).filter(
        ExerciseListItem.list_id == list_id,
        ExerciseListItem.exercise_id == exercise_id
    ).first()
    if not list_item:
        raise HTTPException(status_code=404, detail="Exercise not in this list")

    old_position = list_item.position
    new_position = position_data.position

    if old_position == new_position:
        # No change needed
        exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
        return ExerciseInList(
            list_item_id=list_item.id,
            exercise_id=exercise.id,
            exercise_title=exercise.title,
            position=list_item.position,
            weight=list_item.weight
        )

    # Adjust positions of other items
    if new_position < old_position:
        # Moving up: shift items down
        db.query(ExerciseListItem).filter(
            ExerciseListItem.list_id == list_id,
            ExerciseListItem.position >= new_position,
            ExerciseListItem.position < old_position
        ).update({ExerciseListItem.position: ExerciseListItem.position + 1})
    else:
        # Moving down: shift items up
        db.query(ExerciseListItem).filter(
            ExerciseListItem.list_id == list_id,
            ExerciseListItem.position <= new_position,
            ExerciseListItem.position > old_position
        ).update({ExerciseListItem.position: ExerciseListItem.position - 1})

    # Update item position
    list_item.position = new_position
    db.commit()
    db.refresh(list_item)

    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    return ExerciseInList(
        list_item_id=list_item.id,
        exercise_id=exercise.id,
        exercise_title=exercise.title,
        position=list_item.position,
        weight=list_item.weight
    )


@router.delete("/{list_id}/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_exercise_from_list(
    list_id: int,
    exercise_id: int,
    confirm: bool = Query(False, description="Set to true to confirm removal despite existing submissions"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Remove an exercise from a list (professor only)"""
    # Get list and verify authorization
    exercise_list = db.query(ExerciseList).filter(ExerciseList.id == list_id).first()
    if not exercise_list:
        raise HTTPException(status_code=404, detail="Exercise list not found")

    class_ = db.query(Class).filter(Class.id == exercise_list.class_id).first()
    if class_.professor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to manage this list")

    # Get the list item
    list_item = db.query(ExerciseListItem).filter(
        ExerciseListItem.list_id == list_id,
        ExerciseListItem.exercise_id == exercise_id
    ).first()
    if not list_item:
        raise HTTPException(status_code=404, detail="Exercise not in this list")

    # Check for existing submissions
    submission_count = db.query(Submission).join(ClassEnrollment).filter(
        Submission.exercise_id == exercise_id,
        ClassEnrollment.class_id == exercise_list.class_id
    ).count()

    if submission_count > 0 and not confirm:
        raise HTTPException(
            status_code=400,
            detail=f"{submission_count} submissions exist for this exercise. Set confirm=true to proceed."
        )

    # Remove the item
    position = list_item.position
    db.delete(list_item)

    # Adjust positions of items after the removed one
    db.query(ExerciseListItem).filter(
        ExerciseListItem.list_id == list_id,
        ExerciseListItem.position > position
    ).update({ExerciseListItem.position: ExerciseListItem.position - 1})

    db.commit()

    return None


@router.get("/classes/{class_id}/lists", response_model=List[ExerciseListDetailResponse])
def get_class_lists(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all exercise lists for a class"""
    # Verify access to class
    class_ = db.query(Class).filter(Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    is_professor = class_.professor_id == current_user.id
    enrollment = db.query(ClassEnrollment).filter(
        ClassEnrollment.class_id == class_id,
        ClassEnrollment.student_id == current_user.id
    ).first()

    if not (is_professor or enrollment):
        raise HTTPException(status_code=403, detail="Not authorized to view this class")

    # Get lists
    query = db.query(ExerciseList).filter(ExerciseList.class_id == class_id)

    # Filter by group if student
    if current_user.role == UserRole.STUDENT:
        # Get student's groups in this class
        student_groups = db.query(GroupMembership.group_id).filter(
            GroupMembership.student_id == current_user.id
        ).subquery()

        # Show lists with no group (class-wide) or student's groups
        query = query.filter(
            (ExerciseList.group_id.is_(None)) |
            (ExerciseList.group_id.in_(student_groups))
        )

    lists = query.all()

    # Build detailed response
    result = []
    for lst in lists:
        items = db.query(ExerciseListItem, Exercise).join(Exercise).filter(
            ExerciseListItem.list_id == lst.id
        ).order_by(ExerciseListItem.position).all()

        exercises = [
            ExerciseInList(
                list_item_id=item.id,
                exercise_id=exercise.id,
                exercise_title=exercise.title,
                position=item.position,
                weight=item.weight
            )
            for item, exercise in items
        ]

        result.append(
            ExerciseListDetailResponse(
                id=lst.id,
                title=lst.title,
                class_id=lst.class_id,
                group_id=lst.group_id,
                opens_at=lst.opens_at,
                closes_at=lst.closes_at,
                late_penalty_percent_per_day=lst.late_penalty_percent_per_day,
                auto_publish_grades=lst.auto_publish_grades,
                exercises=exercises
            )
        )

    return result
