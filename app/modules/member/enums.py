"""Member module enums."""

from enum import Enum


class MembershipStatus(str, Enum):
    """A member's place in one community's Telegram group."""

    PAID_NOT_JOINED = "PAID_NOT_JOINED"  # has a plan, hasn't joined the group yet
    JOINED = "JOINED"
    LEFT = "LEFT"  # left the group on their own; can request again while the plan lasts
    REMOVED = "REMOVED"  # removed by PulseAccess when their plan ended
