import pytest
from sqlalchemy import event

from app.models.category import Category
from app.models.item import Item
from app.models.stock_movement import StockMovement
from app.routers.stock_movements import create_stock_movement
from app.schemas.stock_movement import StockMovementCreate


def test_failed_movement_flush_rolls_back_stock_and_history(db_session):
    category = Category(name="Atomicity Test")
    db_session.add(category)
    db_session.flush()

    item = Item(
        name="Atomicity Drill",
        sku="ATOMICITY-001",
        category_id=category.id,
        quantity=10,
        minimum_stock=0,
    )
    db_session.add(item)
    db_session.commit()

    item_id = item.id

    def fail_after_stock_movement_flush(session, flush_context):
        if any(
            isinstance(instance, StockMovement)
            for instance in session.new
        ):
            raise RuntimeError("Simulated failure after SQL flush.")

    event.listen(
        db_session,
        "after_flush",
        fail_after_stock_movement_flush,
    )

    try:
        with pytest.raises(
            RuntimeError,
            match="Simulated failure after SQL flush.",
        ):
            create_stock_movement(
                item_id=item_id,
                movement_data=StockMovementCreate(
                    movement_type="IN",
                    quantity=5,
                    notes="Atomicity failure test",
                ),
                db=db_session,
            )
    finally:
        event.remove(
            db_session,
            "after_flush",
            fail_after_stock_movement_flush,
        )

    db_session.expire_all()

    updated_item = db_session.get(Item, item_id)

    movement_count = (
        db_session.query(StockMovement)
        .filter(StockMovement.item_id == item_id)
        .count()
    )

    assert updated_item.quantity == 10
    assert movement_count == 0