"""The History Store: where ended games are kept, behind a port the app and the tests plug into."""

import threading
from typing import Any, Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Field, Session, SQLModel, col, select

from devbingo_backend.errors import ErrorCode
from devbingo_backend.game import Draw, GameSummary
from devbingo_backend.pool import Topic
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimRecord


class AlreadyStored(Exception):
    """A game with this code is already in the store. History is never overwritten."""


class HistoryUnavailable(Exception):
    """The store cannot be reached right now, so nothing can be saved or read."""


class HistoryStore(Protocol):
    """Ended games, kept by the game's code."""

    def save(self, summary: GameSummary) -> None:
        """Keep an ended game. Raises AlreadyStored if the code already has history, which is left
        as it was, and HistoryUnavailable if the store can't be written."""
        ...

    def exists(self, code: str) -> bool:
        """Whether a game with this code is stored. Raises HistoryUnavailable if it can't be read."""
        ...

    def load(self, code: str) -> GameSummary | None:
        """The ended game with this code, or None if none is stored.
        Raises HistoryUnavailable if the store can't be read."""
        ...


class InMemoryHistoryStore:
    """A store that keeps games in memory, with no database. For tests."""

    def __init__(self) -> None:
        self._games: dict[str, GameSummary] = {}

    def save(self, summary: GameSummary) -> None:
        if summary.code in self._games:
            raise AlreadyStored(summary.code)
        self._games[summary.code] = summary

    def exists(self, code: str) -> bool:
        return code in self._games

    def load(self, code: str) -> GameSummary | None:
        return self._games.get(code)


class GameHistoryRecord(SQLModel, table=True):
    __tablename__ = "game_histories"

    code: str = Field(primary_key=True)
    reason: str
    pool_name: str | None = None


class GameDrawRecord(SQLModel, table=True):
    __tablename__ = "game_history_draws"

    id: int | None = Field(default=None, primary_key=True)
    game_code: str = Field(foreign_key="game_histories.code", index=True)
    position: int
    name: str
    explanation: str


class GameClaimRecord(SQLModel, table=True):
    __tablename__ = "game_history_claims"

    id: int | None = Field(default=None, primary_key=True)
    game_code: str = Field(foreign_key="game_histories.code", index=True)
    # Where the claim sits in the claim log, so the order survives.
    sequence: int
    player: str
    prize: str
    accepted: bool
    error: str | None = None


class GameWinnerRecord(SQLModel, table=True):
    __tablename__ = "game_history_winners"

    id: int | None = Field(default=None, primary_key=True)
    game_code: str = Field(foreign_key="game_histories.code", index=True)
    prize: str
    sequence: int
    player: str


_TABLES = [
    GameHistoryRecord.__table__,
    GameDrawRecord.__table__,
    GameClaimRecord.__table__,
    GameWinnerRecord.__table__,
]

# One process holds the app's state (ADR 0001), so a process-wide lock is enough.
_create_lock = threading.Lock()


class PostgresHistoryStore:
    """The store the app uses: ended games kept in Postgres, tables created on first use."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._ready = False

    def _ensure_tables(self) -> None:
        with _create_lock:
            if not self._ready:
                SQLModel.metadata.create_all(self._engine, tables=_TABLES)
                self._ready = True

    def save(self, summary: GameSummary) -> None:
        try:
            self._ensure_tables()
            with Session(self._engine) as session:
                if session.get(GameHistoryRecord, summary.code) is not None:
                    raise AlreadyStored(summary.code)
                session.add(
                    GameHistoryRecord(
                        code=summary.code, reason=summary.end_reason, pool_name=summary.pool_name
                    )
                )
                session.flush()
                for draw in summary.draws:
                    session.add(
                        GameDrawRecord(
                            game_code=summary.code,
                            position=draw.position,
                            name=draw.topic.name,
                            explanation=draw.topic.explanation,
                        )
                    )
                for sequence, claim in enumerate(summary.claims):
                    session.add(
                        GameClaimRecord(
                            game_code=summary.code,
                            sequence=sequence,
                            player=claim.player,
                            prize=claim.prize.value,
                            accepted=claim.accepted,
                            error=claim.error.value if claim.error else None,
                        )
                    )
                for prize, players in summary.prizes.items():
                    for sequence, player in enumerate(players):
                        session.add(
                            GameWinnerRecord(
                                game_code=summary.code,
                                prize=prize.value,
                                sequence=sequence,
                                player=player,
                            )
                        )
                session.commit()
        except SQLAlchemyError:
            raise HistoryUnavailable from None

    def exists(self, code: str) -> bool:
        try:
            self._ensure_tables()
            with Session(self._engine) as session:
                return session.get(GameHistoryRecord, code) is not None
        except SQLAlchemyError:
            raise HistoryUnavailable from None

    def load(self, code: str) -> GameSummary | None:
        try:
            self._ensure_tables()
            with Session(self._engine) as session:
                game = session.get(GameHistoryRecord, code)
                if game is None:
                    return None
                draws = session.exec(
                    select(GameDrawRecord)
                    .where(GameDrawRecord.game_code == code)
                    .order_by(col(GameDrawRecord.position))
                ).all()
                claims = session.exec(
                    select(GameClaimRecord)
                    .where(GameClaimRecord.game_code == code)
                    .order_by(col(GameClaimRecord.sequence))
                ).all()
                winner_rows = session.exec(
                    select(GameWinnerRecord)
                    .where(GameWinnerRecord.game_code == code)
                    .order_by(col(GameWinnerRecord.sequence))
                ).all()
        except SQLAlchemyError:
            raise HistoryUnavailable from None
        prizes: dict[Prize, tuple[str, ...]] = {
            prize: tuple(row.player for row in winner_rows if row.prize == prize.value)
            for prize in Prize
        }
        return GameSummary(
            code=game.code,
            end_reason=game.reason,  # type: ignore[arg-type]
            pool_name=game.pool_name,
            draws=tuple(Draw(row.position, Topic(row.name, row.explanation)) for row in draws),
            claims=tuple(
                ClaimRecord(
                    row.player,
                    Prize(row.prize),
                    row.accepted,
                    ErrorCode(row.error) if row.error else None,
                )
                for row in claims
            ),
            prizes=prizes,
        )
