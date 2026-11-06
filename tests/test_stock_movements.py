
def create_test_item(client):
    category_response = client.post(
        "/categories/",
        json={
            "name": "Electrical Equipment",
            "description": "Workshop equipment",
        },
    )

    category_id = category_response.json()["id"]

    item_response = client.post(
        "/items/",
        json={
            "name": "Electric Drill",
            "sku": "DRILL-001",
            "description": "Workshop drill",
            "category_id": category_id,
            "quantity": 10,
            "minimum_stock": 2,
            "location": "Storage A",
        },
    )

    assert item_response.status_code == 201

    return item_response.json()["id"]


def create_movement(
    client,
    item_id,
    movement_type,
    quantity,
    notes="Test movement",
):
    return client.post(
        f"/items/{item_id}/movements/",
        json={
            "movement_type": movement_type,
            "quantity": quantity,
            "notes": notes,
        },
    )


def get_item_quantity(client, item_id):
    response = client.get(f"/items/{item_id}")

    assert response.status_code == 200

    return response.json()["quantity"]


def test_stock_increases_after_in_movement(client):
    item_id = create_test_item(client)

    response = create_movement(
        client,
        item_id,
        "IN",
        5,
    )

    assert response.status_code == 201
    assert response.json()["previous_quantity"] == 10
    assert response.json()["new_quantity"] == 15
    assert get_item_quantity(client, item_id) == 15


def test_stock_decreases_after_out_movement(client):
    item_id = create_test_item(client)

    response = create_movement(
        client,
        item_id,
        "OUT",
        4,
    )

    assert response.status_code == 201
    assert response.json()["previous_quantity"] == 10
    assert response.json()["new_quantity"] == 6
    assert get_item_quantity(client, item_id) == 6


def test_out_movement_cannot_exceed_available_stock(client):
    item_id = create_test_item(client)

    response = create_movement(
        client,
        item_id,
        "OUT",
        15,
    )

    assert response.status_code == 400
    assert get_item_quantity(client, item_id) == 10


def test_adjustment_sets_actual_stock_quantity(client):
    item_id = create_test_item(client)

    response = create_movement(
        client,
        item_id,
        "ADJUSTMENT",
        7,
    )

    assert response.status_code == 201
    assert response.json()["previous_quantity"] == 10
    assert response.json()["new_quantity"] == 7
    assert get_item_quantity(client, item_id) == 7


def test_zero_quantity_in_movement_is_rejected(client):
    item_id = create_test_item(client)

    response = create_movement(
        client,
        item_id,
        "IN",
        0,
    )

    assert response.status_code == 422
    assert get_item_quantity(client, item_id) == 10


def test_negative_stock_adjustment_is_rejected(client):
    item_id = create_test_item(client)

    response = create_movement(
        client,
        item_id,
        "ADJUSTMENT",
        -5,
    )

    assert response.status_code == 422
    assert get_item_quantity(client, item_id) == 10


def test_movement_for_missing_item_is_rejected(client):
    response = create_movement(
        client,
        9999,
        "IN",
        5,
    )

    assert response.status_code == 404


def test_item_movement_history(client):
    item_id = create_test_item(client)

    create_movement(client, item_id, "IN", 5)
    create_movement(client, item_id, "OUT", 3)

    response = client.get(
        f"/items/{item_id}/movements/"
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["movement_type"] == "OUT"


def test_all_movements_include_item_name(client):
    item_id = create_test_item(client)

    create_movement(client, item_id, "IN", 5)

    response = client.get("/stock-movements/")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["item_name"] == "Electric Drill"


def test_movement_type_filter(client):
    item_id = create_test_item(client)

    create_movement(client, item_id, "IN", 5)
    create_movement(client, item_id, "OUT", 3)

    response = client.get(
        "/stock-movements/?movement_type=IN"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["movement_type"] == "IN"


def test_movement_search_by_item_name(client):
    item_id = create_test_item(client)

    create_movement(client, item_id, "IN", 5)

    response = client.get(
        "/stock-movements/?search=Electric Drill"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_movement_pagination(client):
    item_id = create_test_item(client)

    create_movement(client, item_id, "IN", 1)
    create_movement(client, item_id, "IN", 2)
    create_movement(client, item_id, "IN", 3)

    response = client.get(
        "/stock-movements/?page=1&page_size=2"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 2
    assert response.json()["total_pages"] == 2
    assert len(response.json()["items"]) == 2

def test_zero_quantity_out_movement_is_rejected(client):
    item_id = create_test_item(client)

    response = create_movement(
        client,
        item_id,
        "OUT",
        0,
    )

    assert response.status_code == 422
    assert get_item_quantity(client, item_id) == 10


def test_invalid_movement_type_is_rejected(client):
    item_id = create_test_item(client)

    response = create_movement(
        client,
        item_id,
        "INVALID",
        5,
    )

    assert response.status_code == 422
    assert get_item_quantity(client, item_id) == 10


def test_zero_quantity_adjustment_sets_stock_to_zero(client):
    item_id = create_test_item(client)

    response = create_movement(
        client,
        item_id,
        "ADJUSTMENT",
        0,
    )

    assert response.status_code == 201
    assert response.json()["previous_quantity"] == 10
    assert response.json()["new_quantity"] == 0
    assert get_item_quantity(client, item_id) == 0


def test_movement_filter_by_item_id(client):
    first_item_id = create_test_item(client)

    category_response = client.post(
        "/categories/",
        json={"name": "Other Equipment"},
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

    create_movement(client, first_item_id, "IN", 2)
    create_movement(client, second_item_id, "IN", 3)

    response = client.get(
        f"/stock-movements/?item_id={first_item_id}"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert all(
        movement["item_id"] == first_item_id
        for movement in data["items"]
    )
