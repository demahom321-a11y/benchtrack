from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HEAD = "2a394cc50900"


def test_migrations_build_current_schema_from_empty_database(tmp_path):
    database_path = tmp_path / "migration_test.db"

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite:///{database_path.as_posix()}",
    )

    command.upgrade(config, "head")
    command.check(config)

    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}"
    )

    try:
        with engine.connect() as connection:
            current_revision = connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )

            assert current_revision == EXPECTED_HEAD

            item_foreign_keys = connection.exec_driver_sql(
                "PRAGMA foreign_key_list(items)"
            ).fetchall()

            movement_foreign_keys = connection.exec_driver_sql(
                "PRAGMA foreign_key_list(stock_movements)"
            ).fetchall()

            maintenance_foreign_keys = connection.exec_driver_sql(
                "PRAGMA foreign_key_list(maintenance_tasks)"
            ).fetchall()

            assert any(
                row[2] == "categories" and row[3] == "category_id"
                for row in item_foreign_keys
            )

            assert any(
                row[2] == "items" and row[3] == "item_id"
                for row in movement_foreign_keys
            )

            assert any(
                row[2] == "items" and row[3] == "item_id"
                for row in maintenance_foreign_keys
            )
    finally:
        engine.dispose()