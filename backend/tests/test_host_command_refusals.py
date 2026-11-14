"""How the host commands answer: a game error becomes a refusal to the sender, a malformed payload
is refused as invalid, and anything that is not a game error is not swallowed."""

import pytest
from helpers import RealtimeTable, host_message, run

from devbingo_backend.game import HostLink


@pytest.mark.parametrize("command", ["start_game", "draw_topic", "end_game"])
def test_a_malformed_host_payload_is_refused_as_invalid(command):
    table = RealtimeTable()
    ack = run(getattr(table.adapter, command)("sid-host", {"code": 5}))
    assert ack == {"ok": False, "error": "invalid_message"}


@pytest.mark.parametrize("command", ["start_game", "draw_topic", "end_game"])
def test_a_wrong_host_token_is_refused_as_not_host(command):
    table = RealtimeTable()
    wrong = HostLink(code=table.game.code, host_token="not-the-host-token")
    ack = run(getattr(table.adapter, command)("sid-host", host_message(wrong)))
    assert ack == {"ok": False, "error": "not_host"}


@pytest.mark.parametrize("command", ["start_game", "draw_topic", "end_game"])
def test_an_error_that_is_not_a_game_error_is_not_turned_into_a_refusal(
    command, monkeypatch
):
    table = RealtimeTable()
    registry_method = {
        "start_game": "start",
        "draw_topic": "draw",
        "end_game": "end",
    }[command]

    def broken(_host):
        raise RuntimeError("a bug, not a rule")

    monkeypatch.setattr(table.registry, registry_method, broken)
    with pytest.raises(RuntimeError, match="a bug, not a rule"):
        run(getattr(table.adapter, command)("sid-host", host_message(table.game)))
