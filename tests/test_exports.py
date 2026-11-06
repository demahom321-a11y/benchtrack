import csv
from io import StringIO

import pytest

from app.routers.exports import safe_csv_value


def create_export_item(
    client,
    name="Electric Drill",
    sku="DRILL-001",
):
    category_response = client.post(
        "/categories/",
        json={"name": "Tools"},
    )
    assert category_response.status_code == 201

    item_response = client.post(
        "/items/",
        json={
            "name": name,
            "sku": sku,
            "category_id": category_response.json()["id"],
            "quantity": 10,
            "minimum_stock": 2,
            "location": "Storage A",
        },
    )
    assert item_response.status_code == 201

    return item_response.json()["id"]


def parse_csv_response(response):
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.content.startswith(b"\xef\xbb\xbf")

    text = response.content.decode("utf-8-sig")
    return list(csv.reader(StringIO(text)))


def test_export_items_csv(client):
    create_export_item(client)

    response = client.get("/exports/items.csv")
    rows = parse_csv_response(response)

    assert rows[0] == [
        "ID",
        "Name",
        "SKU",
        "Description",
        "Category",
        "Quantity",
        "Minimum Stock",
        "Location",
        "Created At",
        "Updated At",
    ]

    assert len(rows) == 2
    assert rows[1][1] == "Electric Drill"
    assert rows[1][2] == "DRILL-001"
    assert rows[1][4] == "Tools"


def test_export_empty_items_csv(client):
    response = client.get("/exports/items.csv")
    rows = parse_csv_response(response)

    assert len(rows) == 1
    assert rows[0][0] == "ID"


def test_export_stock_movements_csv(client):
    item_id = create_export_item(client)

    movement_response = client.post(
        f"/items/{item_id}/movements/",
        json={
            "movement_type": "IN",
            "quantity": 5,
            "notes": "New delivery",
        },
    )
    assert movement_response.status_code == 201

    response = client.get("/exports/stock-movements.csv")
    rows = parse_csv_response(response)

    assert rows[0][0] == "ID"
    assert rows[0][4] == "Movement Type"
    assert len(rows) == 2
    assert rows[1][2] == "Electric Drill"
    assert rows[1][3] == "DRILL-001"
    assert rows[1][4] == "IN"
    assert rows[1][5] == "5"


def test_export_empty_stock_movements_csv(client):
    response = client.get("/exports/stock-movements.csv")
    rows = parse_csv_response(response)

    assert len(rows) == 1


def test_export_maintenance_tasks_csv(client):
    item_id = create_export_item(client)

    task_response = client.post(
        "/maintenance-tasks/",
        json={
            "item_id": item_id,
            "title": "Inspect electric drill",
            "description": "Regular inspection",
            "status": "OPEN",
            "priority": "HIGH",
            "scheduled_date": "2026-11-05",
        },
    )
    assert task_response.status_code == 201

    response = client.get("/exports/maintenance-tasks.csv")
    rows = parse_csv_response(response)

    assert rows[0][0] == "ID"
    assert rows[0][4] == "Title"
    assert rows[0][7] == "Priority"
    assert len(rows) == 2
    assert rows[1][2] == "Electric Drill"
    assert rows[1][4] == "Inspect electric drill"
    assert rows[1][7] == "HIGH"
    assert rows[1][8] == "2026-11-05"


def test_export_empty_maintenance_tasks_csv(client):
    response = client.get("/exports/maintenance-tasks.csv")
    rows = parse_csv_response(response)

    assert len(rows) == 1


def test_csv_formula_injection_is_prevented(client):
    create_export_item(
        client,
        name="=HYPERLINK(\"https://example.com\")",
    )

    response = client.get("/exports/items.csv")
    rows = parse_csv_response(response)

    assert len(rows) == 2
    assert rows[1][1].startswith("'=")


def test_csv_export_preserves_arabic_text(client):
    arabic_name = "معدات الورشة"
    create_export_item(client, name=arabic_name)

    response = client.get("/exports/items.csv")
    rows = parse_csv_response(response)

    assert rows[1][1] == arabic_name


def test_csv_export_filename_header(client):
    response = client.get("/exports/items.csv")

    assert response.status_code == 200
    assert (
        'attachment; filename="benchtrack-inventory.csv"'
        == response.headers["content-disposition"]
    )



@pytest.mark.parametrize(
    "dangerous_name",
    [
        "=1+1",
        "+1+1",
        "-1+1",
        "@SUM(A1:A2)",
        "\t=1+1",
        "\r=1+1",
        "\n=1+1",
        "  =1+1",
    ],
)
def test_csv_formula_injection_variants_are_prevented(
    client,
    dangerous_name,
):
    create_export_item(
        client,
        name=dangerous_name,
    )

    response = client.get("/exports/items.csv")
    rows = parse_csv_response(response)

    assert response.status_code == 200
    assert rows[1][1] == "'" + dangerous_name.strip()


@pytest.mark.parametrize(
    "dangerous_value",
    [
        "=1+1",
        "+1+1",
        "-1+1",
        "@SUM(A1:A2)",
        "\t=1+1",
        "\r=1+1",
        "\n=1+1",
        "  =1+1",
    ],
)
def test_safe_csv_value_escapes_raw_formula_prefixes(dangerous_value):
    assert safe_csv_value(dangerous_value) == "'" + dangerous_value
