import threading
from typing import Any

from sqlmodel import Field, Session, SQLModel, select

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.pool import Pool, Topic, build_pool


class PoolRecord(SQLModel, table=True):
    __tablename__ = "pools"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    is_default: bool = False


class PoolTopicRecord(SQLModel, table=True):
    __tablename__ = "pool_topics"

    id: int | None = Field(default=None, primary_key=True)
    pool_id: int = Field(foreign_key="pools.id", index=True)
    position: int
    name: str
    explanation: str


DEFAULT_POOL_NAME = "Default"

# One process holds the app's state (ADR 0001), so a process-wide lock is
# enough to stop two first requests from seeding the default pool twice.
_seed_lock = threading.Lock()


def ensure_default_pool(engine: Any) -> None:
    """Create the tables if needed and seed the default pool once."""
    with _seed_lock:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            existing = session.exec(
                select(PoolRecord).where(PoolRecord.is_default == True)  # noqa: E712
            ).first()
            if existing is not None:
                return

            record = PoolRecord(name=DEFAULT_POOL_NAME, is_default=True)
            session.add(record)
            session.flush()
            for position, topic in enumerate(DEFAULT_POOL.topics):
                session.add(
                    PoolTopicRecord(
                        pool_id=record.id,
                        position=position,
                        name=topic.name,
                        explanation=topic.explanation,
                    )
                )
            session.commit()


def load_default_pool(engine: Any) -> Pool:
    """Read the seeded default pool back, validated, in list order."""
    with Session(engine) as session:
        record = session.exec(
            select(PoolRecord).where(PoolRecord.is_default == True)  # noqa: E712
        ).one()
        rows = session.exec(
            select(PoolTopicRecord)
            .where(PoolTopicRecord.pool_id == record.id)
            .order_by(PoolTopicRecord.position)
        ).all()
    return build_pool([Topic(row.name, row.explanation) for row in rows])
