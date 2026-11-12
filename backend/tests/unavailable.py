from devbingo_backend.pool import Pool
from devbingo_backend.pool_library import PoolLibraryUnavailable


class UnavailablePoolLibrary:
    """A Pool Library that cannot be reached, for testing how callers cope."""

    def load_default(self) -> Pool:
        raise PoolLibraryUnavailable
