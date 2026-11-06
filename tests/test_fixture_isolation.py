import pytest
from conftest import preserve_dependency_overrides

from app.main import app


def test_dependency_overrides_are_restored_after_exception():
    original_state = app.dependency_overrides.copy()

    dependency = object()
    another_dependency = object()

    def original_override():
        return "original"

    def replacement_override():
        return "replacement"

    expected_state = {
        **original_state,
        dependency: original_override,
    }

    app.dependency_overrides.clear()
    app.dependency_overrides.update(expected_state)

    try:
        with (
            pytest.raises(
                RuntimeError,
                match="Simulated test failure.",
            ),
            preserve_dependency_overrides(
                {
                    dependency: replacement_override,
                    another_dependency: replacement_override,
                }
            ),
        ):
            assert (
                app.dependency_overrides[dependency]
                is replacement_override
            )
            assert another_dependency in app.dependency_overrides

            raise RuntimeError("Simulated test failure.")

        assert app.dependency_overrides == expected_state

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_state)