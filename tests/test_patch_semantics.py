import pytest


def create_test_item(client):
    category_response = client.post(
        "/categories/",
        json={
            "name": "PATCH Test Category",
            "description": "Original category description",
        },
    )
    assert category_response.status_code == 201

    category_id = category_response.json()["id"]

    item_response = client.post(
        "/items/",
        json={
            "name": "PATCH Test Drill",
            "sku": "PATCH-DRILL-001",
            "description": "Original item description",
            "category_id": category_id,
            "quantity": 10,
            "minimum_stock": 2,
            "location": "Storage A",
        },
    )
    assert item_response.status_code == 201

    return category_id, item_response.json()["id"]


def create_test_task(client, item_id):
    response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "Original inspection",
            "description": "Original task description",
            "status": "COMPLETED",
            "priority": "HIGH",
            "scheduled_date": "2026-11-05",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_category_description_can_be_cleared_with_null(client):
    category_id, _ = create_test_item(client)

    response = client.patch(
        f"/categories/{category_id}",
        json={"description": None},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_item_optional_fields_can_be_cleared_with_null(client):
    _, item_id = create_test_item(client)

    response = client.patch(
        f"/items/{item_id}",
        json={
            "description": None,
            "location": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["location"] is None


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "sku",
        "category_id",
        "minimum_stock",
    ],
)
def test_item_required_fields_reject_null(client, field):
    _, item_id = create_test_item(client)
    original_response = client.get(f"/items/{item_id}")
    assert original_response.status_code == 200
    original_data = original_response.json()

    response = client.patch(
        f"/items/{item_id}",
        json={field: None},
    )

    assert response.status_code == 422

    unchanged = client.get(f"/items/{item_id}")
    assert unchanged.status_code == 200
    assert unchanged.json() == original_data


def test_item_quantity_null_is_rejected_without_changing_stock(client):
    _, item_id = create_test_item(client)

    response = client.patch(
        f"/items/{item_id}",
        json={"quantity": None},
    )

    assert response.status_code == 400

    unchanged = client.get(f"/items/{item_id}")

    assert unchanged.status_code == 200
    assert unchanged.json()["quantity"] == 10


def test_maintenance_optional_fields_can_be_cleared_with_null(client):
    _, item_id = create_test_item(client)
    task = create_test_task(client, item_id)

    response = client.patch(
        f"/maintenance-tasks/{task['id']}",
        json={
            "description": None,
            "scheduled_date": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["scheduled_date"] is None


def test_omitted_maintenance_fields_remain_unchanged(client):
    _, item_id = create_test_item(client)
    task = create_test_task(client, item_id)

    original_completed_at = task["completed_at"]

    response = client.patch(
        f"/maintenance-tasks/{task['id']}",
        json={"title": "Updated inspection"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "Updated inspection"
    assert data["description"] == "Original task description"
    assert data["status"] == "COMPLETED"
    assert data["priority"] == "HIGH"
    assert data["scheduled_date"] == "2026-11-05"
    assert data["completed_at"] == original_completed_at


def test_empty_patch_requests_leave_records_unchanged(client):
    category_id, item_id = create_test_item(client)
    task = create_test_task(client, item_id)

    category_response = client.patch(
        f"/categories/{category_id}",
        json={},
    )

    item_response = client.patch(
        f"/items/{item_id}",
        json={},
    )

    task_response = client.patch(
        f"/maintenance-tasks/{task['id']}",
        json={},
    )

    assert category_response.status_code == 200
    assert item_response.status_code == 200
    assert task_response.status_code == 200

    assert category_response.json()["name"] == "PATCH Test Category"
    assert item_response.json()["quantity"] == 10
    assert task_response.json()["status"] == "COMPLETED"
    assert task_response.json()["completed_at"] == task["completed_at"]