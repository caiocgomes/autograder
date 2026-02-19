"""Integration tests for /products endpoints (app/routers/products.py)"""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from app.models.product import Product, ProductAccessRule, AccessRuleType


def _mock_product(id=1, name="Test Product", hotmart_product_id="HP-001", is_active=True):
    p = Mock(spec=Product)
    p.id = id
    p.name = name
    p.hotmart_product_id = hotmart_product_id
    p.is_active = is_active
    p.created_at = datetime(2024, 1, 1, 0, 0, 0)
    p.access_rules = []
    return p


def _mock_rule(id=1, product_id=1, rule_type=AccessRuleType.DISCORD_ROLE, rule_value="role-123"):
    r = Mock(spec=ProductAccessRule)
    r.id = id
    r.product_id = product_id
    r.rule_type = rule_type
    r.rule_value = rule_value
    r.created_at = datetime(2024, 1, 1, 0, 0, 0)
    return r


class TestCreateProduct:
    def test_admin_creates_product_returns_201(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.refresh = Mock(side_effect=lambda p: (
            setattr(p, "id", 1),
            setattr(p, "created_at", datetime(2024, 1, 1)),
            setattr(p, "is_active", True),
            setattr(p, "access_rules", []),
        ))

        response = client.post("/products", json={
            "name": "Python Bootcamp",
            "hotmart_product_id": "HP-001",
        })

        assert response.status_code == 201
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_duplicate_hotmart_product_id_returns_400(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        existing = _mock_product()
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        response = client.post("/products", json={
            "name": "Duplicate",
            "hotmart_product_id": "HP-001",
        })

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_non_admin_cannot_create_product(self, client_with_student):
        client, mock_db, student = client_with_student

        response = client.post("/products", json={
            "name": "Python Bootcamp",
            "hotmart_product_id": "HP-001",
        })

        assert response.status_code == 403

    def test_professor_cannot_create_product(self, client_with_professor):
        client, mock_db, professor = client_with_professor

        response = client.post("/products", json={
            "name": "Python Bootcamp",
            "hotmart_product_id": "HP-001",
        })

        assert response.status_code == 403


class TestListProducts:
    def test_admin_gets_list_of_products(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        products = [_mock_product(id=1), _mock_product(id=2, hotmart_product_id="HP-002")]
        mock_db.query.return_value.all.return_value = products

        response = client.get("/products")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_empty_list_returns_200(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.all.return_value = []

        response = client.get("/products")

        assert response.status_code == 200
        assert response.json() == []


class TestGetProduct:
    def test_existing_product_returns_200(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        product = _mock_product()
        mock_db.query.return_value.filter.return_value.first.return_value = product

        response = client.get("/products/1")

        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_nonexistent_product_returns_404(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/products/999")

        assert response.status_code == 404


class TestUpdateProduct:
    def test_patch_name_returns_200(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        product = _mock_product()
        mock_db.query.return_value.filter.return_value.first.return_value = product
        mock_db.refresh = Mock(side_effect=lambda p: setattr(p, "name", "Updated Name"))

        response = client.patch("/products/1", json={"name": "Updated Name"})

        assert response.status_code == 200
        mock_db.commit.assert_called_once()

    def test_patch_nonexistent_product_returns_404(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.patch("/products/999", json={"name": "Anything"})

        assert response.status_code == 404

    def test_patch_is_active_flag(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        product = _mock_product()
        mock_db.query.return_value.filter.return_value.first.return_value = product
        mock_db.refresh = Mock()

        response = client.patch("/products/1", json={"is_active": False})

        assert response.status_code == 200
        assert product.is_active is False


class TestDeleteProduct:
    def test_delete_existing_product_returns_204(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        product = _mock_product()
        mock_db.query.return_value.filter.return_value.first.return_value = product

        response = client.delete("/products/1")

        assert response.status_code == 204
        mock_db.delete.assert_called_once_with(product)
        mock_db.commit.assert_called_once()

    def test_delete_nonexistent_product_returns_404(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.delete("/products/999")

        assert response.status_code == 404


class TestProductAccessRules:
    def test_add_access_rule_returns_201(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        product = _mock_product()

        def side_effect_first():
            return product

        # First call: find product
        mock_db.query.return_value.filter.return_value.first.return_value = product
        rule = _mock_rule()
        mock_db.refresh = Mock(side_effect=lambda r: (
            setattr(r, "id", 1),
            setattr(r, "product_id", 1),
            setattr(r, "created_at", datetime(2024, 1, 1)),
        ))

        response = client.post("/products/1/rules", json={
            "rule_type": "discord_role",
            "rule_value": "role-abc",
        })

        assert response.status_code == 201
        mock_db.add.assert_called_once()

    def test_add_rule_to_nonexistent_product_returns_404(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.post("/products/999/rules", json={
            "rule_type": "discord_role",
            "rule_value": "role-abc",
        })

        assert response.status_code == 404

    def test_delete_access_rule_returns_204(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        rule = _mock_rule()
        mock_db.query.return_value.filter.return_value.first.return_value = rule

        response = client.delete("/products/1/rules/1")

        assert response.status_code == 204
        mock_db.delete.assert_called_once_with(rule)

    def test_delete_nonexistent_rule_returns_404(self, client_with_admin):
        client, mock_db, admin = client_with_admin
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.delete("/products/1/rules/999")

        assert response.status_code == 404
