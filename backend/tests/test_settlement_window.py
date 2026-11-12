import random

import pytest
from helpers import draw_everything, names_on

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    ClaimNotValid,
    ClaimPending,
    GameAlreadyEnded,
    GameRegistry,
    NoTopicsLeft,
    PlayerRef,
    SettlementWindowOpen,
)
from devbingo_backend.prizes import Prize


@pytest.fixture
def table():
    registry = GameRegistry(rng=random.Random(7))
    game = registry.create_game(DEFAULT_POOL)
    tickets = {
        name: registry.join(PlayerRef(game.code, name)).ticket for name in ("Ada", "Grace")
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

    pending = registry.claim(ada(game), Prize.EARLY_FIVE)

    assert pending.opened_window is True
    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == []


def test_two_claims_in_one_window_win_the_prize_together(table):
    registry, game, tickets = table
    draw_all_and_tick_five(registry, game, tickets)
    registry.claim(ada(game), Prize.EARLY_FIVE)

    second = registry.claim(grace(game), Prize.EARLY_FIVE)
    settled = registry.close_window(game.code, Prize.EARLY_FIVE)

    assert second.opened_window is False
    assert settled.awarded_to == ("Ada", "Grace")
    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == ["Ada", "Grace"]


def test_an_invalid_claim_is_refused_and_opens_no_window(table):
    registry, game, tickets = table
    registry.draw(game)

    with pytest.raises(ClaimNotValid):
        registry.claim(ada(game), Prize.EARLY_FIVE)

    registry.draw(game)


def test_draws_are_refused_while_a_window_is_open_and_resume_after_it_closes(table):
    registry, game, tickets = table
    draw_all_and_tick_five(registry, game, tickets)
    registry.claim(ada(game), Prize.EARLY_FIVE)

    with pytest.raises(SettlementWindowOpen):
        registry.draw(game)
    registry.close_window(game.code, Prize.EARLY_FIVE)

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
    assert ticked in registry.ticks(ada(game))

    registry.close_window(game.code, Prize.EARLY_FIVE)
    registry.untick(ada(game), ticked)
    assert ticked not in registry.ticks(ada(game))


def test_a_queued_claim_is_judged_at_close_on_what_the_player_has_ticked_then(table):
    registry, game, tickets = table
    draw_everything(registry, game)
    tick_five(registry, game, tickets["Ada"], ada(game))
    registry.claim(ada(game), Prize.EARLY_FIVE)
    registry.claim(grace(game), Prize.EARLY_FIVE)

    settled = registry.close_window(game.code, Prize.EARLY_FIVE)

    assert settled.awarded_to == ("Ada",)
    assert settled.refused == ("Grace",)
    assert [(r.player, r.accepted) for r in registry.claim_log(game.code)] == [
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
    settled = registry.close_window(game.code, Prize.FULL_HOUSE)

    assert settled.awarded_to == ("Ada", "Grace")
    assert settled.ends_game is True
    with pytest.raises(GameAlreadyEnded):
        registry.draw(game)


def test_closing_a_window_that_is_not_open_does_nothing(table):
    registry, game, _ = table

    assert registry.close_window(game.code, Prize.EARLY_FIVE) is None


def test_a_window_still_open_when_the_full_house_ends_the_game_refuses_its_claims(table):
    registry, game, tickets = table
    draw_everything(registry, game)
    for name, who in (("Ada", ada(game)), ("Grace", grace(game))):
        for topic in names_on(tickets[name]):
            registry.tick(who, topic)
    registry.claim(ada(game), Prize.EARLY_FIVE)
    registry.claim(grace(game), Prize.FULL_HOUSE)
    registry.close_window(game.code, Prize.FULL_HOUSE)

    settled = registry.close_window(game.code, Prize.EARLY_FIVE)

    assert settled.awarded_to == ()
    assert settled.refused == ("Ada",)
