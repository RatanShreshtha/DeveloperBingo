from collections.abc import Set
from enum import StrEnum


class Prize(StrEnum):
    """The prizes a game can award. The value is the name the wire uses."""

    EARLY_FIVE = "early_five"


EARLY_FIVE_TOPICS = 5


def is_won(prize: Prize, ticked_and_drawn: Set[str]) -> bool:
    """Whether a player's ticked, drawn topics satisfy the prize.

    The caller passes only topics that are both ticked and drawn, so this checks
    the pattern alone.
    """
    if prize is Prize.EARLY_FIVE:
        return len(ticked_and_drawn) >= EARLY_FIVE_TOPICS
    raise ValueError(f"no rule for prize {prize!r}")
