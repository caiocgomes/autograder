"""Tests for enrollment service (app/services/enrollment.py)"""
import pytest
from unittest.mock import Mock, MagicMock, call

from app.models.class_models import ClassEnrollment, EnrollmentSource
from app.models.user import User, UserRole


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    return db


@pytest.fixture
def student():
    user = Mock(spec=User)
    user.id = 42
    user.email = "student@test.com"
    user.role = UserRole.STUDENT
    return user


class TestAutoEnrollByProduct:
    def test_creates_new_enrollment_when_none_exists(self, mock_db, student):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.services.enrollment import auto_enroll_by_product
        result = auto_enroll_by_product(mock_db, student, class_id=10, product_id=5)

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

        added = mock_db.add.call_args[0][0]
        assert added.class_id == 10
        assert added.student_id == student.id
        assert added.enrollment_source == EnrollmentSource.PRODUCT

    def test_returns_existing_product_enrollment_without_duplicate(self, mock_db, student):
        existing = Mock(spec=ClassEnrollment)
        existing.enrollment_source = EnrollmentSource.PRODUCT
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        from app.services.enrollment import auto_enroll_by_product
        result = auto_enroll_by_product(mock_db, student, class_id=10, product_id=5)

        assert result is existing
        mock_db.add.assert_not_called()

    def test_returns_existing_manual_enrollment_without_duplicate(self, mock_db, student):
        existing = Mock(spec=ClassEnrollment)
        existing.enrollment_source = EnrollmentSource.MANUAL
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        from app.services.enrollment import auto_enroll_by_product
        result = auto_enroll_by_product(mock_db, student, class_id=10, product_id=5)

        assert result is existing
        mock_db.add.assert_not_called()

    def test_works_without_product_id(self, mock_db, student):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.services.enrollment import auto_enroll_by_product
        result = auto_enroll_by_product(mock_db, student, class_id=10)

        mock_db.add.assert_called_once()


class TestAutoUnenrollByProduct:
    def test_deletes_product_enrollment_and_returns_true(self, mock_db, student):
        product_enrollment = Mock(spec=ClassEnrollment)
        product_enrollment.enrollment_source = EnrollmentSource.PRODUCT
        mock_db.query.return_value.filter.return_value.first.return_value = product_enrollment

        from app.services.enrollment import auto_unenroll_by_product
        result = auto_unenroll_by_product(mock_db, student, class_id=10)

        assert result is True
        mock_db.delete.assert_called_once_with(product_enrollment)
        mock_db.flush.assert_called_once()

    def test_manual_enrollment_preserved_returns_false(self, mock_db, student):
        # The service filters on enrollment_source=PRODUCT, so no product enrollment found means return None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.services.enrollment import auto_unenroll_by_product
        result = auto_unenroll_by_product(mock_db, student, class_id=10)

        assert result is False
        mock_db.delete.assert_not_called()

    def test_no_enrollment_at_all_returns_false(self, mock_db, student):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.services.enrollment import auto_unenroll_by_product
        result = auto_unenroll_by_product(mock_db, student, class_id=99)

        assert result is False
        mock_db.delete.assert_not_called()

    def test_does_not_flush_when_nothing_deleted(self, mock_db, student):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.services.enrollment import auto_unenroll_by_product
        auto_unenroll_by_product(mock_db, student, class_id=10)

        mock_db.flush.assert_not_called()
