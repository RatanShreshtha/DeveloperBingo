import socket


def unused_database_url() -> str:
    """A database URL pointing at a port nothing is listening on."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"postgresql+psycopg://bingo:bingo@127.0.0.1:{port}/devbingo"
