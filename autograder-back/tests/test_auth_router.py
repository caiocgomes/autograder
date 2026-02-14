"""Tests for authentication endpoints (Task 16.1)"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.models.user import User, UserRole


class TestRegister:
    def test_register_success(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        # No existing user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        # Mock the refresh on new user
        mock_db.refresh = Mock(side_effect=lambda u: setattr(u, 'id', 1))

        with patch("app.routers.auth.hash_password", return_value="hashed"):
            with patch("app.routers.auth.create_access_token", return_value="access_token"):
                with patch("app.routers.auth.create_refresh_token", return_value="refresh_token"):
                    response = client.post("/auth/register", json={
                        "email": "new@test.com",
                        "password": "password123"
                    })

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_register_duplicate_email(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        existing_user = Mock(spec=User)
        existing_user.email = "existing@test.com"
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        response = client.post("/auth/register", json={
            "email": "existing@test.com",
            "password": "password123"
        })

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        response = client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "password123"
        })
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.password_hash = "hashed"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch("app.routers.auth.rate_limiter") as mock_rl:
            mock_rl.is_blocked.return_value = False
            with patch("app.routers.auth.verify_password", return_value=True):
                with patch("app.routers.auth.create_access_token", return_value="at"):
                    with patch("app.routers.auth.create_refresh_token", return_value="rt"):
                        response = client.post("/auth/login", json={
                            "email": "user@test.com",
                            "password": "password123"
                        })

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "at"
        assert data["refresh_token"] == "rt"

    def test_login_wrong_password(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_user = Mock(spec=User)
        mock_user.password_hash = "hashed"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch("app.routers.auth.rate_limiter") as mock_rl:
            mock_rl.is_blocked.return_value = False
            mock_rl.record_failed_attempt.return_value = 1
            mock_rl.max_attempts = 5
            with patch("app.routers.auth.verify_password", return_value=False):
                response = client.post("/auth/login", json={
                    "email": "user@test.com",
                    "password": "wrong"
                })

        assert response.status_code == 401

    def test_login_rate_limited(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        with patch("app.routers.auth.rate_limiter") as mock_rl:
            mock_rl.is_blocked.return_value = True
            mock_rl.window_minutes = 15
            response = client.post("/auth/login", json={
                "email": "user@test.com",
                "password": "password"
            })

        assert response.status_code == 429

    def test_login_user_not_found(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.routers.auth.rate_limiter") as mock_rl:
            mock_rl.is_blocked.return_value = False
            mock_rl.record_failed_attempt.return_value = 1
            mock_rl.max_attempts = 5
            with patch("app.routers.auth.verify_password", return_value=False):
                response = client.post("/auth/login", json={
                    "email": "nonexistent@test.com",
                    "password": "password"
                })

        assert response.status_code == 401


class TestRefresh:
    def test_refresh_success(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch("app.routers.auth.verify_token", return_value={"sub": 1, "type": "refresh"}):
            with patch("app.routers.auth.create_access_token", return_value="new_at"):
                with patch("app.routers.auth.create_refresh_token", return_value="new_rt"):
                    response = client.post("/auth/refresh", json={
                        "refresh_token": "old_refresh"
                    })

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new_at"

    def test_refresh_invalid_token(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        with patch("app.routers.auth.verify_token", return_value=None):
            response = client.post("/auth/refresh", json={
                "refresh_token": "invalid"
            })

        assert response.status_code == 401


class TestPasswordReset:
    def test_password_reset_request_always_202(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.routers.auth.create_access_token", return_value="token"):
            response = client.post("/auth/password-reset", json={
                "email": "anyone@test.com"
            })

        # Always returns 202 to prevent email enumeration
        assert response.status_code == 202

    def test_password_reset_confirm_success(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        mock_user = Mock(spec=User)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch("app.routers.auth.verify_token", return_value={"sub": 1, "purpose": "password_reset"}):
            with patch("app.routers.auth.hash_password", return_value="new_hash"):
                response = client.post("/auth/password-reset/confirm", json={
                    "token": "valid_token",
                    "new_password": "newpassword123"
                })

        assert response.status_code == 200

    def test_password_reset_confirm_invalid_token(self, unauthenticated_client):
        client, mock_db = unauthenticated_client
        with patch("app.routers.auth.verify_token", return_value=None):
            response = client.post("/auth/password-reset/confirm", json={
                "token": "invalid",
                "new_password": "newpassword123"
            })

        assert response.status_code == 400
