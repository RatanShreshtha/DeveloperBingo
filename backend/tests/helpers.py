"""Setup shared by the engine tests."""

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry
from devbingo_backend.pool import Topic
from devbingo_backend.ticket import Ticket
from devbingo_backend.wire import HostLink


def ticket_of(grid: list[list[str | None]]) -> Ticket:
    """A ticket laid out exactly as given, so a test can control which cells are filled."""
    return Ticket(
        tuple(
            tuple(Topic(name, f"{name} explained") if name else None for name in line)
            for line in grid
        )
    )


def names_on(ticket: Ticket) -> list[str]:
    """The topic names on a ticket, in a fixed order.

    Read straight from the lines, deliberately not through the ticket's own
    `topic_names()`, so tests check the engine against the ticket's contents.
    """
    return sorted({cell.name for line in ticket.lines for cell in line if cell is not None})


def start_and_draw_everything(registry: GameRegistry, game: HostLink) -> None:
    """Start the game and draw every topic in the pool, so any topic may be ticked."""
    registry.start(game)
    for _ in range(len(DEFAULT_POOL.topics)):
        registry.draw(game)
