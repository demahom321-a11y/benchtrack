
import csv
from io import StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.models.item import Item
from app.models.maintenance_task import MaintenanceTask
from app.models.stock_movement import StockMovement

router = APIRouter(
    prefix="/exports",
    tags=["Exports"],
)



def safe_csv_value(value):
    """Prevent spreadsheet formula injection in text cells."""
    if not isinstance(value, str):
        return value

    trimmed_value = value.lstrip(" ")

    dangerous_prefixes = (
        "=",
        "+",
        "-",
        "@",
        "\t",
        "\r",
        "\n",
    )

    if trimmed_value.startswith(dangerous_prefixes):
        return "'" + value

    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value

    return value



def create_csv_response(filename: str, headers: list, rows: list):
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(headers)

    for row in rows:
        writer.writerow([safe_csv_value(value) for value in row])

    content = output.getvalue().encode("utf-8-sig")

    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/items.csv")
def export_items(db: Session = Depends(get_db)):
    statement = (
        select(Item, Category.name)
        .join(Category, Category.id == Item.category_id)
        .order_by(Item.id.asc())
    )

    results = db.execute(statement).all()

    rows = [
        (
            item.id,
            item.name,
            item.sku,
            item.description,
            category_name,
            item.quantity,
            item.minimum_stock,
            item.location,
            item.created_at.isoformat() if item.created_at else "",
            item.updated_at.isoformat() if item.updated_at else "",
        )
        for item, category_name in results
    ]

    return create_csv_response(
        "benchtrack-inventory.csv",
        [
            "ID",
            "Name",
            "SKU",
            "Description",
            "Category",
            "Quantity",
            "Minimum Stock",
            "Location",
            "Created At",
            "Updated At",
        ],
        rows,
    )


@router.get("/stock-movements.csv")
def export_stock_movements(db: Session = Depends(get_db)):
    statement = (
        select(StockMovement, Item.name, Item.sku)
        .join(Item, Item.id == StockMovement.item_id)
        .order_by(
            StockMovement.created_at.desc(),
            StockMovement.id.desc(),
        )
    )

    results = db.execute(statement).all()

    rows = [
        (
            movement.id,
            movement.item_id,
            item_name,
            item_sku,
            movement.movement_type,
            movement.quantity,
            movement.previous_quantity,
            movement.new_quantity,
            movement.notes,
            movement.created_at.isoformat()
            if movement.created_at
            else "",
        )
        for movement, item_name, item_sku in results
    ]

    return create_csv_response(
        "benchtrack-stock-movements.csv",
        [
            "ID",
            "Item ID",
            "Item Name",
            "SKU",
            "Movement Type",
            "Movement Quantity",
            "Previous Quantity",
            "New Quantity",
            "Notes",
            "Created At",
        ],
        rows,
    )


@router.get("/maintenance-tasks.csv")
def export_maintenance_tasks(db: Session = Depends(get_db)):
    statement = (
        select(MaintenanceTask, Item.name, Item.sku)
        .join(Item, Item.id == MaintenanceTask.item_id)
        .order_by(
            MaintenanceTask.created_at.desc(),
            MaintenanceTask.id.desc(),
        )
    )

    results = db.execute(statement).all()

    rows = [
        (
            task.id,
            task.item_id,
            item_name,
            item_sku,
            task.title,
            task.description,
            task.status,
            task.priority,
            task.scheduled_date.isoformat()
            if task.scheduled_date
            else "",
            task.completed_at.isoformat()
            if task.completed_at
            else "",
            task.created_at.isoformat()
            if task.created_at
            else "",
            task.updated_at.isoformat()
            if task.updated_at
            else "",
        )
        for task, item_name, item_sku in results
    ]

    return create_csv_response(
        "benchtrack-maintenance-tasks.csv",
        [
            "ID",
            "Item ID",
            "Item Name",
            "SKU",
            "Title",
            "Description",
            "Status",
            "Priority",
            "Scheduled Date",
            "Completed At",
            "Created At",
            "Updated At",
        ],
        rows,
    )
