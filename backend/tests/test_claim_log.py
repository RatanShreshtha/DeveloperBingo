import random

import pytest

from helpers import ManualRegistry, start_and_draw_everything
from test_claims import PRIZE_TOPICS, tick

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import PlayerRef
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimRecord
from devbingo_backend.errors import ErrorCode


@pytest.fixture
def table():
    registry = ManualRegistry(rng=random.Random(31))
    game = registry.create_game(DEFAULT_POOL)
    ada = registry.join(PlayerRef(game.code, "Ada")).snapshot.ticket
    registry.join(PlayerRef(game.code, "Grace"))
    return registry, game, ada


def attempt(registry, game, name, prize):
    try:
        registry.claim(PlayerRef(game.code, name), prize)
    except Exception:
        pass


def test_the_log_holds_accepted_and_refused_claims_in_order(table):
    registry, game, ada = table
    start_and_draw_everything(registry, game)
    tick(registry, game, "Ada", PRIZE_TOPICS[Prize.EARLY_FIVE](ada))

    attempt(registry, game, "Grace", Prize.EARLY_FIVE)
    attempt(registry, game, "Ada", Prize.EARLY_FIVE)
    assert registry.host_snapshot(game).claims == (
        ClaimRecord("Grace", Prize.EARLY_FIVE, False, ErrorCode.CLAIM_NOT_VALID),
    )  # Ada's claim is logged when its window settles, not before
    registry.settle()
    attempt(registry, game, "Grace", Prize.EARLY_FIVE)

    assert registry.host_snapshot(game).claims == (
        ClaimRecord("Grace", Prize.EARLY_FIVE, False, ErrorCode.CLAIM_NOT_VALID),
        ClaimRecord("Ada", Prize.EARLY_FIVE, True),
        ClaimRecord("Grace", Prize.EARLY_FIVE, False, ErrorCode.PRIZE_TAKEN),
    )


def test_a_claim_before_the_game_starts_is_logged_as_refused(table):
    registry, game, _ = table

    attempt(registry, game, "Ada", Prize.EARLY_FIVE)

    assert registry.host_snapshot(game).claims == (
        ClaimRecord("Ada", Prize.EARLY_FIVE, False, ErrorCode.NOT_STARTED),
    )


def test_a_claim_after_the_game_ends_is_logged_as_refused(table):
    registry, game, _ = table
    registry.start(game)
    registry.end(game)

    attempt(registry, game, "Ada", Prize.EARLY_FIVE)

    assert registry.host_snapshot(game).claims == (
        ClaimRecord("Ada", Prize.EARLY_FIVE, False, ErrorCode.GAME_ENDED),
    )


def test_a_claim_by_someone_who_is_not_a_player_is_not_logged(table):
    registry, game, _ = table
    registry.start(game)

    attempt(registry, game, "Stranger", Prize.EARLY_FIVE)

    assert registry.host_snapshot(game).claims == ()
