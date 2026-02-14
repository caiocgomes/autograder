"""Tests for class management endpoints (Task 16.2)"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from app.models.user import User, UserRole
from app.models.class_models import Class, ClassEnrollment


class TestCreateClass:
    def test_create_class_as_professor(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_db.refresh = Mock(side_effect=lambda c: (setattr(c, 'id', 1), setattr(c, 'invite_code', 'ABC123')))

        response = client.post("/classes", json={"name": "Data Science 101"})
        assert response.status_code == 201
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_class_as_student_forbidden(self, client_with_student):
        client, mock_db, student = client_with_student
        response = client.post("/classes", json={"name": "Test"})
        assert response.status_code == 403


class TestListClasses:
    def test_list_classes_professor(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_class = Mock(spec=Class)
        mock_class.id = 1
        mock_class.name = "Test Class"
        mock_class.professor_id = professor.id
        mock_class.invite_code = "ABC"
        mock_class.archived = False
        mock_class.created_at = "2024-01-01T00:00:00"
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_class]

        response = client.get("/classes")
        assert response.status_code == 200


class TestGetClass:
    def test_get_class_detail(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_class = Mock(spec=Class)
        mock_class.id = 1
        mock_class.name = "Test Class"
        mock_class.professor_id = professor.id
        mock_class.invite_code = "ABC"
        mock_class.archived = False
        mock_class.created_at = "2024-01-01T00:00:00"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_class

        # Mock students and groups queries
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []

        response = client.get("/classes/1")
        assert response.status_code == 200

    def test_get_nonexistent_class(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/classes/999")
        assert response.status_code == 404


class TestEnrollment:
    def test_enroll_with_invite_code(self, client_with_student):
        client, mock_db, student = client_with_student
        mock_class = Mock(spec=Class)
        mock_class.id = 1
        mock_class.invite_code = "VALID_CODE"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_class

        response = client.post("/classes/1/enroll", json={"invite_code": "VALID_CODE"})
        # Should succeed (200 or 201)
        assert response.status_code in (200, 201)

    def test_enroll_wrong_invite_code(self, client_with_student):
        client, mock_db, student = client_with_student
        mock_class = Mock(spec=Class)
        mock_class.id = 1
        mock_class.invite_code = "VALID_CODE"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_class

        response = client.post("/classes/1/enroll", json={"invite_code": "WRONG"})
        assert response.status_code in (400, 403)


class TestArchiveClass:
    def test_archive_class(self, client_with_professor):
        client, mock_db, professor = client_with_professor
        mock_class = Mock(spec=Class)
        mock_class.id = 1
        mock_class.professor_id = professor.id
        mock_class.archived = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_class

        response = client.patch("/classes/1/archive")
        assert response.status_code == 200
