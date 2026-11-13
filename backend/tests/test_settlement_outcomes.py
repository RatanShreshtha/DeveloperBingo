"""The outcomes the engine hands back when windows settle, so callers never diff the claim log."""

import random

import pytest
from helpers import ManualRegistry, draw_everything, names_on

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import ClaimNotValid, Outcome, PlayerRef
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimRecord
from devbingo_backend.errors import ErrorCode


@pytest.fixture
def table():
    registry = ManualRegistry(rng=random.Random(7))
    game = registry.create_game(DEFAULT_POOL)
    tickets = {
        name: registry.join(PlayerRef(game.code, name)).snapshot.ticket for name in ("Ada", "Grace")
    }
    registry.start(game)
    draw_everything(registry, game)
    for name, ticket in tickets.items():
        for topic in names_on(ticket)[:5]:
            registry.tick(PlayerRef(game.code, name), topic)
    return registry, game


def player(game, name):
    return PlayerRef(game.code, name)


def test_closing_a_window_returns_each_claimants_outcome(table):
    registry, game = table
    registry.claim(player(game, "Ada"), Prize.EARLY_FIVE)
    registry.claim(player(game, "Grace"), Prize.EARLY_FIVE)

    ((outcome,)) = registry.settle()
    (settled,) = outcome.settled

    assert settled.records == (
        ClaimRecord("Ada", Prize.EARLY_FIVE, accepted=True),
        ClaimRecord("Grace", Prize.EARLY_FIVE, accepted=True),
    )


def test_ending_the_game_settles_every_open_window_as_refused_game_ended(table):
    registry, game = table
    registry.claim(player(game, "Ada"), Prize.EARLY_FIVE)
    registry.claim(player(game, "Grace"), Prize.EARLY_FIVE)

    outcome = registry.end(game)
    settled = outcome.settled

    ended = ErrorCode.GAME_ENDED
    assert outcome.ended == "host"
    assert outcome.window_open is False
    assert [s.prize for s in settled] == [Prize.EARLY_FIVE]
    assert settled[0].awarded_to == ()
    assert settled[0].records == (
        ClaimRecord("Ada", Prize.EARLY_FIVE, accepted=False, error=ended),
        ClaimRecord("Grace", Prize.EARLY_FIVE, accepted=False, error=ended),
    )
    assert registry.host_snapshot(game).claims == settled[0].records
    assert registry.host_snapshot(game).prizes[Prize.EARLY_FIVE] == ()


def test_ending_a_game_with_no_open_window_settles_nothing(table):
    registry, game = table

    # No window was open, so the host is not told of a window change either.
    assert registry.end(game) == Outcome(ended="host")


def test_a_claim_refused_outright_reports_its_logged_record_in_the_outcome(table):
    registry, game = table

    result = registry.claim(player(game, "Ada"), Prize.FULL_HOUSE)

    assert isinstance(result.refusal, ClaimNotValid)
    assert result.outcome.decided == tuple(registry.host_snapshot(game).claims)
    assert result.outcome.settled == ()
