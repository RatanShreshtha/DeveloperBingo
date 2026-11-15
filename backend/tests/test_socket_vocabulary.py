"""The socket vocabulary is declared once. Each server event names the message it carries, and every
such message is in the OpenAPI schema, so the generated frontend types cannot silently miss one."""

from devbingo_backend.wire import SERVER_MESSAGES, SOCKET_MODELS, ServerEvent


def test_every_server_event_names_the_message_it_carries():
    assert set(SERVER_MESSAGES) == set(ServerEvent)


def test_every_message_a_server_event_carries_is_in_the_openapi_schema():
    assert set(SERVER_MESSAGES.values()) <= set(SOCKET_MODELS)
