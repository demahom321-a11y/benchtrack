def strip_non_blank_text(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()

        if not value:
            raise ValueError(
                "This field must contain at least one "
                "non-whitespace character."
            )

    return value