from collections.abc import Set
from enum import StrEnum


class Prize(StrEnum):
    """The prizes a game can award. The value is the name the wire uses."""

    EARLY_FIVE = "early_five"


EARLY_FIVE_TOPICS = 5


def satisfies(prize: Prize, ticked_and_drawn: Set[str]) -> bool:
    """Whether the topics given form the pattern the prize needs.

    The caller passes only topics that are both ticked and drawn, so this checks
    the pattern alone, not whether the claim is allowed.
    """
    if prize is Prize.EARLY_FIVE:
        return len(ticked_and_drawn) >= EARLY_FIVE_TOPICS
    raise ValueError(f"no rule for prize {prize!r}")
