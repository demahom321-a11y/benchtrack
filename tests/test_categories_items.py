
def create_category(client, name="Electrical Equipment"):
    return client.post(
        "/categories/",
        json={
            "name": name,
            "description": "Workshop equipment",
        },
    )


def create_item(client, category_id, sku="TOOL-001"):
    return client.post(
        "/items/",
        json={
            "name": "Professional Electric Drill",
            "sku": sku,
            "description": "Cordless workshop drill",
            "category_id": category_id,
            "quantity": 10,
            "minimum_stock": 2,
            "location": "Storage Room A",
        },
    )


def test_create_category(client):
    response = create_category(client)

    assert response.status_code == 201
    assert response.json()["name"] == "Electrical Equipment"


def test_duplicate_category_is_rejected(client):
    first_response = create_category(client)
    second_response = create_category(client)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_create_item(client):
    category_response = create_category(client)
    category_id = category_response.json()["id"]

    response = create_item(client, category_id)

    assert response.status_code == 201
    assert response.json()["name"] == "Professional Electric Drill"
    assert response.json()["quantity"] == 10
    assert response.json()["category_id"] == category_id


def test_item_with_missing_category_is_rejected(client):
    response = create_item(client, category_id=9999)

    assert response.status_code == 404


def test_duplicate_item_sku_is_rejected(client):
    category_response = create_category(client)
    category_id = category_response.json()["id"]

    first_response = create_item(client, category_id)
    second_response = create_item(client, category_id)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_get_item_by_id(client):
    category_response = create_category(client)
    category_id = category_response.json()["id"]

    create_response = create_item(client, category_id)
    item_id = create_response.json()["id"]

    response = client.get(f"/items/{item_id}")

    assert response.status_code == 200
    assert response.json()["id"] == item_id


def test_update_item_name(client):
    category_response = create_category(client)
    category_id = category_response.json()["id"]

    create_response = create_item(client, category_id)
    item_id = create_response.json()["id"]

    response = client.patch(
        f"/items/{item_id}",
        json={"name": "Updated Electric Drill"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Electric Drill"


def test_item_quantity_cannot_be_changed_directly(client):
    category_response = create_category(client)
    category_id = category_response.json()["id"]

    create_response = create_item(client, category_id)
    item_id = create_response.json()["id"]

    response = client.patch(
        f"/items/{item_id}",
        json={"quantity": 50},
    )

    assert response.status_code == 400

    unchanged = client.get(f"/items/{item_id}")
    assert unchanged.status_code == 200
    assert unchanged.json()["quantity"] == 10

    history = client.get(f"/items/{item_id}/movements/")
    assert history.status_code == 200
    assert history.json() == []


def test_category_with_assigned_item_cannot_be_deleted(client):
    category_response = create_category(client)
    category_id = category_response.json()["id"]

    create_item(client, category_id)

    response = client.delete(f"/categories/{category_id}")

    assert response.status_code == 409

def test_delete_item_without_history(client):
    category_response = create_category(client)
    category_id = category_response.json()["id"]

    item_response = create_item(client, category_id)
    item_id = item_response.json()["id"]

    response = client.delete(f"/items/{item_id}")

    assert response.status_code == 204

    get_response = client.get(f"/items/{item_id}")
    assert get_response.status_code == 404


def test_item_with_stock_movements_cannot_be_deleted(client):
    category_response = create_category(client)
    category_id = category_response.json()["id"]

    item_response = create_item(client, category_id)
    item_id = item_response.json()["id"]

    movement_response = client.post(
        f"/items/{item_id}/movements/",
        json={
            "movement_type": "IN",
            "quantity": 2,
            "notes": "Test delivery",
        },
    )

    assert movement_response.status_code == 201

    response = client.delete(f"/items/{item_id}")

    assert response.status_code == 409

    get_response = client.get(f"/items/{item_id}")
    assert get_response.status_code == 200
    assert get_response.json()["quantity"] == 12


def test_item_with_maintenance_tasks_cannot_be_deleted(client):
    category_response = create_category(client)
    category_id = category_response.json()["id"]

    item_response = create_item(client, category_id)
    item_id = item_response.json()["id"]

    task_response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "Inspect electric drill",
        },
    )

    assert task_response.status_code == 201

    response = client.delete(f"/items/{item_id}")

    assert response.status_code == 409

    get_response = client.get(f"/items/{item_id}")
    assert get_response.status_code == 200


