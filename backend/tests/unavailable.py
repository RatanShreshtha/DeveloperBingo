from collections.abc import Sequence

from devbingo_backend.pool import Pool, Topic
from devbingo_backend.pool_library import PoolLibraryUnavailable


class UnavailablePoolLibrary:
    """A Pool Library that cannot be reached, for testing how callers cope."""

    def load_default(self) -> Pool:
        raise PoolLibraryUnavailable

    def save(self, name: str, topics: Sequence[Topic]):
        raise PoolLibraryUnavailable

    def list_pools(self):
        raise PoolLibraryUnavailable

    def get(self, pool_id: int):
        raise PoolLibraryUnavailable
