
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.models.item import Item
from app.models.maintenance_task import MaintenanceTask
from app.models.stock_movement import StockMovement

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/")
def get_dashboard(
    recent_limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    # 1. Inventory overview
    total_items = db.scalar(
        select(func.count(Item.id))
    ) or 0

    total_stock_units = db.scalar(
        select(func.coalesce(func.sum(Item.quantity), 0))
    ) or 0

    low_stock_items_count = db.scalar(
        select(func.count(Item.id)).where(
            Item.quantity > 0,
            Item.quantity <= Item.minimum_stock,
        )
    ) or 0

    out_of_stock_items_count = db.scalar(
        select(func.count(Item.id)).where(
            Item.quantity == 0
        )
    ) or 0

    # 2. Items grouped by category
    category_rows = db.execute(
        select(
            Category.id,
            Category.name,
            func.count(Item.id).label("items_count"),
            func.coalesce(func.sum(Item.quantity), 0).label(
                "stock_units"
            ),
        )
        .outerjoin(Item, Item.category_id == Category.id)
        .group_by(Category.id, Category.name)
        .order_by(Category.name)
    ).all()

    categories = [
        {
            "category_id": row.id,
            "name": row.name,
            "items_count": row.items_count,
            "stock_units": row.stock_units,
        }
        for row in category_rows
    ]

    # 3. Maintenance task counts
    maintenance_statuses: list[
        Literal["OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
    ] = [
        "OPEN",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    ]

    status_rows = db.execute(
        select(
            MaintenanceTask.status,
            func.count(MaintenanceTask.id),
        ).group_by(MaintenanceTask.status)
    ).all()

    maintenance_by_status = {
        task_status: 0 for task_status in maintenance_statuses
    }

    for task_status, count in status_rows:
        maintenance_by_status[task_status] = count

    total_maintenance_tasks = sum(
        maintenance_by_status.values()
    )

    high_priority_tasks_count = db.scalar(
        select(func.count(MaintenanceTask.id)).where(
            MaintenanceTask.priority == "HIGH",
            MaintenanceTask.status.in_(["OPEN", "IN_PROGRESS"]),
        )
    ) or 0

    # 4. Latest stock movements
    movement_rows = db.execute(
        select(
            StockMovement.id,
            StockMovement.item_id,
            Item.name.label("item_name"),
            StockMovement.movement_type,
            StockMovement.quantity,
            StockMovement.previous_quantity,
            StockMovement.new_quantity,
            StockMovement.notes,
            StockMovement.created_at,
        )
        .join(Item, Item.id == StockMovement.item_id)
        .order_by(
            StockMovement.created_at.desc(),
            StockMovement.id.desc(),
        )
        .limit(recent_limit)
    ).all()

    recent_movements = [
        {
            "id": row.id,
            "item_id": row.item_id,
            "item_name": row.item_name,
            "movement_type": row.movement_type,
            "quantity": row.quantity,
            "previous_quantity": row.previous_quantity,
            "new_quantity": row.new_quantity,
            "notes": row.notes,
            "created_at": row.created_at,
        }
        for row in movement_rows
    ]

    # 5. Latest maintenance tasks
    task_rows = db.execute(
        select(
            MaintenanceTask.id,
            MaintenanceTask.item_id,
            Item.name.label("item_name"),
            MaintenanceTask.title,
            MaintenanceTask.status,
            MaintenanceTask.priority,
            MaintenanceTask.scheduled_date,
            MaintenanceTask.completed_at,
            MaintenanceTask.created_at,
        )
        .join(Item, Item.id == MaintenanceTask.item_id)
        .order_by(
            MaintenanceTask.created_at.desc(),
            MaintenanceTask.id.desc(),
        )
        .limit(recent_limit)
    ).all()

    recent_maintenance_tasks = [
        {
            "id": row.id,
            "item_id": row.item_id,
            "item_name": row.item_name,
            "title": row.title,
            "status": row.status,
            "priority": row.priority,
            "scheduled_date": row.scheduled_date,
            "completed_at": row.completed_at,
            "created_at": row.created_at,
        }
        for row in task_rows
    ]

    return {
        "inventory": {
            "total_items": total_items,
            "total_stock_units": total_stock_units,
            "low_stock_items": low_stock_items_count,
            "out_of_stock_items": out_of_stock_items_count,
        },
        "categories": categories,
        "maintenance": {
            "total_tasks": total_maintenance_tasks,
            "by_status": maintenance_by_status,
            "high_priority_active_tasks": high_priority_tasks_count,
        },
        "recent_stock_movements": recent_movements,
        "recent_maintenance_tasks": recent_maintenance_tasks,
    }
