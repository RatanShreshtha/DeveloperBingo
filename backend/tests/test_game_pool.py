import random

from helpers import ManualScheduler, start_and_draw_everything

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry, PlayerRef
from devbingo_backend.pool import Topic, build_pool


def custom_pool(prefix: str):
    """A valid pool whose topics are named differently from the default pool's."""
    return build_pool(
        [
            Topic(f"{prefix}{number:02}", f"{prefix}{number:02} explained")
            for number in range(90)
        ]
    )


def test_a_game_deals_tickets_from_the_pool_it_was_created_with():
    pool = custom_pool("Alpha")
    registry = GameRegistry(scheduler=ManualScheduler(), rng=random.Random(3))
    game = registry.create_game(pool)

    ticket = registry.join(PlayerRef(game.code, "Ada")).snapshot.ticket

    assert ticket.topic_names() <= {topic.name for topic in pool.topics}


def test_a_game_draws_from_the_pool_it_was_created_with():
    pool = custom_pool("Alpha")
    registry = GameRegistry(scheduler=ManualScheduler(), rng=random.Random(3))
    game = registry.create_game(pool)
    registry.join(PlayerRef(game.code, "Ada"))

    start_and_draw_everything(registry, game)

    drawn = {draw.topic.name for draw in registry.host_snapshot(game).draws}
    assert drawn == {topic.name for topic in pool.topics}
    assert drawn.isdisjoint(topic.name for topic in DEFAULT_POOL.topics)


def test_two_games_keep_their_own_pools():
    registry = GameRegistry(scheduler=ManualScheduler(), rng=random.Random(3))
    alpha = registry.create_game(custom_pool("Alpha"))
    beta = registry.create_game(custom_pool("Beta"))

    alpha_ticket = registry.join(PlayerRef(alpha.code, "Ada")).snapshot.ticket
    beta_ticket = registry.join(PlayerRef(beta.code, "Ada")).snapshot.ticket

    assert all(name.startswith("Alpha") for name in alpha_ticket.topic_names())
    assert all(name.startswith("Beta") for name in beta_ticket.topic_names())


def test_the_registry_reports_the_pool_a_game_was_created_with():
    pool = custom_pool("Alpha")
    registry = GameRegistry(scheduler=ManualScheduler(), rng=random.Random(3))
    game = registry.create_game(pool)

    assert registry.host_snapshot(game).pool is pool
