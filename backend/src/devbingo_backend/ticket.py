import random
from dataclasses import dataclass

from devbingo_backend.pool import Pool, Topic

TICKET_LINES = 3
TICKET_COLUMNS = 9
TOPICS_PER_LINE = 5
TOPICS_PER_TICKET = 15
MAX_TOPICS_PER_COLUMN = 3


@dataclass(frozen=True)
class Ticket:
    """A tambola-style ticket: three lines of nine cells, some of them empty."""

    lines: tuple[tuple[Topic | None, ...], ...]

    def to_cells(self) -> list[list[str | None]]:
        """The ticket as topic names, with empty cells as None."""
        return [[cell.name if cell else None for cell in line] for line in self.lines]


def _column_counts(rng: random.Random) -> list[int]:
    """Give each column one topic, then spread the rest, capped at three per column."""
    counts = [1] * TICKET_COLUMNS
    extra = TOPICS_PER_TICKET - TICKET_COLUMNS
    while extra:
        column = rng.randrange(TICKET_COLUMNS)
        if counts[column] < MAX_TOPICS_PER_COLUMN:
            counts[column] += 1
            extra -= 1
    return counts


def build_ticket(pool: Pool, rng: random.Random) -> Ticket:
    pool_columns = pool.columns()
    while True:
        counts = _column_counts(rng)
        # For each column, the lines its topics sit in.
        column_lines = [rng.sample(range(TICKET_LINES), count) for count in counts]
        line_totals = [0] * TICKET_LINES
        for lines in column_lines:
            for line in lines:
                line_totals[line] += 1
        if all(total == TOPICS_PER_LINE for total in line_totals):
            break

    grid: list[list[Topic | None]] = [[None] * TICKET_COLUMNS for _ in range(TICKET_LINES)]
    for column, lines in enumerate(column_lines):
        column_topics = pool_columns[column]
        chosen = rng.sample(column_topics, len(lines))
        # Topics keep the pool's order from the top of the column downwards.
        chosen.sort(key=column_topics.index)
        for line, topic in zip(sorted(lines), chosen):
            grid[line][column] = topic

    return Ticket(tuple(tuple(line) for line in grid))
