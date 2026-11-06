

def create_item(client, name, sku, quantity, minimum_stock, category_name):
    categories_response = client.get("/categories/")
    assert categories_response.status_code == 200

    categories = categories_response.json()

    existing_category = next(
        (
            category
            for category in categories
            if category["name"] == category_name
        ),
        None,
    )

    if existing_category:
        category_id = existing_category["id"]
    else:
        category_response = client.post(
            "/categories/",
            json={"name": category_name},
        )
        assert category_response.status_code == 201
        category_id = category_response.json()["id"]

    item_response = client.post(
        "/items/",
        json={
            "name": name,
            "sku": sku,
            "category_id": category_id,
            "quantity": quantity,
            "minimum_stock": minimum_stock,
            "location": "Storage A",
        },
    )

    assert item_response.status_code == 201
    return item_response.json()["id"]



def test_dashboard_empty_database(client):
    response = client.get("/dashboard/")

    assert response.status_code == 200
    data = response.json()

    assert data["inventory"]["total_items"] == 0
    assert data["inventory"]["total_stock_units"] == 0
    assert data["inventory"]["low_stock_items"] == 0
    assert data["inventory"]["out_of_stock_items"] == 0
    assert data["categories"] == []
    assert data["maintenance"]["total_tasks"] == 0
    assert data["maintenance"]["high_priority_active_tasks"] == 0
    assert data["recent_stock_movements"] == []
    assert data["recent_maintenance_tasks"] == []


def test_dashboard_inventory_statistics(client):
    create_item(
        client, "Drill", "DRILL-001", 10, 3, "Tools"
    )
    create_item(
        client, "Hammer", "HAMMER-001", 2, 5, "Tools"
    )
    create_item(
        client, "Saw", "SAW-001", 0, 2, "Equipment"
    )

    response = client.get("/dashboard/")

    assert response.status_code == 200
    inventory = response.json()["inventory"]

    assert inventory["total_items"] == 3
    assert inventory["total_stock_units"] == 12
    assert inventory["low_stock_items"] == 1
    assert inventory["out_of_stock_items"] == 1


def test_dashboard_categories_grouping(client):
    create_item(
        client, "Drill", "DRILL-001", 10, 2, "Tools"
    )
    create_item(
        client, "Hammer", "HAMMER-001", 5, 2, "Tools"
    )
    create_item(
        client, "Saw", "SAW-001", 4, 1, "Equipment"
    )

    response = client.get("/dashboard/")

    assert response.status_code == 200
    categories = response.json()["categories"]

    assert len(categories) == 2

    tools = next(
        category for category in categories
        if category["name"] == "Tools"
    )

    assert tools["items_count"] == 2
    assert tools["stock_units"] == 15


def test_dashboard_includes_empty_categories(client):
    category_response = client.post(
        "/categories/",
        json={"name": "Unused Category"},
    )
    assert category_response.status_code == 201

    response = client.get("/dashboard/")

    assert response.status_code == 200

    category = next(
        category for category in response.json()["categories"]
        if category["name"] == "Unused Category"
    )

    assert category["items_count"] == 0
    assert category["stock_units"] == 0


def test_dashboard_maintenance_statistics(client):
    item_id = create_item(
        client, "Drill", "DRILL-001", 10, 2, "Tools"
    )

    tasks = [
        ("Open task", "OPEN", "HIGH"),
        ("Progress task", "IN_PROGRESS", "HIGH"),
        ("Completed task", "COMPLETED", "HIGH"),
        ("Cancelled task", "CANCELLED", "MEDIUM"),
    ]

    for title, task_status, priority in tasks:
        response = client.post(
            "/maintenance-tasks/",
            json={
                "item_id": item_id,
                "title": title,
                "status": task_status,
                "priority": priority,
            },
        )
        assert response.status_code == 201

    response = client.get("/dashboard/")

    assert response.status_code == 200
    maintenance = response.json()["maintenance"]

    assert maintenance["total_tasks"] == 4
    assert maintenance["by_status"] == {
        "OPEN": 1,
        "IN_PROGRESS": 1,
        "COMPLETED": 1,
        "CANCELLED": 1,
    }
    assert maintenance["high_priority_active_tasks"] == 2


def test_dashboard_recent_limit(client):
    item_id = create_item(
        client, "Drill", "DRILL-001", 10, 2, "Tools"
    )

    for index in range(3):
        response = client.post(
            f"/items/{item_id}/movements/",
            json={
                "movement_type": "IN",
                "quantity": 1,
                "notes": f"Movement {index}",
            },
        )
        assert response.status_code == 201

    response = client.get("/dashboard/?recent_limit=2")

    assert response.status_code == 200
    assert len(response.json()["recent_stock_movements"]) == 2


def test_dashboard_invalid_recent_limit_is_rejected(client):
    response = client.get("/dashboard/?recent_limit=0")

    assert response.status_code == 422


def test_dashboard_recent_movements_include_item_name(client):
    item_id = create_item(
        client, "Electric Drill", "DRILL-001", 10, 2, "Tools"
    )

    movement_response = client.post(
        f"/items/{item_id}/movements/",
        json={
            "movement_type": "IN",
            "quantity": 3,
            "notes": "New delivery",
        },
    )
    assert movement_response.status_code == 201

    response = client.get("/dashboard/")

    assert response.status_code == 200
    movements = response.json()["recent_stock_movements"]

    assert len(movements) == 1
    assert movements[0]["item_name"] == "Electric Drill"


def test_dashboard_recent_maintenance_tasks_include_item_name(client):
    item_id = create_item(
        client, "Electric Drill", "DRILL-001", 10, 2, "Tools"
    )

    task_response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "Inspect drill",
            "priority": "HIGH",
        },
    )
    assert task_response.status_code == 201

    response = client.get("/dashboard/")

    assert response.status_code == 200
    tasks = response.json()["recent_maintenance_tasks"]

    assert len(tasks) == 1
    assert tasks[0]["item_name"] == "Electric Drill"
    assert tasks[0]["title"] == "Inspect drill"
