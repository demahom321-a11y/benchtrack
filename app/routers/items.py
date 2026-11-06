from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.models.item import Item
from app.models.maintenance_task import MaintenanceTask
from app.models.stock_movement import StockMovement
from app.schemas.item import (
    ItemCreate,
    ItemListResponse,
    ItemResponse,
    ItemUpdate,
)

router = APIRouter(
    prefix="/items",
    tags=["Items"],
)


def _commit_item(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "UNIQUE constraint failed: items.sku" not in str(exc.orig):
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An item with this SKU already exists.",
        ) from exc


@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "The specified category does not exist."},
        409: {"description": "An item with this SKU already exists."},
    },
)
def create_item(
    item_data: ItemCreate,
    db: Session = Depends(get_db),
):
    db.execute(text("BEGIN IMMEDIATE"))

    existing_item = (
        db.query(Item)
        .filter(Item.sku == item_data.sku)
        .first()
    )

    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An item with this SKU already exists.",
        )

    category = db.get(Category, item_data.category_id)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    new_item = Item(**item_data.model_dump())

    db.add(new_item)
    _commit_item(db)
    db.refresh(new_item)

    return new_item


@router.get(
    "/",
    response_model=ItemListResponse,
)
def get_items(
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=150,
        description="Search by item name, SKU, or description.",
    ),
    category_id: int | None = Query(default=None, gt=0),
    location: str | None = Query(
        default=None,
        min_length=1,
        max_length=150,
    ),
    low_stock: bool = Query(default=False),
    out_of_stock: bool = Query(default=False),
    sort_by: Literal[
        "id",
        "name",
        "sku",
        "quantity",
        "minimum_stock",
        "created_at",
        "updated_at",
    ] = Query(default="id"),
    order: Literal["asc", "desc"] = Query(default="asc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if low_stock and out_of_stock:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Choose either low_stock or out_of_stock, not both.",
        )

    query = db.query(Item)

    # Search by name, SKU, or description.
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Item.name.ilike(search_term),
                Item.sku.ilike(search_term),
                Item.description.ilike(search_term),
            )
        )

    # Filter by category.
    if category_id is not None:
        query = query.filter(Item.category_id == category_id)

    # Filter by storage location.
    if location:
        query = query.filter(
            Item.location.ilike(f"%{location.strip()}%")
        )

    # Filter by stock level.
    if low_stock:
        query = query.filter(
            Item.quantity <= Item.minimum_stock,
            Item.quantity > 0,
        )

    if out_of_stock:
        query = query.filter(Item.quantity == 0)

    # Count matching records before pagination.
    total = query.count()

    # Sort using an explicit list of allowed columns.
    sort_column = getattr(Item, sort_by)

    if order == "desc":
        query = query.order_by(
            sort_column.desc(),
            Item.id.desc(),
        )
    else:
        query = query.order_by(
            sort_column.asc(),
            Item.id.asc(),
        )

    # Apply pagination.
    items = (
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    total_pages = (total + page_size - 1) // page_size

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    responses={
        404: {"description": "Item not found."},
    },
)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = db.get(Item, item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found.",
        )

    return item


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    responses={
        400: {
            "description": "Stock quantity must be changed through stock movements."
        },
        404: {"description": "The item or specified category does not exist."},
        409: {"description": "An item with this SKU already exists."},
    },
)
def update_item(
    item_id: int,
    item_data: ItemUpdate,
    db: Session = Depends(get_db),
):
    update_data = item_data.model_dump(exclude_unset=True)

    if "sku" in update_data:
        db.execute(text("BEGIN IMMEDIATE"))

    item = db.get(Item, item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found.",
        )

    # Stock quantity must only be changed through stock movements.
    if "quantity" in update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use stock movements to change item quantity.",
        )

    # These database fields cannot be null.
    required_fields = ("name", "sku", "category_id", "minimum_stock")

    for field in required_fields:
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field} cannot be null.",
            )

    # Check SKU uniqueness.
    if "sku" in update_data:
        existing_item = (
            db.query(Item)
            .filter(
                Item.sku == update_data["sku"],
                Item.id != item_id,
            )
            .first()
        )

        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An item with this SKU already exists.",
            )

    # Check that the selected category exists.
    if "category_id" in update_data:
        category = db.get(Category, update_data["category_id"])

        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )

    for field, value in update_data.items():
        setattr(item, field, value)

    _commit_item(db)
    db.refresh(item)

    return item



@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Item not found."},
        409: {
            "description": "The item cannot be deleted while it has stock movement or maintenance history."
        },
    },
)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = db.get(Item, item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found.",
        )

    has_movements = (
        db.query(StockMovement.id)
        .filter(StockMovement.item_id == item_id)
        .first()
        is not None
    )

    if has_movements:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This item cannot be deleted because it has "
                "stock movement history."
            ),
        )

    has_maintenance_tasks = (
        db.query(MaintenanceTask.id)
        .filter(MaintenanceTask.item_id == item_id)
        .first()
        is not None
    )

    if has_maintenance_tasks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This item cannot be deleted because it has "
                "maintenance history."
            ),
        )

    db.delete(item)
    db.commit()
