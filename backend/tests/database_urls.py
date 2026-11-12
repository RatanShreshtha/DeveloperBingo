import socket


def unused_database_url() -> str:
    """A database URL pointing at a port nothing is listening on."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"postgresql+psycopg://bingo:bingo@127.0.0.1:{port}/devbingo"


def database_is_reachable(url: str) -> bool:
    """Whether a Postgres server answers at this URL, so database tests can skip when it doesn't."""
    from sqlmodel import create_engine, text

    engine = create_engine(url, connect_args={"connect_timeout": 2})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return False
    finally:
        engine.dispose()
    return True
