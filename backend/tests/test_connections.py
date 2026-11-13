"""Which connection holds which player, with no sockets and no game."""

import pytest

from devbingo_backend.connections import Connections
from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.errors import AlreadyJoined, NotJoined
from devbingo_backend.game import GameRegistry, PlayerRef

ADA = PlayerRef("ABC123", "Ada")
GRACE = PlayerRef("ABC123", "Grace")


def test_a_first_connection_replaces_nothing_and_is_the_players():
    connections = Connections()

    assert connections.attach("sid-1", ADA) == ()
    assert connections.player_on("sid-1") == ADA
    assert connections.held_by(ADA) == ("sid-1",)
    assert connections.is_connected(ADA)


def test_a_new_connection_replaces_the_old_one():
    connections = Connections()
    connections.attach("sid-1", ADA)

    assert connections.attach("sid-2", ADA) == ("sid-1",)

    assert connections.held_by(ADA) == ("sid-2",)
    with pytest.raises(NotJoined):
        connections.player_on("sid-1")


def test_the_late_drop_of_a_replaced_connection_changes_nothing():
    connections = Connections()
    connections.attach("sid-1", ADA)
    connections.attach("sid-2", ADA)

    assert connections.detach("sid-1") is None

    assert connections.is_connected(ADA)


def test_dropping_the_current_connection_leaves_the_player_not_connected():
    connections = Connections()
    connections.attach("sid-1", ADA)

    assert connections.detach("sid-1") == ADA

    assert not connections.is_connected(ADA)


def test_a_connection_that_never_joined_drops_to_nothing():
    assert Connections().detach("sid-9") is None


def test_each_player_keeps_their_own_connection():
    connections = Connections()
    connections.attach("sid-1", ADA)
    connections.attach("sid-2", GRACE)

    connections.drop_player(ADA)

    assert not connections.is_connected(ADA)
    assert connections.held_by(GRACE) == ("sid-2",)


@pytest.fixture
def registry():
    return GameRegistry()


def test_the_engine_refuses_a_second_join_on_the_same_connection(registry):
    game = registry.create_game(DEFAULT_POOL)
    registry.join(PlayerRef(game.code, "Ada"), connection="sid-1")

    with pytest.raises(AlreadyJoined):
        registry.join(PlayerRef(game.code, "Grace"), connection="sid-1")


def test_the_engine_names_the_connection_a_takeover_replaced(registry):
    game = registry.create_game(DEFAULT_POOL)
    ada = PlayerRef(game.code, "Ada")
    first = registry.join(ada, connection="sid-1")

    second = registry.join(ada, first.rejoin_token, connection="sid-2")

    assert second.replaced == ("sid-1",)
    assert registry.connections_of(ada) == ("sid-2",)
    registry.drop("sid-1")
    assert registry.connections_of(ada) == ("sid-2",)


def test_a_dropped_player_can_rejoin_by_name_and_replaces_nothing(registry):
    game = registry.create_game(DEFAULT_POOL)
    ada = PlayerRef(game.code, "Ada")
    registry.join(ada, connection="sid-1")
    registry.drop("sid-1")

    assert registry.join(ada, connection="sid-2").replaced == ()


def test_the_engine_knows_who_joined_over_a_connection(registry):
    game = registry.create_game(DEFAULT_POOL)
    registry.join(PlayerRef(game.code, "ada"), connection="sid-1")

    assert registry.player_on("sid-1") == PlayerRef(game.code, "ada")
    with pytest.raises(NotJoined):
        registry.player_on("sid-2")
