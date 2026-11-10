import random
from dataclasses import dataclass

from devbingo_backend.pool import Pool, Topic

TICKET_ROWS = 3
TICKET_COLUMNS = 9
TOPICS_PER_ROW = 5
TOPICS_PER_TICKET = 15
MAX_TOPICS_PER_COLUMN = 3


@dataclass(frozen=True)
class Ticket:
    """A tambola-style board: three rows of nine cells, some of them empty."""

    rows: tuple[tuple[Topic | None, ...], ...]

    def names(self) -> list[list[str | None]]:
        return [[cell.name if cell else None for cell in row] for row in self.rows]


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
        # For each column, the rows its topics sit in.
        column_rows = [rng.sample(range(TICKET_ROWS), count) for count in counts]
        row_totals = [0] * TICKET_ROWS
        for rows in column_rows:
            for row in rows:
                row_totals[row] += 1
        if all(total == TOPICS_PER_ROW for total in row_totals):
            break

    grid: list[list[Topic | None]] = [[None] * TICKET_COLUMNS for _ in range(TICKET_ROWS)]
    for column, rows in enumerate(column_rows):
        column_topics = pool_columns[column]
        chosen = rng.sample(column_topics, len(rows))
        # Topics keep the pool's order from the top of the column downwards.
        chosen.sort(key=column_topics.index)
        for row, topic in zip(sorted(rows), chosen):
            grid[row][column] = topic

    return Ticket(tuple(tuple(row) for row in grid))
