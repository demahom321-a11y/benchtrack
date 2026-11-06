import pytest


def create_category(client):
    response = client.post(
        "/categories/",
        json={"name": "Boundary Category"},
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_item(client):
    category_id = create_category(client)

    response = client.post(
        "/items/",
        json={
            "name": "Boundary Drill",
            "sku": "BOUNDARY-001",
            "category_id": category_id,
            "quantity": 10,
            "minimum_stock": 2,
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.parametrize(
    ("name", "expected_status"),
    [
        ("AB", 201),
        ("C" * 100, 201),
        ("A", 422),
        ("D" * 101, 422),
    ],
)
def test_category_name_length_boundaries(
    client,
    name,
    expected_status,
):
    response = client.post(
        "/categories/",
        json={"name": name},
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    ("field", "value", "expected_status"),
    [
        ("name", "AB", 201),
        ("name", "N" * 150, 201),
        ("name", "A", 422),
        ("name", "N" * 151, 422),
        ("sku", "AB", 201),
        ("sku", "S" * 50, 201),
        ("sku", "S", 422),
        ("sku", "S" * 51, 422),
        ("location", "L" * 150, 201),
        ("location", "L" * 151, 422),
    ],
)
def test_item_text_length_boundaries(
    client,
    field,
    value,
    expected_status,
):
    category_id = create_category(client)

    payload = {
        "name": "Boundary Item",
        "sku": "BOUNDARY-ITEM-001",
        "category_id": category_id,
        "quantity": 10,
        "minimum_stock": 2,
    }

    payload[field] = value

    response = client.post("/items/", json=payload)

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    ("title", "expected_status"),
    [
        ("AB", 201),
        ("T" * 150, 201),
        ("A", 422),
        ("T" * 151, 422),
    ],
)
def test_maintenance_title_length_boundaries(
    client,
    title,
    expected_status,
):
    item_id = create_item(client)

    response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": title,
        },
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    ("field", "value", "expected_status"),
    [
        ("quantity", 0, 201),
        ("quantity", -1, 422),
        ("minimum_stock", 0, 201),
        ("minimum_stock", -1, 422),
    ],
)
def test_item_numeric_boundaries(
    client,
    field,
    value,
    expected_status,
):
    category_id = create_category(client)

    payload = {
        "name": "Numeric Boundary Item",
        "sku": "NUMERIC-001",
        "category_id": category_id,
        "quantity": 10,
        "minimum_stock": 2,
    }

    payload[field] = value

    response = client.post("/items/", json=payload)

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "invalid_date",
    [
        "not-a-date",
        "2026-02-30",
        "2026-13-01",
    ],
)
def test_maintenance_create_rejects_invalid_dates(
    client,
    invalid_date,
):
    item_id = create_item(client)

    response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "Date Boundary Inspection",
            "scheduled_date": invalid_date,
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("path", "params"),
    [
        (
            "/maintenance-tasks/",
            {"scheduled_from": "not-a-date"},
        ),
        (
            "/stock-movements/",
            {"date_from": "2026-02-30"},
        ),
    ],
)
def test_date_filters_reject_invalid_dates(
    client,
    path,
    params,
):
    response = client.get(path, params=params)

    assert response.status_code == 422


def test_stock_movement_rejects_reversed_date_range(client):
    response = client.get(
        "/stock-movements/",
        params={
            "date_from": "2026-12-02",
            "date_to": "2026-12-01",
        },
    )

    assert response.status_code == 400


def test_dashboard_accepts_maximum_recent_limit(client):
    response = client.get("/dashboard/?recent_limit=20")

    assert response.status_code == 200


def test_dashboard_rejects_recent_limit_above_maximum(client):
    response = client.get("/dashboard/?recent_limit=21")

    assert response.status_code == 422