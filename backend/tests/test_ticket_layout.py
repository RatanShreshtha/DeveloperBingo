from helpers import ticket_of

# Top line fills columns 0, 2, 4, 6, 8. Middle fills 1, 3, 4, 5, 7. Bottom fills 0, 1, 3, 5, 8.
STAGGERED = ticket_of(
    [
        ["a0", None, "a2", None, "a4", None, "a6", None, "a8"],
        [None, "b1", None, "b3", "b4", "b5", None, "b7", None],
        ["c0", "c1", None, "c3", None, "c5", None, None, "c8"],
    ]
)


def test_a_ticket_lists_the_names_of_all_its_topics():
    assert STAGGERED.topic_names() == {
        "a0",
        "a2",
        "a4",
        "a6",
        "a8",
        "b1",
        "b3",
        "b4",
        "b5",
        "b7",
        "c0",
        "c1",
        "c3",
        "c5",
        "c8",
    }


def test_a_line_is_the_five_topics_on_it():
    assert STAGGERED.line(0) == {"a0", "a2", "a4", "a6", "a8"}
    assert STAGGERED.line(1) == {"b1", "b3", "b4", "b5", "b7"}
    assert STAGGERED.line(2) == {"c0", "c1", "c3", "c5", "c8"}


def test_the_four_corners_are_the_outermost_topics_of_the_top_and_bottom_lines():
    assert STAGGERED.four_corners() == {"a0", "a8", "c0", "c8"}


def test_the_corners_follow_each_line_when_the_top_and_bottom_lines_end_in_different_columns():
    ticket = ticket_of(
        [
            [None, "a1", "a2", None, "a4", None, "a6", "a7", None],
            ["b0", None, None, "b3", None, "b5", None, None, "b8"],
            ["c0", None, "c2", "c3", None, "c5", None, "c7", None],
        ]
    )

    assert ticket.four_corners() == {"a1", "a7", "c0", "c7"}
