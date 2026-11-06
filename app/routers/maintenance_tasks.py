
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.item import Item
from app.models.maintenance_task import MaintenanceTask
from app.schemas.maintenance_task import (
    MaintenanceTaskCreate,
    MaintenanceTaskListResponse,
    MaintenanceTaskResponse,
    MaintenanceTaskUpdate,
)

router = APIRouter(
    prefix="/maintenance-tasks",
    tags=["Maintenance"],
)


@router.post(
    "/",
    response_model=MaintenanceTaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {
            "description": "The item associated with this maintenance task was not found."
        },
    },
)
def create_maintenance_task(
    task_data: MaintenanceTaskCreate,
    db: Session = Depends(get_db),
):
    item = db.get(Item, task_data.item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found.",
        )

    task = MaintenanceTask(**task_data.model_dump())

    if task.status == "COMPLETED":
        task.completed_at = datetime.now(UTC)

    try:
        db.add(task)
        db.commit()
        db.refresh(task)
    except Exception:
        db.rollback()
        raise

    return task


@router.get(
    "/",
    response_model=MaintenanceTaskListResponse,
)
def get_maintenance_tasks(
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=150,
        description="Search by task title, description, item name, or SKU.",
    ),
    status_filter: Literal[
        "OPEN",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    ] | None = Query(default=None, alias="status"),
    priority: Literal["LOW", "MEDIUM", "HIGH"] | None = None,
    item_id: int | None = Query(default=None, gt=0),
    scheduled_from: date | None = None,
    scheduled_to: date | None = None,
    sort_by: Literal[
        "id",
        "title",
        "status",
        "priority",
        "scheduled_date",
        "created_at",
        "updated_at",
        "completed_at",
    ] = Query(default="created_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if (
        scheduled_from is not None
        and scheduled_to is not None
        and scheduled_from > scheduled_to
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="scheduled_from cannot be later than scheduled_to.",
        )

    filters = []

    if search and search.strip():
        search_term = f"%{search.strip()}%"

        filters.append(
            or_(
                MaintenanceTask.title.ilike(search_term),
                MaintenanceTask.description.ilike(search_term),
                Item.name.ilike(search_term),
                Item.sku.ilike(search_term),
            )
        )

    if status_filter is not None:
        filters.append(
            MaintenanceTask.status == status_filter
        )

    if priority is not None:
        filters.append(
            MaintenanceTask.priority == priority
        )

    if item_id is not None:
        filters.append(
            MaintenanceTask.item_id == item_id
        )

    if scheduled_from is not None:
        filters.append(
            MaintenanceTask.scheduled_date >= scheduled_from
        )

    if scheduled_to is not None:
        filters.append(
            MaintenanceTask.scheduled_date <= scheduled_to
        )

    count_statement = (
        select(func.count(MaintenanceTask.id))
        .join(Item, Item.id == MaintenanceTask.item_id)
        .where(*filters)
    )

    total = db.scalar(count_statement) or 0

    statement = (
        select(MaintenanceTask)
        .join(Item, Item.id == MaintenanceTask.item_id)
        .where(*filters)
    )

    sort_column = getattr(MaintenanceTask, sort_by)

    if order == "asc":
        statement = statement.order_by(
            sort_column.asc(),
            MaintenanceTask.id.asc(),
        )
    else:
        statement = statement.order_by(
            sort_column.desc(),
            MaintenanceTask.id.desc(),
        )

    tasks = db.scalars(
        statement
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    total_pages = (total + page_size - 1) // page_size

    return {
        "items": tasks,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get(
    "/{task_id}",
    response_model=MaintenanceTaskResponse,
    responses={
        404: {"description": "Maintenance task not found."},
    },
)
def get_maintenance_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = db.get(MaintenanceTask, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance task not found.",
        )

    return task


@router.patch(
    "/{task_id}",
    response_model=MaintenanceTaskResponse,
    responses={
        404: {"description": "Maintenance task not found."},
    },
)
def update_maintenance_task(
    task_id: int,
    task_data: MaintenanceTaskUpdate,
    db: Session = Depends(get_db),
):
    task = db.get(MaintenanceTask, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance task not found.",
        )

    update_data = task_data.model_dump(exclude_unset=True)

    for field in ("title", "status", "priority"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field} cannot be null.",
            )

    old_status = task.status

    for field, value in update_data.items():
        setattr(task, field, value)

    if "status" in update_data:
        if task.status == "COMPLETED":
            if (
                old_status != "COMPLETED"
                or task.completed_at is None
            ):
                task.completed_at = datetime.now(UTC)
        else:
            task.completed_at = None

    try:
        db.commit()
        db.refresh(task)
    except Exception:
        db.rollback()
        raise

    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Maintenance task not found."},
    },
)
def delete_maintenance_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = db.get(MaintenanceTask, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance task not found.",
        )

    try:
        db.delete(task)
        db.commit()
    except Exception:
        db.rollback()
        raise
