from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.validators import strip_non_blank_text

MaintenanceStatus = Literal[
    "OPEN",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
]

MaintenancePriority = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]


class MaintenanceTaskCreate(BaseModel):
    item_id: int = Field(gt=0)
    title: str = Field(min_length=2, max_length=150)
    description: str | None = None

    status: MaintenanceStatus = "OPEN"
    priority: MaintenancePriority = "MEDIUM"

    scheduled_date: date | None = None

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value):
        return strip_non_blank_text(value)


class MaintenanceTaskUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    description: str | None = None

    status: MaintenanceStatus | None = None
    priority: MaintenancePriority | None = None

    scheduled_date: date | None = None

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value):
        return strip_non_blank_text(value)


class MaintenanceTaskResponse(BaseModel):
    id: int
    item_id: int
    title: str
    description: str | None

    status: MaintenanceStatus
    priority: MaintenancePriority

    scheduled_date: date | None
    completed_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaintenanceTaskListResponse(BaseModel):
    items: list[MaintenanceTaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int