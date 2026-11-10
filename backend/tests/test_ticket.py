import random

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.ticket import build_ticket


def sample_tickets(count: int = 300):
    rng = random.Random(1234)
    return [build_ticket(DEFAULT_POOL, rng) for _ in range(count)]


def test_a_ticket_has_three_lines_of_nine_cells():
    for ticket in sample_tickets(50):
        assert len(ticket.lines) == 3
        assert all(len(line) == 9 for line in ticket.lines)


def test_each_line_has_exactly_five_topics():
    for ticket in sample_tickets():
        for line in ticket.lines:
            assert sum(cell is not None for cell in line) == 5


def test_a_ticket_has_exactly_fifteen_topics():
    for ticket in sample_tickets():
        assert sum(cell is not None for line in ticket.lines for cell in line) == 15


def test_each_column_has_one_to_three_topics_and_none_is_empty():
    for ticket in sample_tickets():
        for column in range(9):
            count = sum(ticket.lines[line][column] is not None for line in range(3))
            assert 1 <= count <= 3


def test_topics_in_a_column_follow_the_pool_order_top_to_bottom():
    pool_columns = DEFAULT_POOL.columns()
    for ticket in sample_tickets():
        for column in range(9):
            cells = [ticket.lines[line][column] for line in range(3)]
            topics = [cell for cell in cells if cell is not None]
            # Each topic belongs to this pool column, and the ticket lists
            # them in the same order the pool does, top to bottom.
            assert all(topic in pool_columns[column] for topic in topics)
            positions = [pool_columns[column].index(topic) for topic in topics]
            assert positions == sorted(positions)


def test_every_topic_on_a_ticket_comes_from_the_pool():
    pool_topics = set(DEFAULT_POOL.topics)
    for ticket in sample_tickets(50):
        for line in ticket.lines:
            for cell in line:
                if cell is not None:
                    assert cell in pool_topics
