import random

import pytest

from helpers import ManualScheduler, claim_and_settle, names_on, start_and_draw_everything

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    GameAlreadyEnded,
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
    registry = GameRegistry(scheduler=ManualScheduler(), rng=random.Random(31))
    game = registry.create_game(DEFAULT_POOL)
    ada_ticket = registry.join(PlayerRef(game.code, "Ada")).snapshot.ticket
    grace_ticket = registry.join(PlayerRef(game.code, "Grace")).snapshot.ticket
    start_and_draw_everything(registry, game)
    return registry, game, ada_ticket, grace_ticket


def tick(registry, game, name, topics):
    for topic in topics:
        registry.tick(PlayerRef(game.code, name), topic)


# The topics a ticket needs ticked to earn each prize, in a fixed order.
LINE_PRIZES = [(Prize.TOP_LINE, 0), (Prize.MIDDLE_LINE, 1), (Prize.BOTTOM_LINE, 2)]
PRIZE_TOPICS = {
    Prize.EARLY_FIVE: lambda ticket: names_on(ticket)[:5],
    **{prize: (lambda ticket, line=line: sorted(ticket.line(line))) for prize, line in LINE_PRIZES},
    Prize.FOUR_CORNERS: lambda ticket: sorted(ticket.four_corners()),
    Prize.FULL_HOUSE: lambda ticket: names_on(ticket),
}
ALL_PRIZES = list(PRIZE_TOPICS)


@pytest.mark.parametrize("prize", ALL_PRIZES)
def test_a_complete_pattern_wins_its_prize(started_with_every_topic_drawn, prize):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    tick(registry, game, "Ada", PRIZE_TOPICS[prize](ada_ticket))

    (settled,) = claim_and_settle(registry, PlayerRef(game.code, "Ada"), prize).settled

    assert settled.prize is prize
    assert settled.awarded_to == ("Ada",)
    assert registry.host_snapshot(game).prizes[prize] == ("Ada",)


@pytest.mark.parametrize("prize", ALL_PRIZES)
def test_an_incomplete_pattern_is_refused_and_changes_nothing(started_with_every_topic_drawn, prize):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    tick(registry, game, "Ada", PRIZE_TOPICS[prize](ada_ticket)[:-1])
    board_before = registry.host_snapshot(game).prizes
    ticks_before = registry.player_snapshot(PlayerRef(game.code, "Ada")).ticks

    with pytest.raises(ClaimNotValid):
        registry.claim(PlayerRef(game.code, "Ada"), prize)

    assert registry.host_snapshot(game).prizes == board_before
    assert registry.player_snapshot(PlayerRef(game.code, "Ada")).ticks == ticks_before


@pytest.mark.parametrize("prize", ALL_PRIZES)
def test_each_prize_is_awarded_once_per_game(started_with_every_topic_drawn, prize):
    registry, game, ada_ticket, grace_ticket = started_with_every_topic_drawn
    tick(registry, game, "Ada", PRIZE_TOPICS[prize](ada_ticket))
    tick(registry, game, "Grace", PRIZE_TOPICS[prize](grace_ticket))
    claim_and_settle(registry, PlayerRef(game.code, "Ada"), prize)

    # Awarding the full house also ends the game, so a second claim meets that first.
    refusal = GameAlreadyEnded if prize is Prize.FULL_HOUSE else PrizeAlreadyAwarded
    with pytest.raises(refusal):
        registry.claim(PlayerRef(game.code, "Grace"), prize)

    assert registry.host_snapshot(game).prizes[prize] == ("Ada",)


def test_one_player_can_win_several_line_prizes(started_with_every_topic_drawn):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    for prize, _ in LINE_PRIZES:
        tick(registry, game, "Ada", PRIZE_TOPICS[prize](ada_ticket))

    for prize, _ in LINE_PRIZES:
        claim_and_settle(registry, PlayerRef(game.code, "Ada"), prize)

    board = registry.host_snapshot(game).prizes
    assert [board[prize] for prize, _ in LINE_PRIZES] == [("Ada",), ("Ada",), ("Ada",)]


def test_a_prize_remains_open_until_someone_claims_it(started_with_every_topic_drawn):
    registry, game, _, _ = started_with_every_topic_drawn

    assert registry.host_snapshot(game).prizes[Prize.EARLY_FIVE] == ()


def test_claims_are_refused_before_the_game_starts():
    registry = GameRegistry(scheduler=ManualScheduler(), rng=random.Random(31))
    game = registry.create_game(DEFAULT_POOL)
    registry.join(PlayerRef(game.code, "Ada"))

    with pytest.raises(GameNotStarted):
        registry.claim(PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)


def test_only_players_in_the_game_can_claim(started_with_every_topic_drawn):
    registry, game, _, _ = started_with_every_topic_drawn

    with pytest.raises(NotAPlayer):
        registry.claim(PlayerRef(game.code, "Nobody"), Prize.EARLY_FIVE)
