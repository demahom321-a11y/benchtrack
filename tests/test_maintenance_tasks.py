
def create_test_item(client):
    category_response = client.post(
        "/categories/",
        json={
            "name": "Electrical Equipment",
            "description": "Workshop equipment",
        },
    )
    assert category_response.status_code == 201

    item_response = client.post(
        "/items/",
        json={
            "name": "Electric Drill",
            "sku": "DRILL-001",
            "description": "Workshop drill",
            "category_id": category_response.json()["id"],
            "quantity": 10,
            "minimum_stock": 2,
            "location": "Storage A",
        },
    )
    assert item_response.status_code == 201

    return item_response.json()["id"]


def create_test_task(
    client,
    item_id,
    title="Inspect electric drill",
    status="OPEN",
    priority="MEDIUM",
    scheduled_date="2026-11-05",
):
    return client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": title,
            "description": "Regular workshop inspection",
            "status": status,
            "priority": priority,
            "scheduled_date": scheduled_date,
        },
    )


def test_create_maintenance_task(client):
    item_id = create_test_item(client)

    response = create_test_task(client, item_id)

    assert response.status_code == 201
    data = response.json()

    assert data["item_id"] == item_id
    assert data["title"] == "Inspect electric drill"
    assert data["status"] == "OPEN"
    assert data["priority"] == "MEDIUM"
    assert data["completed_at"] is None


def test_create_task_for_missing_item_is_rejected(client):
    response = create_test_task(client, 9999)

    assert response.status_code == 404


def test_create_completed_task_sets_completed_at(client):
    item_id = create_test_item(client)

    response = create_test_task(
        client,
        item_id,
        status="COMPLETED",
    )

    assert response.status_code == 201
    assert response.json()["completed_at"] is not None


def test_invalid_task_status_is_rejected(client):
    item_id = create_test_item(client)

    response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "Inspect equipment",
            "status": "INVALID",
            "priority": "HIGH",
        },
    )

    assert response.status_code == 422


def test_invalid_task_priority_is_rejected(client):
    item_id = create_test_item(client)

    response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "Inspect equipment",
            "status": "OPEN",
            "priority": "URGENT",
        },
    )

    assert response.status_code == 422


