"""
Product catalog CRUD - admin only.
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product, ProductAccessRule
from app.models.user import UserRole
from app.schemas.products import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductAccessRuleCreate,
    ProductAccessRuleResponse,
)
from app.auth.dependencies import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])

admin_only = require_role(UserRole.ADMIN)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    _: None = Depends(admin_only),
):
    existing = db.query(Product).filter(Product.hotmart_product_id == data.hotmart_product_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product already registered for this Hotmart ID")

    product = Product(name=data.name, hotmart_product_id=data.hotmart_product_id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=List[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    _: None = Depends(admin_only),
):
    return db.query(Product).all()


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(admin_only),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(admin_only),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.name is not None:
        product.name = data.name
    if data.is_active is not None:
        product.is_active = data.is_active

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(admin_only),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()


@router.post("/{product_id}/rules", response_model=ProductAccessRuleResponse, status_code=status.HTTP_201_CREATED)
def add_access_rule(
    product_id: int,
    data: ProductAccessRuleCreate,
    db: Session = Depends(get_db),
    _: None = Depends(admin_only),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    rule = ProductAccessRule(
        product_id=product_id,
        rule_type=data.rule_type,
        rule_value=data.rule_value,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{product_id}/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_access_rule(
    product_id: int,
    rule_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(admin_only),
):
    rule = db.query(ProductAccessRule).filter(
        ProductAccessRule.id == rule_id,
        ProductAccessRule.product_id == product_id,
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Access rule not found")
    db.delete(rule)
    db.commit()
