"""Vector memory for Zoyd semantic search.

Uses Redis 8.0 native VSET commands (VADD, VSIM, VREM, VINFO, VCARD)
to store and retrieve embeddings for iteration outputs, task descriptions,
and error patterns. Metadata is stored as JSON at separate keys.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
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

    def store_output(
        self,
        session_id: str,
        iteration: int,
        output: str,
        task_text: str,
        return_code: int,
    ) -> str | None:
        """Store an iteration output embedding and metadata.

        Generates a unique element ID, embeds the output text via the
        provider, adds it to the outputs vector set with ``VADD``, and
        stores JSON metadata at ``zoyd:vectors:meta:{element_id}``.

        Args:
            session_id: The current session identifier.
            iteration: Iteration number within the session.
            output: Full Claude output text for this iteration.
            task_text: The task being worked on.
            return_code: Claude process return code.

        Returns:
            The element ID if stored successfully, or ``None`` on failure.
        """
        element_id = f"output:{session_id}:{iteration}:{uuid.uuid4().hex[:8]}"
        vector = self.provider.embed(output)

        # VADD key FP32 element_id V1 V2 ... Vn
        self.client.execute_command(
            "VADD", OUTPUTS_KEY, "FP32", element_id, *vector,
        )

        # Store metadata as JSON at a separate key
        metadata = {
            "session_id": session_id,
            "iteration": iteration,
            "task_text": task_text,
            "output_preview": output[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "return_code": return_code,
        }
        self.client.set(
            f"{META_PREFIX}{element_id}", json.dumps(metadata),
        )

        return element_id

    def store_task(
        self,
        session_id: str,
        task_text: str,
        line_number: int,
    ) -> str | None:
        """Store a task description embedding and metadata.

        Generates a unique element ID, embeds the task text via the
        provider, adds it to the tasks vector set with ``VADD``, and
        stores JSON metadata at ``zoyd:vectors:meta:{element_id}``.

        Args:
            session_id: The current session identifier.
            task_text: The task description text.
            line_number: Line number of the task in the PRD file.

        Returns:
            The element ID if stored successfully, or ``None`` on failure.
        """
        element_id = f"task:{session_id}:{line_number}:{uuid.uuid4().hex[:8]}"
        vector = self.provider.embed(task_text)

        # VADD key FP32 element_id V1 V2 ... Vn
        self.client.execute_command(
            "VADD", TASKS_KEY, "FP32", element_id, *vector,
        )

        # Store metadata as JSON at a separate key
        metadata = {
            "session_id": session_id,
            "task_text": task_text,
            "line_number": line_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.client.set(
            f"{META_PREFIX}{element_id}", json.dumps(metadata),
        )

        return element_id
