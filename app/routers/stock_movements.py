
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.item import Item
from app.models.stock_movement import StockMovement
from app.schemas.stock_movement import (
    StockMovementCreate,
    StockMovementResponse,
)

router = APIRouter(tags=["Stock Movements"])


@router.post(
    "/items/{item_id}/movements/",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Insufficient stock for this movement."},
        404: {"description": "Item not found."},
    },
)
def create_stock_movement(
    item_id: int,
    movement_data: StockMovementCreate,
    db: Session = Depends(get_db),
):
    try:
        # Acquire SQLite's write lock before reading the stock quantity.
        # This prevents two concurrent movements from using the same
        # outdated stock value.
        db.execute(text("BEGIN IMMEDIATE"))

        item = (
            db.query(Item)
            .filter(Item.id == item_id)
            .first()
        )

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found.",
            )

        previous_quantity = item.quantity

        if movement_data.movement_type == "IN":
            new_quantity = (
                previous_quantity + movement_data.quantity
            )

        elif movement_data.movement_type == "OUT":
            if movement_data.quantity > previous_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient stock for this movement.",
                )

            new_quantity = (
                previous_quantity - movement_data.quantity
            )

        else:
            # ADJUSTMENT quantity represents the actual counted stock.
            new_quantity = movement_data.quantity

        movement = StockMovement(
            item_id=item.id,
            movement_type=movement_data.movement_type,
            quantity=movement_data.quantity,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            notes=movement_data.notes,
        )

        item.quantity = new_quantity
        db.add(movement)

        db.commit()
        db.refresh(movement)

        return movement

    except Exception:
        db.rollback()
        raise


@router.get(
    "/items/{item_id}/movements/",
    response_model=list[StockMovementResponse],
    responses={
        404: {"description": "Item not found."},
    },
)
def get_item_movements(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = (
        db.query(Item)
        .filter(Item.id == item_id)
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found.",
        )

    return (
        db.query(StockMovement)
        .filter(StockMovement.item_id == item_id)
        .order_by(StockMovement.id.desc())
        .all()
    )


@router.get(
    "/stock-movements/",
    responses={
        400: {"description": "Invalid date range or movement type."},
    },
)
def get_all_stock_movements(
    search: str | None = Query(default=None, max_length=150),
    item_id: int | None = Query(default=None, gt=0),
    movement_type: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    sort_by: str = Query(
        default="created_at",
        pattern="^(id|created_at|quantity|movement_type)$",
    ),
    order: str = Query(
        default="desc",
        pattern="^(asc|desc)$",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from cannot be after date_to.",
        )

    query = (
        db.query(
            StockMovement,
            Item.name.label("item_name"),
        )
        .join(Item, StockMovement.item_id == Item.id)
    )

    if item_id is not None:
        query = query.filter(
            StockMovement.item_id == item_id
        )

    if movement_type is not None:
        movement_type = movement_type.strip().upper()

        if movement_type not in {"IN", "OUT", "ADJUSTMENT"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid movement type.",
            )

        query = query.filter(
            StockMovement.movement_type == movement_type
        )

    if search and search.strip():
        search_term = f"%{search.strip()}%"

        query = query.filter(
            (Item.name.ilike(search_term))
            | (Item.sku.ilike(search_term))
            | (StockMovement.notes.ilike(search_term))
        )

    if date_from is not None:
        start_datetime = datetime.combine(
            date_from,
            time.min,
        )

        query = query.filter(
            StockMovement.created_at >= start_datetime
        )

    if date_to is not None:
        end_datetime = datetime.combine(
            date_to + timedelta(days=1),
            time.min,
        )

        query = query.filter(
            StockMovement.created_at < end_datetime
        )

    total = query.count()

    sort_columns = {
        "id": StockMovement.id,
        "created_at": StockMovement.created_at,
        "quantity": StockMovement.quantity,
        "movement_type": StockMovement.movement_type,
    }

    sort_column = sort_columns[sort_by]

    if order == "asc":
        query = query.order_by(
            sort_column.asc(),
            StockMovement.id.asc(),
        )
    else:
        query = query.order_by(
            sort_column.desc(),
            StockMovement.id.desc(),
        )

    results = (
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []

    for movement, item_name in results:
        items.append(
            {
                "id": movement.id,
                "item_id": movement.item_id,
                "item_name": item_name,
                "movement_type": movement.movement_type,
                "quantity": movement.quantity,
                "previous_quantity": movement.previous_quantity,
                "new_quantity": movement.new_quantity,
                "notes": movement.notes,
                "created_at": movement.created_at,
            }
        )

    total_pages = (total + page_size - 1) // page_size

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
