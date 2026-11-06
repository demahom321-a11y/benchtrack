from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.category import Category
from app.models.item import Item
from app.models.stock_movement import StockMovement


@pytest.fixture
def stock_environment(tmp_path):
    db_path = tmp_path / "stock_concurrency.db"

    engine = create_engine(
        URL.create("sqlite", database=str(db_path)),
        connect_args={
            "check_same_thread": False,
            "timeout": 10,
        },
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    testing_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    with testing_session_local() as db:
        category = Category(name="Stock Concurrency")
        db.add(category)
        db.flush()

        item = Item(
            name="Concurrency Drill",
            sku="CONCURRENT-STOCK-001",
            category_id=category.id,
            quantity=10,
            minimum_stock=0,
        )
        db.add(item)
        db.commit()
        item_id = item.id

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client, testing_session_local, item_id
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()


def send_concurrently(client, item_id, movements):
    barrier = Barrier(len(movements))

    def send_movement(payload):
        barrier.wait(timeout=5)
        return client.post(
            f"/items/{item_id}/movements/",
            json=payload,
        )

    with ThreadPoolExecutor(max_workers=len(movements)) as executor:
        futures = [
            executor.submit(send_movement, payload)
            for payload in movements
        ]

        return [
            future.result(timeout=15)
            for future in futures
        ]


def read_stock_state(session_factory, item_id):
    with session_factory() as db:
        item = db.get(Item, item_id)

        movements = (
            db.query(StockMovement)
            .filter(StockMovement.item_id == item_id)
            .order_by(StockMovement.id.asc())
            .all()
        )

        return item.quantity, movements


def test_concurrent_stock_out_requests_are_safe(stock_environment):
    client, session_factory, item_id = stock_environment

    responses = send_concurrently(
        client,
        item_id,
        [
            {"movement_type": "OUT", "quantity": 7},
            {"movement_type": "OUT", "quantity": 7},
        ],
    )

    assert sorted(
        response.status_code for response in responses
    ) == [201, 400]

    quantity, movements = read_stock_state(session_factory, item_id)

    assert quantity == 3
    assert len(movements) == 1
    assert movements[0].previous_quantity == 10
    assert movements[0].new_quantity == 3


def test_concurrent_stock_in_requests_preserve_both_movements(
    stock_environment,
):
    client, session_factory, item_id = stock_environment

    responses = send_concurrently(
        client,
        item_id,
        [
            {"movement_type": "IN", "quantity": 5},
            {"movement_type": "IN", "quantity": 3},
        ],
    )

    assert [response.status_code for response in responses] == [201, 201]

    quantity, movements = read_stock_state(session_factory, item_id)

    assert quantity == 18
    assert len(movements) == 2
    assert all(movement.movement_type == "IN" for movement in movements)
    assert sum(movement.quantity for movement in movements) == 8

    assert movements[0].previous_quantity == 10
    assert movements[1].previous_quantity == movements[0].new_quantity
    assert movements[-1].new_quantity == quantity


def test_concurrent_in_and_out_movements_preserve_stock_history(
    stock_environment,
):
    client, session_factory, item_id = stock_environment

    responses = send_concurrently(
        client,
        item_id,
        [
            {"movement_type": "IN", "quantity": 5},
            {"movement_type": "OUT", "quantity": 7},
        ],
    )

    assert [response.status_code for response in responses] == [201, 201]

    quantity, movements = read_stock_state(session_factory, item_id)

    assert quantity == 8
    assert len(movements) == 2
    assert {movement.movement_type for movement in movements} == {
        "IN",
        "OUT",
    }

    assert movements[0].previous_quantity == 10
    assert movements[1].previous_quantity == movements[0].new_quantity
    assert movements[-1].new_quantity == quantity


def test_concurrent_stock_adjustments_preserve_movement_chain(
    stock_environment,
):
    client, session_factory, item_id = stock_environment

    responses = send_concurrently(
        client,
        item_id,
        [
            {"movement_type": "ADJUSTMENT", "quantity": 7},
            {"movement_type": "ADJUSTMENT", "quantity": 4},
        ],
    )

    assert [response.status_code for response in responses] == [201, 201]

    quantity, movements = read_stock_state(session_factory, item_id)

    assert len(movements) == 2
    assert all(
        movement.movement_type == "ADJUSTMENT"
        for movement in movements
    )

    assert movements[0].previous_quantity == 10
    assert movements[1].previous_quantity == movements[0].new_quantity

    assert all(
        movement.quantity == movement.new_quantity
        for movement in movements
    )

    assert quantity in {4, 7}
    assert movements[-1].new_quantity == quantity