"""Telegram connect enums."""

from enum import Enum


class OwnerType(str, Enum):
    """Which kind of account a Telegram link belongs to."""

    CREATOR = "CREATOR"
    MEMBER = "MEMBER"
