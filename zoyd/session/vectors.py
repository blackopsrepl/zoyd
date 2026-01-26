"""Vector memory for Zoyd semantic search.

Uses Redis 8.0 native VSET commands (VADD, VSIM, VREM, VINFO, VCARD)
to store and retrieve embeddings for iteration outputs, task descriptions,
and error patterns. Metadata is stored as JSON at separate keys.
"""

from __future__ import annotations

from typing import Any

from zoyd.session.embedding import EmbeddingProvider


# Redis key names for the three vector sets
OUTPUTS_KEY = "zoyd:vectors:outputs"
TASKS_KEY = "zoyd:vectors:tasks"
ERRORS_KEY = "zoyd:vectors:errors"

# Prefix for per-element metadata keys (JSON stored at zoyd:vectors:meta:{element_id})
META_PREFIX = "zoyd:vectors:meta:"


class VectorMemory:
    """Semantic memory backed by Redis 8.0 vector sets.

    Stores embeddings in three vector sets (outputs, tasks, errors)
    and associated metadata as JSON strings at separate Redis keys.
    All operations use ``client.execute_command()`` since the ``redis``
    Python package does not have native VSET wrappers.

    Args:
        host: Redis server hostname.
        port: Redis server port.
        db: Redis database number.
        password: Redis password.
        provider: Embedding provider for generating vectors.
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.provider = provider
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazily create the Redis client."""
        if self._client is None:
            import redis

            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
            )
        return self._client
