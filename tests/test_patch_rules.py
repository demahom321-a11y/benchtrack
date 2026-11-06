def create_test_item(client, name, sku, category_id):
    response = client.post(
        "/items/",
        json={
            "name": name,
            "sku": sku,
            "category_id": category_id,
            "quantity": 10,
            "minimum_stock": 2,
        },
    )

    assert response.status_code == 201
    return response.json()


def create_test_category(client, name):
    response = client.post(
        "/categories/",
        json={"name": name},
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_test_task(client, item_id, status="OPEN"):
    response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "Patch Rules Inspection",
            "status": status,
            "priority": "MEDIUM",
        },
    )

    assert response.status_code == 201
    return response.json()


def test_item_patch_duplicate_sku_is_rejected_without_changes(client):
    category_id = create_test_category(client, "Patch SKU Category")

    first_item = create_test_item(
        client,
        "First Drill",
        "PATCH-SKU-001",
        category_id,
    )

    create_test_item(
        client,
        "Second Drill",
        "PATCH-SKU-002",
        category_id,
    )

    response = client.patch(
        f"/items/{first_item['id']}",
        json={"sku": "PATCH-SKU-002"},
    )

    assert response.status_code == 409

    unchanged = client.get(f"/items/{first_item['id']}")

    assert unchanged.status_code == 200
    assert unchanged.json()["sku"] == "PATCH-SKU-001"


def test_item_patch_missing_category_is_rejected_without_changes(client):
    category_id = create_test_category(client, "Valid Patch Category")

    item = create_test_item(
        client,
        "Patch Drill",
        "PATCH-CATEGORY-001",
        category_id,
    )

    response = client.patch(
        f"/items/{item['id']}",
        json={"category_id": 999999},
    )

    assert response.status_code == 404

    unchanged = client.get(f"/items/{item['id']}")

    assert unchanged.status_code == 200
    assert unchanged.json()["category_id"] == category_id


def test_item_patch_negative_minimum_stock_is_rejected(client):
    category_id = create_test_category(client, "Minimum Stock Category")

    item = create_test_item(
        client,
        "Minimum Stock Drill",
        "PATCH-MINIMUM-001",
        category_id,
    )

    response = client.patch(
        f"/items/{item['id']}",
        json={"minimum_stock": -1},
    )

    assert response.status_code == 422

    unchanged = client.get(f"/items/{item['id']}")

    assert unchanged.status_code == 200
    assert unchanged.json()["minimum_stock"] == 2


def test_item_patch_zero_minimum_stock_is_allowed(client):
    category_id = create_test_category(client, "Zero Minimum Category")

    item = create_test_item(
        client,
        "Zero Minimum Drill",
        "PATCH-ZERO-001",
        category_id,
    )

    response = client.patch(
        f"/items/{item['id']}",
        json={"minimum_stock": 0},
    )

    assert response.status_code == 200
    assert response.json()["minimum_stock"] == 0


def test_maintenance_patch_invalid_status_is_rejected(client):
    category_id = create_test_category(client, "Invalid Status Category")

    item = create_test_item(
        client,
        "Status Drill",
        "PATCH-STATUS-001",
        category_id,
    )

    task = create_test_task(client, item["id"])

    response = client.patch(
        f"/maintenance-tasks/{task['id']}",
        json={"status": "INVALID"},
    )

    assert response.status_code == 422

    unchanged = client.get(
        f"/maintenance-tasks/{task['id']}"
    )

    assert unchanged.status_code == 200
    assert unchanged.json()["status"] == "OPEN"


def test_maintenance_patch_invalid_priority_is_rejected(client):
    category_id = create_test_category(client, "Invalid Priority Category")

    item = create_test_item(
        client,
        "Priority Drill",
        "PATCH-PRIORITY-001",
        category_id,
    )

    task = create_test_task(client, item["id"])

    response = client.patch(
        f"/maintenance-tasks/{task['id']}",
        json={"priority": "URGENT"},
    )

    assert response.status_code == 422

    unchanged = client.get(
        f"/maintenance-tasks/{task['id']}"
    )

    assert unchanged.status_code == 200
    assert unchanged.json()["priority"] == "MEDIUM"


def test_maintenance_patch_invalid_scheduled_date_is_rejected(client):
    category_id = create_test_category(client, "Invalid Date Category")

    item = create_test_item(
        client,
        "Date Drill",
        "PATCH-DATE-001",
        category_id,
    )

    task = create_test_task(client, item["id"])

    response = client.patch(
        f"/maintenance-tasks/{task['id']}",
        json={"scheduled_date": "2026-02-30"},
    )

    assert response.status_code == 422

    unchanged = client.get(
        f"/maintenance-tasks/{task['id']}"
    )

    assert unchanged.status_code == 200
    assert unchanged.json()["scheduled_date"] is None


def test_completed_at_is_preserved_when_completed_task_is_updated(client):
    category_id = create_test_category(client, "Completed Task Category")

    item = create_test_item(
        client,
        "Completed Drill",
        "PATCH-COMPLETED-001",
        category_id,
    )

    task = create_test_task(
        client,
        item["id"],
        status="COMPLETED",
    )

    original_completed_at = task["completed_at"]

    assert original_completed_at is not None

    response = client.patch(
        f"/maintenance-tasks/{task['id']}",
        json={"title": "Updated Completed Inspection"},
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["title"] == "Updated Completed Inspection"
    assert updated["status"] == "COMPLETED"
    assert updated["completed_at"] == original_completed_at