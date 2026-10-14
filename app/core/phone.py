"""Phone number normalisation shared by registration and Telegram linking."""

import re

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_phone(raw: str) -> str:
    """Return the phone as '+<country code><number>' with no separators.

    Telegram sends contact numbers without a leading '+', so both sides are
    reduced to digits before the '+' is added back.
    """
    digits = re.sub(r"\D", "", raw)
    return f"+{digits}"


def is_valid_phone(raw: str) -> bool:
    """True when the input has a country code and 8-15 digits."""
    if not raw.strip().startswith("+"):
        return False
    return bool(_E164.match(normalize_phone(raw)))
