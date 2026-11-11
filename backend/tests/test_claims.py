import random

import pytest

from helpers import names_on, start_and_draw_everything

from devbingo_backend.game import (
    GameNotStarted,
    GameRegistry,
    NotAPlayer,
    PlayerRef,
    PrizeAlreadyAwarded,
    ClaimNotValid,
)
from devbingo_backend.prizes import Prize


@pytest.fixture
def started_with_every_topic_drawn():
    registry = GameRegistry(rng=random.Random(31))
    game = registry.create_game()
    ada_ticket = registry.join(PlayerRef(game.code, "Ada")).ticket
    grace_ticket = registry.join(PlayerRef(game.code, "Grace")).ticket
    start_and_draw_everything(registry, game)
    return registry, game, ada_ticket, grace_ticket


def tick_n(registry, game, ticket, name, count):
    player = PlayerRef(game.code, name)
    for topic in names_on(ticket)[:count]:
        registry.tick(player, topic)


def test_five_ticked_and_drawn_topics_award_early_five(started_with_every_topic_drawn):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    tick_n(registry, game, ada_ticket, "Ada", 5)

    outcome = registry.claim(PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)

    assert outcome.prize is Prize.EARLY_FIVE
    assert outcome.awarded_to == ("Ada",)
    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == ["Ada"]


def test_fewer_than_five_ticks_is_not_a_valid_early_five(started_with_every_topic_drawn):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    tick_n(registry, game, ada_ticket, "Ada", 4)
    board_before = registry.prize_board(game.code)
    ticks_before = registry.ticks(PlayerRef(game.code, "Ada"))

    with pytest.raises(ClaimNotValid):
        registry.claim(PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)

    assert registry.prize_board(game.code) == board_before
    assert registry.ticks(PlayerRef(game.code, "Ada")) == ticks_before


def test_the_prize_is_awarded_once_per_game(started_with_every_topic_drawn):
    registry, game, ada_ticket, grace_ticket = started_with_every_topic_drawn
    tick_n(registry, game, ada_ticket, "Ada", 5)
    tick_n(registry, game, grace_ticket, "Grace", 5)
    registry.claim(PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)

    with pytest.raises(PrizeAlreadyAwarded):
        registry.claim(PlayerRef(game.code, "Grace"), Prize.EARLY_FIVE)

    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == ["Ada"]


def test_a_prize_remains_open_until_someone_claims_it(started_with_every_topic_drawn):
    registry, game, _, _ = started_with_every_topic_drawn

    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == []


def test_claims_are_refused_before_the_game_starts():
    registry = GameRegistry(rng=random.Random(31))
    game = registry.create_game()
    registry.join(PlayerRef(game.code, "Ada"))

    with pytest.raises(GameNotStarted):
        registry.claim(PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)


def test_only_players_in_the_game_can_claim(started_with_every_topic_drawn):
    registry, game, _, _ = started_with_every_topic_drawn

    with pytest.raises(NotAPlayer):
        registry.claim(PlayerRef(game.code, "Nobody"), Prize.EARLY_FIVE)


def test_all_fifteen_ticked_and_drawn_topics_award_full_house(started_with_every_topic_drawn):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    tick_n(registry, game, ada_ticket, "Ada", 15)

    outcome = registry.claim(PlayerRef(game.code, "Ada"), Prize.FULL_HOUSE)

    assert outcome.awarded_to == ("Ada",)
    assert registry.prize_board(game.code)[Prize.FULL_HOUSE] == ["Ada"]


def test_a_partly_complete_ticket_is_not_a_valid_full_house(started_with_every_topic_drawn):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    tick_n(registry, game, ada_ticket, "Ada", 14)
    board_before = registry.prize_board(game.code)
    ticks_before = registry.ticks(PlayerRef(game.code, "Ada"))

    with pytest.raises(ClaimNotValid):
        registry.claim(PlayerRef(game.code, "Ada"), Prize.FULL_HOUSE)

    assert registry.prize_board(game.code) == board_before
    assert registry.ticks(PlayerRef(game.code, "Ada")) == ticks_before


def test_full_house_is_awarded_once_per_game(started_with_every_topic_drawn):
    registry, game, ada_ticket, grace_ticket = started_with_every_topic_drawn
    tick_n(registry, game, ada_ticket, "Ada", 15)
    tick_n(registry, game, grace_ticket, "Grace", 15)
    registry.claim(PlayerRef(game.code, "Ada"), Prize.FULL_HOUSE)

    with pytest.raises(PrizeAlreadyAwarded):
        registry.claim(PlayerRef(game.code, "Grace"), Prize.FULL_HOUSE)

    assert registry.prize_board(game.code)[Prize.FULL_HOUSE] == ["Ada"]


def tick_line(registry, game, ticket, name, line):
    for topic in ticket.lines[line]:
        if topic is not None:
            registry.tick(PlayerRef(game.code, name), topic.name)


LINE_PRIZES = [(Prize.TOP_LINE, 0), (Prize.MIDDLE_LINE, 1), (Prize.BOTTOM_LINE, 2)]


@pytest.mark.parametrize(("prize", "line"), LINE_PRIZES)
def test_a_complete_line_wins_its_prize(started_with_every_topic_drawn, prize, line):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    tick_line(registry, game, ada_ticket, "Ada", line)

    outcome = registry.claim(PlayerRef(game.code, "Ada"), prize)

    assert outcome.awarded_to == ("Ada",)
    assert registry.prize_board(game.code)[prize] == ["Ada"]


@pytest.mark.parametrize(("prize", "line"), LINE_PRIZES)
def test_an_incomplete_line_is_refused_and_changes_nothing(started_with_every_topic_drawn, prize, line):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    tick_line(registry, game, ada_ticket, "Ada", line)
    registry.untick(PlayerRef(game.code, "Ada"), next(t.name for t in ada_ticket.lines[line] if t is not None))
    board_before = registry.prize_board(game.code)
    ticks_before = registry.ticks(PlayerRef(game.code, "Ada"))

    with pytest.raises(ClaimNotValid):
        registry.claim(PlayerRef(game.code, "Ada"), prize)

    assert registry.prize_board(game.code) == board_before
    assert registry.ticks(PlayerRef(game.code, "Ada")) == ticks_before


@pytest.mark.parametrize(("prize", "line"), LINE_PRIZES)
def test_each_line_prize_is_awarded_once_per_game(started_with_every_topic_drawn, prize, line):
    registry, game, ada_ticket, grace_ticket = started_with_every_topic_drawn
    tick_line(registry, game, ada_ticket, "Ada", line)
    tick_line(registry, game, grace_ticket, "Grace", line)
    registry.claim(PlayerRef(game.code, "Ada"), prize)

    with pytest.raises(PrizeAlreadyAwarded):
        registry.claim(PlayerRef(game.code, "Grace"), prize)

    assert registry.prize_board(game.code)[prize] == ["Ada"]


def test_one_player_can_win_several_line_prizes(started_with_every_topic_drawn):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    for _, line in LINE_PRIZES:
        tick_line(registry, game, ada_ticket, "Ada", line)

    for prize, _ in LINE_PRIZES:
        registry.claim(PlayerRef(game.code, "Ada"), prize)

    board = registry.prize_board(game.code)
    assert [board[prize] for prize, _ in LINE_PRIZES] == [["Ada"], ["Ada"], ["Ada"]]
