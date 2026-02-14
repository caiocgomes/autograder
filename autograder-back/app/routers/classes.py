from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
import secrets
import string
import csv
import io

from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.class_models import Class, ClassEnrollment, Group, GroupMembership
from app.schemas.classes import (
    ClassCreate,
    ClassResponse,
    ClassDetailResponse,
    EnrollRequest,
    BulkEnrollRequest,
    BulkEnrollResponse,
    GroupCreate,
    GroupResponse,
    GroupMemberAdd,
    StudentInClass,
)

router = APIRouter(prefix="/classes", tags=["classes"])


def generate_invite_code(length: int = 8) -> str:
    """Generate a random invite code"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(
    class_data: ClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Create a new class (professor only)"""
    # Generate unique invite code
    invite_code = generate_invite_code()
    while db.query(Class).filter(Class.invite_code == invite_code).first():
        invite_code = generate_invite_code()

    # Create class
    new_class = Class(
        name=class_data.name,
        professor_id=current_user.id,
        invite_code=invite_code
    )
    db.add(new_class)
    db.commit()
    db.refresh(new_class)

    return new_class


@router.get("", response_model=List[ClassResponse])
def list_classes(
    archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List user's classes (filtered by role)"""
    query = db.query(Class).filter(Class.archived == archived)

    if current_user.role == UserRole.STUDENT:
        # Students see only classes they are enrolled in
        query = query.join(ClassEnrollment).filter(
            ClassEnrollment.student_id == current_user.id
        )
    else:
        # Professors/TAs see classes they teach
        query = query.filter(Class.professor_id == current_user.id)

    classes = query.order_by(Class.created_at.desc()).all()
    return classes


@router.get("/{class_id}", response_model=ClassDetailResponse)
def get_class_details(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get class details with roster"""
    class_ = db.query(Class).filter(Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    # Check access
    is_professor = class_.professor_id == current_user.id
    is_enrolled = db.query(ClassEnrollment).filter(
        ClassEnrollment.class_id == class_id,
        ClassEnrollment.student_id == current_user.id
    ).first() is not None

    if not (is_professor or is_enrolled):
        raise HTTPException(status_code=403, detail="Not authorized to view this class")

    # Get enrolled students
    enrollments = db.query(
        User.id, User.email, ClassEnrollment.enrolled_at
    ).join(ClassEnrollment).filter(
        ClassEnrollment.class_id == class_id
    ).all()

    students = [
        StudentInClass(id=e[0], email=e[1], enrolled_at=e[2])
        for e in enrollments
    ]

    # Get groups
    groups = db.query(Group).filter(Group.class_id == class_id).all()
    groups_with_count = []
    for group in groups:
        member_count = db.query(GroupMembership).filter(
            GroupMembership.group_id == group.id
        ).count()
        groups_with_count.append(
            GroupResponse(
                id=group.id,
                class_id=group.class_id,
                name=group.name,
                member_count=member_count
            )
        )

    return ClassDetailResponse(
        id=class_.id,
        name=class_.name,
        professor_id=class_.professor_id,
        invite_code=class_.invite_code,
        archived=class_.archived,
        created_at=class_.created_at,
        students=students,
        groups=groups_with_count
    )


@router.post("/{class_id}/enroll", status_code=status.HTTP_200_OK)
def enroll_in_class(
    class_id: int,
    enroll_data: EnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.STUDENT]))
):
    """Enroll student in class via invite code"""
    # Find class by invite code
    class_ = db.query(Class).filter(
        Class.id == class_id,
        Class.invite_code == enroll_data.invite_code
    ).first()

    if not class_:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    # Check if already enrolled
    existing = db.query(ClassEnrollment).filter(
        ClassEnrollment.class_id == class_id,
        ClassEnrollment.student_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this class")

    # Create enrollment
    enrollment = ClassEnrollment(
        class_id=class_id,
        student_id=current_user.id
    )
    db.add(enrollment)
    db.commit()

    return {"message": "Successfully enrolled in class", "class_id": class_id}


@router.post("/{class_id}/students", response_model=BulkEnrollResponse)
def bulk_enroll_students(
    class_id: int,
    bulk_data: BulkEnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Bulk import students via CSV (professor only)"""
    # Check class exists and user is professor
    class_ = db.query(Class).filter(Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this class")

    # Parse CSV
    try:
        csv_file = io.StringIO(bulk_data.csv_data)
        reader = csv.DictReader(csv_file)

        if 'email' not in reader.fieldnames or 'name' not in reader.fieldnames:
            raise HTTPException(
                status_code=400,
                detail="CSV must have 'email' and 'name' columns"
            )

        rows = list(reader)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")

    created_count = 0
    enrolled_count = 0
    skipped = []
    details = []

    for row in rows:
        email = row.get('email', '').strip()
        name = row.get('name', '').strip()

        if not email or '@' not in email:
            skipped.append(f"{email} (invalid email)")
            details.append({"email": email, "status": "skipped", "reason": "invalid email"})
            continue

        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Create new student account with temporary password
            temp_password = secrets.token_urlsafe(16)
            from app.auth.security import hash_password
            user = User(
                email=email,
                password_hash=hash_password(temp_password),
                role=UserRole.STUDENT
            )
            db.add(user)
            db.flush()  # Get user.id without committing
            created_count += 1
            details.append({"email": email, "status": "created", "temp_password": temp_password})

        # Enroll if not already enrolled
        existing_enrollment = db.query(ClassEnrollment).filter(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.student_id == user.id
        ).first()

        if not existing_enrollment:
            enrollment = ClassEnrollment(
                class_id=class_id,
                student_id=user.id
            )
            db.add(enrollment)
            enrolled_count += 1
            if user.id:  # Only update details if user was found
                for d in details:
                    if d.get('email') == email:
                        d['status'] = d.get('status', '') + '+enrolled'
                        break
                else:
                    details.append({"email": email, "status": "enrolled"})

    db.commit()

    return BulkEnrollResponse(
        created=created_count,
        enrolled=enrolled_count,
        skipped=skipped,
        details=details
    )


@router.delete("/{class_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def unenroll_student(
    class_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Remove student from class (professor only)"""
    # Check class exists and user is professor
    class_ = db.query(Class).filter(Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this class")

    # Find and delete enrollment
    enrollment = db.query(ClassEnrollment).filter(
        ClassEnrollment.class_id == class_id,
        ClassEnrollment.student_id == student_id
    ).first()

    if not enrollment:
        raise HTTPException(status_code=404, detail="Student not enrolled in this class")

    db.delete(enrollment)
    db.commit()

    return None


@router.post("/{class_id}/groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    class_id: int,
    group_data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Create a group within a class (professor only)"""
    # Check class exists and user is professor
    class_ = db.query(Class).filter(Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this class")

    # Create group
    group = Group(
        class_id=class_id,
        name=group_data.name
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    return GroupResponse(
        id=group.id,
        class_id=group.class_id,
        name=group.name,
        member_count=0
    )


@router.post("/groups/{group_id}/members", status_code=status.HTTP_200_OK)
def add_group_members(
    group_id: int,
    member_data: GroupMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Assign students to a group (professor only)"""
    # Get group and check authorization
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    class_ = db.query(Class).filter(Class.id == group.class_id).first()
    if class_.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this group")

    added = []
    skipped = []

    for student_id in member_data.student_ids:
        # Check if student is enrolled in class
        enrollment = db.query(ClassEnrollment).filter(
            ClassEnrollment.class_id == group.class_id,
            ClassEnrollment.student_id == student_id
        ).first()

        if not enrollment:
            skipped.append({"student_id": student_id, "reason": "not enrolled in class"})
            continue

        # Check if already in group
        existing = db.query(GroupMembership).filter(
            GroupMembership.group_id == group_id,
            GroupMembership.student_id == student_id
        ).first()

        if existing:
            skipped.append({"student_id": student_id, "reason": "already in group"})
            continue

        # Add to group
        membership = GroupMembership(
            group_id=group_id,
            student_id=student_id
        )
        db.add(membership)
        added.append(student_id)

    db.commit()

    return {
        "message": f"Added {len(added)} students to group",
        "added": added,
        "skipped": skipped
    }


@router.patch("/{class_id}/archive", response_model=ClassResponse)
def archive_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """Archive a class (professor only)"""
    # Check class exists and user is professor
    class_ = db.query(Class).filter(Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this class")

    class_.archived = True
    db.commit()
    db.refresh(class_)

    return class_


@router.get("/{class_id}/progress")
def get_class_progress(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROFESSOR, UserRole.ADMIN]))
):
    """
    Get completion statistics for all students in a class.
    Shows progress per student across all exercises.
    """
    from sqlalchemy import func, case
    from app.models.submission import Submission, Grade, SubmissionStatus

    # Check class exists and authorization
    class_ = db.query(Class).filter(Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    if current_user.role == UserRole.PROFESSOR and class_.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this class")

    # Get all students in class
    students = db.query(User).join(ClassEnrollment).filter(
        ClassEnrollment.class_id == class_id
    ).all()

    # Get exercise lists for this class
    from app.models.exercise import ExerciseList, ExerciseListItem
    exercise_lists = db.query(ExerciseList).filter(
        ExerciseList.class_id == class_id
    ).all()

    # Collect all unique exercises
    exercise_ids = set()
    for ex_list in exercise_lists:
        for item in ex_list.items:
            exercise_ids.add(item.exercise_id)

    total_exercises = len(exercise_ids)

    # Calculate stats per student
    progress_data = []

    for student in students:
        # Count completed submissions (with published grades)
        completed = db.query(func.count(func.distinct(Submission.exercise_id))).join(Grade).filter(
            Submission.student_id == student.id,
            Submission.exercise_id.in_(exercise_ids) if exercise_ids else False,
            Grade.published == True
        ).scalar() or 0

        # Count in-progress submissions (submitted but not graded)
        in_progress = db.query(func.count(func.distinct(Submission.exercise_id))).filter(
            Submission.student_id == student.id,
            Submission.exercise_id.in_(exercise_ids) if exercise_ids else False,
            Submission.status.in_([SubmissionStatus.QUEUED, SubmissionStatus.RUNNING])
        ).scalar() or 0

        # Calculate average score for published grades
        avg_score = db.query(func.avg(Grade.final_score)).join(Submission).filter(
            Submission.student_id == student.id,
            Submission.exercise_id.in_(exercise_ids) if exercise_ids else False,
            Grade.published == True
        ).scalar() or 0

        progress_data.append({
            "student_id": student.id,
            "student_email": student.email,
            "completed_exercises": completed,
            "in_progress_exercises": in_progress,
            "not_started": total_exercises - completed - in_progress,
            "total_exercises": total_exercises,
            "completion_percentage": (completed / total_exercises * 100) if total_exercises > 0 else 0,
            "average_score": round(avg_score, 2) if avg_score else 0
        })

    return {
        "class_id": class_id,
        "class_name": class_.name,
        "total_students": len(students),
        "total_exercises": total_exercises,
        "student_progress": progress_data
    }
