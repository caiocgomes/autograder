from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.product import AccessRuleType


class ProductAccessRuleCreate(BaseModel):
    rule_type: AccessRuleType
    rule_value: str = Field(..., min_length=1, max_length=255)


class ProductAccessRuleResponse(BaseModel):
    id: int
    product_id: int
    rule_type: AccessRuleType
    rule_value: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    hotmart_product_id: str = Field(..., min_length=1, max_length=255)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    hotmart_product_id: str
    is_active: bool
    created_at: datetime
    access_rules: List[ProductAccessRuleResponse] = []

    class Config:
        from_attributes = True