def test_delete_missing_item_returns_404(client):
    response = client.delete("/items/9999")

    assert response.status_code == 404

def create_listing_item(
    client,
    category_id,
    *,
    name,
    sku,
    quantity,
    minimum_stock,
    location,
    description,
):
    return client.post(
        "/items/",
        json={
            "name": name,
            "sku": sku,
            "description": description,
            "category_id": category_id,
            "quantity": quantity,
            "minimum_stock": minimum_stock,
            "location": location,
        },
    )


def test_list_items_returns_paginated_response(client):
    category = create_category(client)
    category_id = category.json()["id"]

    for index in range(3):
        response = create_listing_item(
            client,
            category_id,
            name=f"Equipment {index}",
            sku=f"EQUIP-{index:03}",
            quantity=10,
            minimum_stock=2,
            location="Storage A",
            description="Workshop equipment",
        )
        assert response.status_code == 201

    response = client.get("/items/?page=1&page_size=2")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 2
    assert len(data["items"]) == 2


def test_search_items_by_name_sku_and_description(client):
    category = create_category(client)
    category_id = category.json()["id"]

    response = create_listing_item(
        client,
        category_id,
        name="Precision Drill",
        sku="SEARCH-DRILL",
        quantity=10,
        minimum_stock=2,
        location="Storage A",
        description="Special cordless equipment",
    )
    assert response.status_code == 201

    for search_term in (
        "Precision Drill",
        "SEARCH-DRILL",
        "cordless equipment",
    ):
        response = client.get(
            "/items/",
            params={"search": search_term},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["sku"] == "SEARCH-DRILL"


def test_filter_items_by_category_and_location(client):
    first_category = create_category(client, "Electrical")
    second_category = create_category(client, "Mechanical")

    first_item = create_listing_item(
        client,
        first_category.json()["id"],
        name="Electric Drill",
        sku="FILTER-001",
        quantity=10,
        minimum_stock=2,
        location="North Storage",
        description="Electrical equipment",
    )

    second_item = create_listing_item(
        client,
        second_category.json()["id"],
        name="Workshop Hammer",
        sku="FILTER-002",
        quantity=5,
        minimum_stock=1,
        location="South Storage",
        description="Mechanical equipment",
    )

    assert first_item.status_code == 201
    assert second_item.status_code == 201

    category_response = client.get(
        "/items/",
        params={"category_id": first_category.json()["id"]},
    )

    assert category_response.status_code == 200
    assert category_response.json()["total"] == 1
    assert category_response.json()["items"][0]["sku"] == "FILTER-001"

    location_response = client.get(
        "/items/",
        params={"location": "South"},
    )

    assert location_response.status_code == 200
    assert location_response.json()["total"] == 1
    assert location_response.json()["items"][0]["sku"] == "FILTER-002"


def test_low_stock_and_out_of_stock_filters(client):
    category = create_category(client)
    category_id = category.json()["id"]

    test_items = [
        ("Low Stock Drill", "LOW-001", 2, 3),
        ("Empty Stock Drill", "EMPTY-001", 0, 3),
        ("Available Drill", "AVAILABLE-001", 8, 3),
    ]

    for name, sku, quantity, minimum_stock in test_items:
        response = create_listing_item(
            client,
            category_id,
            name=name,
            sku=sku,
            quantity=quantity,
            minimum_stock=minimum_stock,
            location="Storage A",
            description="Workshop equipment",
        )
        assert response.status_code == 201

    low_stock_response = client.get(
        "/items/",
        params={"low_stock": True},
    )

    assert low_stock_response.status_code == 200
    assert low_stock_response.json()["total"] == 1
    assert (
        low_stock_response.json()["items"][0]["sku"]
        == "LOW-001"
    )

    out_of_stock_response = client.get(
        "/items/",
        params={"out_of_stock": True},
    )

    assert out_of_stock_response.status_code == 200
    assert out_of_stock_response.json()["total"] == 1
    assert (
        out_of_stock_response.json()["items"][0]["sku"]
        == "EMPTY-001"
    )


def test_conflicting_stock_filters_are_rejected(client):
    response = client.get(
        "/items/?low_stock=true&out_of_stock=true"
    )

    assert response.status_code == 422


def test_items_sorting_and_pagination(client):
    category = create_category(client)
    category_id = category.json()["id"]

    test_items = [
        ("Drill", "SORT-001", 5),
        ("Hammer", "SORT-002", 8),
        ("Saw", "SORT-003", 2),
    ]

    for name, sku, quantity in test_items:
        response = create_listing_item(
            client,
            category_id,
            name=name,
            sku=sku,
            quantity=quantity,
            minimum_stock=1,
            location="Storage A",
            description="Workshop equipment",
        )
        assert response.status_code == 201

    first_page = client.get(
        "/items/",
        params={
            "sort_by": "quantity",
            "order": "desc",
            "page": 1,
            "page_size": 2,
        },
    )

    assert first_page.status_code == 200

    first_data = first_page.json()

    assert first_data["total"] == 3
    assert first_data["total_pages"] == 2
    assert len(first_data["items"]) == 2
    assert first_data["items"][0]["sku"] == "SORT-002"
    assert first_data["items"][1]["sku"] == "SORT-001"

    second_page = client.get(
        "/items/",
        params={
            "sort_by": "quantity",
            "order": "desc",
            "page": 2,
            "page_size": 2,
        },
    )

    assert second_page.status_code == 200
    assert len(second_page.json()["items"]) == 1
    assert second_page.json()["items"][0]["sku"] == "SORT-003"


def test_invalid_item_pagination_is_rejected(client):
    invalid_page = client.get("/items/?page=0")

    assert invalid_page.status_code == 422

    invalid_page_size = client.get("/items/?page_size=101")

    assert invalid_page_size.status_code == 422

def test_list_categories(client):
    create_category(client, "Electrical")
    create_category(client, "Mechanical")

    response = client.get("/categories/")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert [item["name"] for item in response.json()] == [
        "Electrical",
        "Mechanical",
    ]


def test_get_category_by_id(client):
    created = create_category(client)
    category_id = created.json()["id"]

    response = client.get(f"/categories/{category_id}")

    assert response.status_code == 200
    assert response.json()["id"] == category_id
    assert response.json()["name"] == "Electrical Equipment"


def test_get_missing_category_returns_404(client):
    response = client.get("/categories/9999")

    assert response.status_code == 404


def test_update_category_name(client):
    created = create_category(client)
    category_id = created.json()["id"]

    response = client.patch(
        f"/categories/{category_id}",
        json={"name": "Workshop Tools"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Workshop Tools"


def test_update_category_description(client):
    created = create_category(client)
    category_id = created.json()["id"]

    response = client.patch(
        f"/categories/{category_id}",
        json={"description": "Updated description"},
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"


def test_duplicate_category_name_update_is_rejected(client):
    first = create_category(client, "Electrical")
    second = create_category(client, "Mechanical")

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.patch(
        f"/categories/{first.json()['id']}",
        json={"name": "Mechanical"},
    )

    assert response.status_code == 409

    unchanged = client.get(
        f"/categories/{first.json()['id']}"
    )

    assert unchanged.json()["name"] == "Electrical"


def test_null_category_name_update_is_rejected(client):
    created = create_category(client)
    category_id = created.json()["id"]

    response = client.patch(
        f"/categories/{category_id}",
        json={"name": None},
    )

    assert response.status_code == 422


def test_delete_category_without_items(client):
    created = create_category(client)
    category_id = created.json()["id"]

    response = client.delete(f"/categories/{category_id}")

    assert response.status_code == 204

    get_response = client.get(f"/categories/{category_id}")
    assert get_response.status_code == 404


def test_delete_missing_category_returns_404(client):
    response = client.delete("/categories/9999")

    assert response.status_code == 404
