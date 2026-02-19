"""
Auto-enrollment and auto-unenrollment by product.

Manual enrollments (via invite code) are NEVER touched by this service.
Only enrollments with enrollment_source=product are revoked on churn.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.class_models import ClassEnrollment, EnrollmentSource
from app.models.user import User

logger = logging.getLogger(__name__)


def auto_enroll_by_product(
    db: Session,
    student: User,
    class_id: int,
    product_id: Optional[int] = None,
) -> ClassEnrollment:
    """
    Enroll a student in a class as a product-driven enrollment.
    If already enrolled (manually or by product), does nothing and returns existing enrollment.
    """
    existing = db.query(ClassEnrollment).filter(
        ClassEnrollment.class_id == class_id,
        ClassEnrollment.student_id == student.id,
    ).first()

    if existing:
        logger.info(
            "Student %s already enrolled in class %s (source: %s)",
            student.id, class_id, existing.enrollment_source,
        )
        return existing

    enrollment = ClassEnrollment(
        class_id=class_id,
        student_id=student.id,
        enrollment_source=EnrollmentSource.PRODUCT,
    )
    db.add(enrollment)
    db.flush()
    logger.info("Auto-enrolled student %s in class %s via product", student.id, class_id)
    return enrollment


def auto_unenroll_by_product(db: Session, student: User, class_id: int) -> bool:
    """
    Remove a product-driven enrollment on churn.
    Manual enrollments are preserved.
    Returns True if unenrolled, False if enrollment was manual or not found.
    """
    enrollment = db.query(ClassEnrollment).filter(
        ClassEnrollment.class_id == class_id,
        ClassEnrollment.student_id == student.id,
        ClassEnrollment.enrollment_source == EnrollmentSource.PRODUCT,
    ).first()

    if not enrollment:
        logger.info(
            "No product enrollment found for student %s in class %s (manual enrollment preserved)",
            student.id, class_id,
        )
        return False

    db.delete(enrollment)
    db.flush()
    logger.info("Auto-unenrolled student %s from class %s (product enrollment)", student.id, class_id)
    return True
