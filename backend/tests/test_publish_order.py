"""The order in which `RealtimeAdapter.publish` announces an outcome. Each step is announced in the
order its docstring gives, to the audience it names."""

from helpers import RealtimeTable, run

from devbingo_backend.errors import ErrorCode
from devbingo_backend.game import Draw, GameSummary, Outcome
from devbingo_backend.pool import Topic
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimRecord, Settled


def test_publish_announces_every_part_of_an_outcome_in_the_documented_order():
    table = RealtimeTable()
    table.join("sid-ada", "Ada")
    table.broadcaster.sent.clear()  # the join's own lobby update is not under test

    code = table.game.code
    host = table.host
    refused = ClaimRecord("Ada", Prize.FULL_HOUSE, False, ErrorCode.CLAIM_NOT_VALID)
    settled_record = ClaimRecord("Ada", Prize.EARLY_FIVE, True)
    outcome = Outcome(
        lobby=("Ada",),
        started=True,
        drawn=Draw(1, Topic("Matrix", "A 1999 science-fiction film")),
        decided=(refused,),
        settled=(
            Settled(
                prize=Prize.EARLY_FIVE,
                awarded_to=("Ada",),
                records=(settled_record,),
            ),
        ),
        ended="host",
        window_open=False,
        summary=GameSummary(
            code=code,
            end_reason="host",
            pool_name=None,
            draws=(),
            claims=(),
            prizes={prize: () for prize in Prize},
        ),
    )

    run(table.adapter.publish(code, outcome))

    announced = [(event, target) for event, target, _ in table.broadcaster.sent]
    assert announced == [
        ("lobby_updated", code),  # the room hears the lobby change
        ("game_started", code),
        ("topic_drawn", code),
        ("claim_logged", host),  # the host hears each refused claim
        ("claim_logged", host),  # and each claim a closed window decided
        ("prize_awarded", code),  # then the prizes awarded
        ("game_ended", code),  # then the end
        ("claim_settled", "sid-ada"),  # each claimant hears their own result
        ("window_changed", host),  # the host hears the window state last
    ]
