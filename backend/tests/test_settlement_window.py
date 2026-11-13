import random

import pytest
from helpers import ManualRegistry, draw_everything, names_on

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    ClaimNotValid,
    ClaimPending,
    GameAlreadyEnded,
    NoTopicsLeft,
    PlayerRef,
    SettlementWindowOpen,
)
from devbingo_backend.prizes import Prize


@pytest.fixture
def table():
    registry = ManualRegistry(rng=random.Random(7))
    game = registry.create_game(DEFAULT_POOL)
    tickets = {
        name: registry.join(PlayerRef(game.code, name)).snapshot.ticket for name in ("Ada", "Grace")
    }
    registry.start(game)
    return registry, game, tickets


def ada(game):
    return PlayerRef(game.code, "Ada")


def grace(game):
    return PlayerRef(game.code, "Grace")


def tick_five(registry, game, ticket, who):
    for topic in names_on(ticket)[:5]:
        registry.tick(who, topic)


def draw_all_and_tick_five(registry, game, tickets):
    draw_everything(registry, game)
    tick_five(registry, game, tickets["Ada"], ada(game))
    tick_five(registry, game, tickets["Grace"], grace(game))


def test_a_valid_claim_opens_a_window_and_the_prize_stays_open_until_it_closes(table):
    registry, game, tickets = table
    draw_all_and_tick_five(registry, game, tickets)

    result = registry.claim(ada(game), Prize.EARLY_FIVE)

    assert result.refusal is None
    assert result.outcome.window_open is True
    assert registry.host_snapshot(game).prizes[Prize.EARLY_FIVE] == ()


def test_two_claims_in_one_window_win_the_prize_together(table):
    registry, game, tickets = table
    draw_all_and_tick_five(registry, game, tickets)
    registry.claim(ada(game), Prize.EARLY_FIVE)

    second = registry.claim(grace(game), Prize.EARLY_FIVE)
    ((outcome,)) = registry.settle()
    (settled,) = outcome.settled

    # The window was already open, so nothing about it changed.
    assert second.outcome.window_open is None
    assert settled.awarded_to == ("Ada", "Grace")
    assert registry.host_snapshot(game).prizes[Prize.EARLY_FIVE] == ("Ada", "Grace")


def test_an_invalid_claim_is_refused_and_opens_no_window(table):
    registry, game, tickets = table
    registry.draw(game)

    result = registry.claim(ada(game), Prize.EARLY_FIVE)

    assert isinstance(result.refusal, ClaimNotValid)
    assert result.outcome.window_open is None

    registry.draw(game)


def test_draws_are_refused_while_a_window_is_open_and_resume_after_it_closes(table):
    registry, game, tickets = table
    draw_all_and_tick_five(registry, game, tickets)
    registry.claim(ada(game), Prize.EARLY_FIVE)

    with pytest.raises(SettlementWindowOpen):
        registry.draw(game)
    registry.settle()

    # Every topic is already drawn, so the pool refuses: the settlement hold is gone.
    with pytest.raises(NoTopicsLeft):
        registry.draw(game)


def test_ticks_cannot_be_taken_back_while_the_player_has_a_claim_pending(table):
    registry, game, tickets = table
    draw_all_and_tick_five(registry, game, tickets)
    registry.claim(ada(game), Prize.EARLY_FIVE)
    ticked = names_on(tickets["Ada"])[0]

    with pytest.raises(ClaimPending):
        registry.untick(ada(game), ticked)
    registry.untick(grace(game), names_on(tickets["Grace"])[0])
    assert ticked in registry.player_snapshot(ada(game)).ticks

    registry.settle()
    registry.untick(ada(game), ticked)
    assert ticked not in registry.player_snapshot(ada(game)).ticks


def test_a_queued_claim_is_judged_at_close_on_what_the_player_has_ticked_then(table):
    registry, game, tickets = table
    draw_everything(registry, game)
    tick_five(registry, game, tickets["Ada"], ada(game))
    registry.claim(ada(game), Prize.EARLY_FIVE)
    registry.claim(grace(game), Prize.EARLY_FIVE)

    ((outcome,)) = registry.settle()
    (settled,) = outcome.settled

    assert settled.awarded_to == ("Ada",)
    assert settled.refused == ("Grace",)
    assert [(r.player, r.accepted) for r in registry.host_snapshot(game).claims] == [
        ("Ada", True),
        ("Grace", False),
    ]


def test_a_full_house_ends_the_game_when_its_window_closes_with_every_winner(table):
    registry, game, tickets = table
    draw_everything(registry, game)
    for name, who in (("Ada", ada(game)), ("Grace", grace(game))):
        for topic in names_on(tickets[name]):
            registry.tick(who, topic)

    registry.claim(ada(game), Prize.FULL_HOUSE)
    registry.claim(grace(game), Prize.FULL_HOUSE)
    # The window is still open, so the game is still running.
    with pytest.raises(SettlementWindowOpen):
        registry.draw(game)
    ((outcome,)) = registry.settle()  # one close reports once, for every winner

    assert outcome.settled[0].awarded_to == ("Ada", "Grace")
    assert outcome.ended == "full_house"
    assert registry.host_snapshot(game).status == "ended"
    with pytest.raises(GameAlreadyEnded):
        registry.draw(game)


def test_a_window_still_open_when_the_full_house_ends_the_game_refuses_its_claims(table):
    registry, game, tickets = table
    draw_everything(registry, game)
    for name, who in (("Ada", ada(game)), ("Grace", grace(game))):
        for topic in names_on(tickets[name]):
            registry.tick(who, topic)
    registry.claim(ada(game), Prize.EARLY_FIVE)
    registry.claim(grace(game), Prize.FULL_HOUSE)
    registry.scheduler.pending.reverse()  # the full house window's timer fires first
    (outcome,) = registry.settle()  # the early five's own timer later finds nothing to settle
    full_house, early_five = outcome.settled

    assert full_house.awarded_to == ("Grace",)
    assert early_five.awarded_to == ()
    assert early_five.refused == ("Ada",)
    # An ended game has no open window, so the host is told it closed.
    assert outcome.window_open is False
    assert registry.host_snapshot(game).window_open is False