def test_get_maintenance_task_by_id(client):
    item_id = create_test_item(client)
    created = create_test_task(client, item_id)
    task_id = created.json()["id"]

    response = client.get(f"/maintenance-tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["id"] == task_id
    assert response.json()["title"] == "Inspect electric drill"


def test_get_missing_maintenance_task_returns_404(client):
    response = client.get("/maintenance-tasks/9999")

    assert response.status_code == 404


def test_update_task_title_and_priority(client):
    item_id = create_test_item(client)
    created = create_test_task(client, item_id)
    task_id = created.json()["id"]

    response = client.patch(
        f"/maintenance-tasks/{task_id}",
        json={
            "title": "Replace drill battery",
            "priority": "HIGH",
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Replace drill battery"
    assert response.json()["priority"] == "HIGH"


def test_completing_task_sets_completed_at(client):
    item_id = create_test_item(client)
    created = create_test_task(client, item_id)
    task_id = created.json()["id"]

    response = client.patch(
        f"/maintenance-tasks/{task_id}",
        json={"status": "COMPLETED"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["completed_at"] is not None


def test_reopening_completed_task_clears_completed_at(client):
    item_id = create_test_item(client)
    created = create_test_task(
        client,
        item_id,
        status="COMPLETED",
    )
    task_id = created.json()["id"]

    assert created.json()["completed_at"] is not None

    response = client.patch(
        f"/maintenance-tasks/{task_id}",
        json={"status": "OPEN"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "OPEN"
    assert response.json()["completed_at"] is None


def test_null_title_is_rejected(client):
    item_id = create_test_item(client)
    created = create_test_task(client, item_id)
    task_id = created.json()["id"]

    response = client.patch(
        f"/maintenance-tasks/{task_id}",
        json={"title": None},
    )

    assert response.status_code == 422


def test_null_status_is_rejected(client):
    item_id = create_test_item(client)
    created = create_test_task(client, item_id)
    task_id = created.json()["id"]

    response = client.patch(
        f"/maintenance-tasks/{task_id}",
        json={"status": None},
    )

    assert response.status_code == 422


def test_delete_maintenance_task(client):
    item_id = create_test_item(client)
    created = create_test_task(client, item_id)
    task_id = created.json()["id"]

    response = client.delete(f"/maintenance-tasks/{task_id}")

    assert response.status_code == 204

    get_response = client.get(f"/maintenance-tasks/{task_id}")
    assert get_response.status_code == 404


def test_delete_missing_task_returns_404(client):
    response = client.delete("/maintenance-tasks/9999")

    assert response.status_code == 404


def test_filter_tasks_by_status(client):
    item_id = create_test_item(client)

    create_test_task(client, item_id, title="Open task")
    create_test_task(
        client,
        item_id,
        title="Completed task",
        status="COMPLETED",
    )

    response = client.get("/maintenance-tasks/?status=COMPLETED")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["status"] == "COMPLETED"


def test_filter_tasks_by_priority(client):
    item_id = create_test_item(client)

    create_test_task(
        client,
        item_id,
        title="Low priority task",
        priority="LOW",
    )
    create_test_task(
        client,
        item_id,
        title="High priority task",
        priority="HIGH",
    )

    response = client.get("/maintenance-tasks/?priority=HIGH")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["priority"] == "HIGH"


def test_search_tasks_by_item_name(client):
    item_id = create_test_item(client)
    create_test_task(client, item_id)

    response = client.get("/maintenance-tasks/?search=Electric Drill")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_filter_tasks_by_scheduled_date(client):
    item_id = create_test_item(client)

    create_test_task(
        client,
        item_id,
        title="November inspection",
        scheduled_date="2026-11-05",
    )
    create_test_task(
        client,
        item_id,
        title="December inspection",
        scheduled_date="2026-12-10",
    )

    response = client.get(
        "/maintenance-tasks/"
        "?scheduled_from=2026-11-01"
        "&scheduled_to=2026-11-30"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["title"] == "November inspection"


def test_invalid_scheduled_date_range_is_rejected(client):
    response = client.get(
        "/maintenance-tasks/"
        "?scheduled_from=2026-12-01"
        "&scheduled_to=2026-11-01"
    )

    assert response.status_code == 422


def test_maintenance_task_pagination(client):
    item_id = create_test_item(client)

    create_test_task(client, item_id, title="Task One")
    create_test_task(client, item_id, title="Task Two")
    create_test_task(client, item_id, title="Task Three")

    response = client.get(
        "/maintenance-tasks/?page=1&page_size=2"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 2
    assert len(data["items"]) == 2

def test_null_priority_is_rejected(client):
    item_id = create_test_item(client)
    created = create_test_task(client, item_id)
    task_id = created.json()["id"]

    response = client.patch(
        f"/maintenance-tasks/{task_id}",
        json={"priority": None},
    )

    assert response.status_code == 422


def test_search_tasks_by_title_description_and_item_sku(client):
    item_id = create_test_item(client)

    response = create_test_task(
        client,
        item_id,
        title="Quarterly inspection",
    )
    assert response.status_code == 201

    for search_term in (
        "Quarterly inspection",
        "Regular workshop inspection",
        "DRILL-001",
    ):
        response = client.get(
            "/maintenance-tasks/",
            params={"search": search_term},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1


def test_filter_tasks_by_item_id(client):
    first_item_id = create_test_item(client)

    category_response = client.post(
        "/categories/",
        json={"name": "Mechanical Equipment"},
    )
    assert category_response.status_code == 201

    second_item_response = client.post(
        "/items/",
        json={
            "name": "Workshop Hammer",
            "sku": "HAMMER-001",
            "category_id": category_response.json()["id"],
            "quantity": 5,
            "minimum_stock": 1,
        },
    )
    assert second_item_response.status_code == 201

    second_item_id = second_item_response.json()["id"]

    first_task = create_test_task(
        client,
        first_item_id,
        title="Drill inspection",
    )
    second_task = create_test_task(
        client,
        second_item_id,
        title="Hammer inspection",
    )

    assert first_task.status_code == 201
    assert second_task.status_code == 201

    response = client.get(
        "/maintenance-tasks/",
        params={"item_id": second_item_id},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["item_id"] == second_item_id
    assert data["items"][0]["title"] == "Hammer inspection"


def test_maintenance_tasks_sorting(client):
    item_id = create_test_item(client)

    for title in ("Saw inspection", "Drill inspection", "Hammer inspection"):
        response = create_test_task(
            client,
            item_id,
            title=title,
        )
        assert response.status_code == 201

    response = client.get(
        "/maintenance-tasks/",
        params={
            "sort_by": "title",
            "order": "asc",
        },
    )

    assert response.status_code == 200

    titles = [
        task["title"]
        for task in response.json()["items"]
    ]

    assert titles == [
        "Drill inspection",
        "Hammer inspection",
        "Saw inspection",
    ]


def test_invalid_maintenance_pagination_is_rejected(client):
    invalid_page = client.get(
        "/maintenance-tasks/?page=0"
    )

    assert invalid_page.status_code == 422

    invalid_page_size = client.get(
        "/maintenance-tasks/?page_size=101"
    )

    assert invalid_page_size.status_code == 422
