"""The Game snapshot the engine hands a player or the host: everything needed to show the game from
scratch, in one call. No sockets are involved; the wire forms are checked in test_session_recovery.py."""

import random

import pytest
from helpers import ManualScheduler, names_on, start_and_draw_everything

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry, HostLink, NotAPlayer, NotHost, PlayerRef
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimRecord

OPEN_BOARD = {prize: () for prize in Prize}


@pytest.fixture
def scheduler():
    return ManualScheduler()


@pytest.fixture
def registry(scheduler):
    return GameRegistry(rng=random.Random(5), scheduler=scheduler)


@pytest.fixture
def game(registry):
    return registry.create_game(DEFAULT_POOL, pool_name="Default")


def ada(game):
    return PlayerRef(game.code, "Ada")


def ready_to_claim(registry, game):
    """Ada has joined, every topic is drawn and she has ticked her whole ticket."""
    ticket = registry.join(ada(game)).snapshot.ticket
    start_and_draw_everything(registry, game)
    for topic in names_on(ticket):
        registry.tick(ada(game), topic)


def test_a_player_joining_a_game_in_the_lobby_sees_its_status_and_players(registry, game):
    registry.join(PlayerRef(game.code, "Grace"))

    snapshot = registry.join(ada(game)).snapshot

    assert snapshot.status == "lobby"
    assert snapshot.end_reason is None
    assert snapshot.players == ("Grace", "Ada")
    assert snapshot.draws == ()
    assert dict(snapshot.prizes) == OPEN_BOARD
    assert snapshot.player == ada(game)
    assert snapshot.ticks == frozenset()
    assert snapshot.pending_claims == ()
    assert snapshot.decided_claims == ()


def test_a_rejoin_between_the_start_and_the_first_draw_knows_the_game_started(registry, game):
    registry.join(ada(game))
    registry.start(game)
    registry.disconnect(ada(game))

    snapshot = registry.join(ada(game)).snapshot

    assert snapshot.status == "started"
    assert snapshot.draws == ()


def test_a_snapshot_carries_every_draw_in_order(registry, game):
    registry.join(ada(game))
    registry.start(game)
    first, second = registry.draw(game), registry.draw(game)

    assert registry.player_snapshot(ada(game)).draws == (first, second)


def test_the_hosts_snapshot_carries_status_players_draws_pool_and_claim_log(registry, game):
    registry.join(ada(game))
    registry.start(game)
    registry.draw(game)

    snapshot = registry.host_snapshot(game)

    assert snapshot.status == "started"
    assert snapshot.players == ("Ada",)
    assert len(snapshot.draws) == 1
    assert snapshot.claims == ()
    assert snapshot.window_open is False
    assert snapshot.pool is DEFAULT_POOL
    assert snapshot.pool_name == "Default"


def test_a_snapshot_after_the_game_ends_says_why_and_shows_the_final_prize_board(registry, game):
    registry.join(ada(game))
    registry.start(game)
    registry.end(game)

    snapshot = registry.host_snapshot(game)

    assert snapshot.status == "ended"
    assert snapshot.end_reason == "host"
    assert dict(snapshot.prizes) == OPEN_BOARD


def test_while_a_claim_waits_the_host_sees_the_window_and_the_player_sees_it_pending(registry, game):
    ready_to_claim(registry, game)
    registry.claim(ada(game), Prize.EARLY_FIVE)

    assert registry.host_snapshot(game).window_open is True
    player = registry.player_snapshot(ada(game))
    assert player.pending_claims == (Prize.EARLY_FIVE,)
    assert player.decided_claims == ()


def test_once_the_window_closes_the_player_sees_their_decided_claim(registry, game, scheduler):
    ready_to_claim(registry, game)
    registry.claim(ada(game), Prize.EARLY_FIVE)

    scheduler.close_all()

    player = registry.player_snapshot(ada(game))
    assert player.pending_claims == ()
    assert player.decided_claims == (ClaimRecord("Ada", Prize.EARLY_FIVE, accepted=True),)
    assert player.prizes[Prize.EARLY_FIVE] == ("Ada",)
    assert registry.host_snapshot(game).claims == player.decided_claims


def test_a_snapshot_does_not_change_as_the_game_goes_on(registry, game):
    registry.join(ada(game))
    before = registry.host_snapshot(game)

    registry.join(PlayerRef(game.code, "Grace"))
    registry.start(game)
    registry.draw(game)

    assert (before.status, before.players, before.draws) == ("lobby", ("Ada",), ())


def test_only_the_host_gets_the_hosts_snapshot(registry, game):
    with pytest.raises(NotHost):
        registry.host_snapshot(HostLink(code=game.code, host_token="not-the-host-token"))


def test_only_a_player_in_the_game_gets_a_players_snapshot(registry, game):
    with pytest.raises(NotAPlayer):
        registry.player_snapshot(PlayerRef(game.code, "Nobody"))
