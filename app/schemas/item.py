from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.validators import strip_non_blank_text


class ItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    sku: str = Field(min_length=2, max_length=50)
    description: str | None = None
    category_id: int = Field(gt=0)
    quantity: int = Field(default=0, ge=0)
    minimum_stock: int = Field(default=0, ge=0)
    location: str | None = Field(default=None, max_length=150)

    @field_validator("name", "sku", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return strip_non_blank_text(value)


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    sku: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = None
    category_id: int | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=0)
    minimum_stock: int | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=150)

    @field_validator("name", "sku", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return strip_non_blank_text(value)


class ItemResponse(BaseModel):
    id: int
    name: str
    sku: str
    description: str | None
    category_id: int
    quantity: int
    minimum_stock: int
    location: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int