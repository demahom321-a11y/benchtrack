from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def concurrent_client(tmp_path):
    db_path = tmp_path / "unique_conflicts.db"
    engine = create_engine(
        URL.create(
            "sqlite",
            database=str(db_path),
        ),
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

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_category_name_conflict_is_detected_concurrently(concurrent_client):
    payload = {
        "name": "Shared Category",
        "description": "This name should only be accepted once.",
    }

    barrier = Barrier(2)

    def create_category():
        barrier.wait(timeout=5)
        return concurrent_client.post("/categories/", json=payload)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(create_category)
            for _ in range(2)
        ]
        responses = [
            future.result(timeout=15)
            for future in futures
        ]

    assert sorted(response.status_code for response in responses) == [201, 409]
    categories = concurrent_client.get("/categories/").json()
    assert sum(
        category["name"] == "Shared Category"
        for category in categories
    ) == 1


def test_item_sku_conflict_is_detected_concurrently(concurrent_client):
    category_response = concurrent_client.post(
        "/categories/",
        json={
            "name": "Tools",
            "description": "Shared test category.",
        },
    )
    assert category_response.status_code == 201, category_response.text
    category_id = category_response.json()["id"]

    payload = {
        "name": "Impact Driver",
        "sku": "SKU-UNIQUE-1",
        "description": "Adds a new product record.",
        "category_id": category_id,
        "quantity": 0,
        "minimum_stock": 0,
        "location": "Shelf A",
    }

    barrier = Barrier(2)

    def create_item():
        barrier.wait(timeout=5)
        return concurrent_client.post("/items/", json=payload)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(create_item)
            for _ in range(2)
        ]
        responses = [
            future.result(timeout=15)
            for future in futures
        ]

    assert sorted(response.status_code for response in responses) == [201, 409]
    result = concurrent_client.get(
        "/items/",
        params={"search": "SKU-UNIQUE-1"},
    ).json()
    assert result["total"] == 1


def test_category_unique_integrity_error_rolls_back(db_session):
    from fastapi import HTTPException

    from app.models.category import Category
    from app.routers.categories import _commit_category

    db_session.add(Category(name="Rollback Category"))
    db_session.commit()

    db_session.add(Category(name="Rollback Category"))

    with pytest.raises(HTTPException) as exc_info:
        _commit_category(db_session)

    assert exc_info.value.status_code == 409
    count = (
        db_session.query(Category)
        .filter(Category.name == "Rollback Category")
        .count()
    )
    assert count == 1
