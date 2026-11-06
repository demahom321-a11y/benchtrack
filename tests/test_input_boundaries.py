def create_test_records(client):
    category_response = client.post(
        "/categories/",
        json={"name": "Boundary Category"},
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    item_response = client.post(
        "/items/",
        json={
            "name": "Boundary Drill",
            "sku": "BOUNDARY-001",
            "category_id": category_id,
            "quantity": 10,
            "minimum_stock": 2,
        },
    )
    assert item_response.status_code == 201
    item_id = item_response.json()["id"]

    task_response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "Boundary Inspection",
        },
    )
    assert task_response.status_code == 201

    return category_id, item_id, task_response.json()["id"]


def test_category_create_rejects_whitespace_only_name(client):
    response = client.post(
        "/categories/",
        json={"name": "   "},
    )

    assert response.status_code == 422


def test_item_create_rejects_whitespace_only_name(client):
    category_id, _, _ = create_test_records(client)

    response = client.post(
        "/items/",
        json={
            "name": "   ",
            "sku": "VALID-SKU",
            "category_id": category_id,
        },
    )

    assert response.status_code == 422


def test_item_create_rejects_whitespace_only_sku(client):
    category_id, _, _ = create_test_records(client)

    response = client.post(
        "/items/",
        json={
            "name": "Valid Equipment",
            "sku": "   ",
            "category_id": category_id,
        },
    )

    assert response.status_code == 422


def test_maintenance_create_rejects_whitespace_only_title(client):
    _, item_id, _ = create_test_records(client)

    response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "   ",
        },
    )

    assert response.status_code == 422


def test_category_patch_rejects_whitespace_only_name(client):
    category_id, _, _ = create_test_records(client)

    response = client.patch(
        f"/categories/{category_id}",
        json={"name": "   "},
    )

    assert response.status_code == 422


def test_item_patch_rejects_whitespace_only_name(client):
    _, item_id, _ = create_test_records(client)

    response = client.patch(
        f"/items/{item_id}",
        json={"name": "   "},
    )

    assert response.status_code == 422


def test_item_patch_rejects_whitespace_only_sku(client):
    _, item_id, _ = create_test_records(client)

    response = client.patch(
        f"/items/{item_id}",
        json={"sku": "   "},
    )

    assert response.status_code == 422


def test_maintenance_patch_rejects_whitespace_only_title(client):
    _, _, task_id = create_test_records(client)

    response = client.patch(
        f"/maintenance-tasks/{task_id}",
        json={"title": "   "},
    )

    assert response.status_code == 422


def test_category_create_strips_outer_whitespace(client):
    response = client.post(
        "/categories/",
        json={"name": "  Electrical Tools  "},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Electrical Tools"


def test_category_patch_strips_outer_whitespace(client):
    category_id, _, _ = create_test_records(client)

    response = client.patch(
        f"/categories/{category_id}",
        json={"name": "  Mechanical Tools  "},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Mechanical Tools"


def test_item_create_strips_name_and_sku(client):
    category_id, _, _ = create_test_records(client)

    response = client.post(
        "/items/",
        json={
            "name": "  Electric Grinder  ",
            "sku": "  GRINDER-001  ",
            "category_id": category_id,
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Electric Grinder"
    assert response.json()["sku"] == "GRINDER-001"


def test_item_patch_strips_name_and_sku(client):
    _, item_id, _ = create_test_records(client)

    response = client.patch(
        f"/items/{item_id}",
        json={
            "name": "  Updated Drill  ",
            "sku": "  UPDATED-001  ",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Drill"
    assert response.json()["sku"] == "UPDATED-001"


def test_maintenance_create_strips_title(client):
    _, item_id, _ = create_test_records(client)

    response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "  Quarterly Inspection  ",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Quarterly Inspection"


def test_maintenance_patch_strips_title(client):
    _, _, task_id = create_test_records(client)

    response = client.patch(
        f"/maintenance-tasks/{task_id}",
        json={"title": "  Updated Inspection  "},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Inspection"