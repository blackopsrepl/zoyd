"""Redis-based session storage for Zoyd.

Provides Redis-backed storage for session data with efficient
sorted set indexing for session listing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from zoyd.session.models import (
    ClaudeOutput,
    GitCommitRecord,
    Session,
    SessionEvent,
    SessionMetadata,
    SessionStatistics,
    TaskTransition,
)
from .helpers import from_json, to_json
from .interfaces import SessionStorage


class RedisStorage(SessionStorage):
    """Redis-based session storage.

    Session data is stored in Redis using the following key structure:
    - zoyd:session:{id}:meta - JSON with metadata + statistics
    - zoyd:session:{id}:events - List of JSON event records
    - zoyd:session:{id}:outputs - List of JSON output records
    - zoyd:session:{id}:transitions - List of JSON transition records
    - zoyd:session:{id}:commits - List of JSON commit records
    - zoyd:sessions:index - Sorted set for listing (score=timestamp)

    The redis package is lazily imported to avoid ImportError when not using
    the Redis backend.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        key_prefix: str = "zoyd:",
    ) -> None:
        """Initialize Redis storage.

        Args:
            host: Redis server hostname.
            port: Redis server port.
            db: Redis database number.
            password: Redis password (None for no auth).
            key_prefix: Prefix for all Redis keys.
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.key_prefix = key_prefix
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazily get the Redis client.

        Returns:
            Redis client instance.

        Raises:
            ImportError: If redis package is not installed.
        """
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

    def _meta_key(self, session_id: str) -> str:
        """Get the Redis key for session metadata.

        Args:
            session_id: Session ID.

        Returns:
            Redis key string.
        """
        return f"{self.key_prefix}session:{session_id}:meta"

    def _events_key(self, session_id: str) -> str:
        """Get the Redis key for session events.

        Args:
            session_id: Session ID.

        Returns:
            Redis key string.
        """
        return f"{self.key_prefix}session:{session_id}:events"

    def _outputs_key(self, session_id: str) -> str:
        """Get the Redis key for session outputs.

        Args:
            session_id: Session ID.

        Returns:
            Redis key string.
        """
        return f"{self.key_prefix}session:{session_id}:outputs"

    def _transitions_key(self, session_id: str) -> str:
        """Get the Redis key for session transitions.

        Args:
            session_id: Session ID.

        Returns:
            Redis key string.
        """
        return f"{self.key_prefix}session:{session_id}:transitions"

    def _commits_key(self, session_id: str) -> str:
        """Get the Redis key for session commits.

        Args:
            session_id: Session ID.

        Returns:
            Redis key string.
        """
        return f"{self.key_prefix}session:{session_id}:commits"

    def _index_key(self) -> str:
        """Get the Redis key for the sessions index.

        Returns:
            Redis key string.
        """
        return f"{self.key_prefix}sessions:index"

    def create_session(self, metadata: SessionMetadata) -> str:
        """Create a new session in Redis.

        Uses SET for meta and ZADD for the index (score=timestamp).

        Args:
            metadata: Session metadata.

        Returns:
            Session ID of the created session.
        """
        session_id = metadata.session_id
        # Store metadata and empty statistics as JSON
        data = {
            "metadata": metadata.to_dict(),
            "statistics": SessionStatistics().to_dict(),
        }
        self.client.set(self._meta_key(session_id), to_json(data))
        # Add to index with timestamp as score for sorting
        timestamp = datetime.fromisoformat(metadata.started_at).timestamp()
        self.client.zadd(self._index_key(), {session_id: timestamp})
        return session_id

    def end_session(
        self, session_id: str, ended_at: str | None = None
    ) -> None:
        """Mark a session as ended by updating meta JSON with ended_at.

        Args:
            session_id: ID of the session to end.
            ended_at: ISO timestamp when session ended (default: now).
        """
        meta_json = self.client.get(self._meta_key(session_id))
        if meta_json is None:
            return
        data = from_json(meta_json)
        if ended_at is None:
            ended_at = datetime.now().isoformat()
        data["metadata"]["ended_at"] = ended_at
        self.client.set(self._meta_key(session_id), to_json(data))

    def get_metadata(self, session_id: str) -> SessionMetadata | None:
        """Get session metadata by ID.

        Uses GET to fetch and parse meta JSON.

        Args:
            session_id: ID of the session.

        Returns:
            SessionMetadata or None if not found.
        """
        meta_json = self.client.get(self._meta_key(session_id))
        if meta_json is None:
            return None
        data = from_json(meta_json)
        return SessionMetadata.from_dict(data.get("metadata", {}))

    def update_statistics(
        self, session_id: str, statistics: SessionStatistics
    ) -> None:
        """Update session statistics.

        Gets meta JSON, updates stats, and SETs back.

        Args:
            session_id: ID of the session.
            statistics: New statistics to store.
        """
        meta_json = self.client.get(self._meta_key(session_id))
        if meta_json is None:
            return
        data = from_json(meta_json)
        data["statistics"] = statistics.to_dict()
        self.client.set(self._meta_key(session_id), to_json(data))

    def add_event(self, session_id: str, event: SessionEvent) -> None:
        """Add an event to a session using RPUSH.

        Args:
            session_id: ID of the session.
            event: Event to add.
        """
        if self.client.exists(self._meta_key(session_id)):
            self.client.rpush(self._events_key(session_id), to_json(event))

    def add_output(self, session_id: str, output: ClaudeOutput) -> None:
        """Add a Claude output to a session using RPUSH.

        Args:
            session_id: ID of the session.
            output: Output to add.
        """
        if self.client.exists(self._meta_key(session_id)):
            self.client.rpush(self._outputs_key(session_id), to_json(output))

    def add_transition(
        self, session_id: str, transition: TaskTransition
    ) -> None:
        """Add a task transition to a session using RPUSH.

        Args:
            session_id: ID of the session.
            transition: Transition to add.
        """
        if self.client.exists(self._meta_key(session_id)):
            self.client.rpush(
                self._transitions_key(session_id), to_json(transition)
            )

    def add_commit(self, session_id: str, commit: GitCommitRecord) -> None:
        """Add a git commit record to a session using RPUSH.

        Args:
            session_id: ID of the session.
            commit: Commit record to add.
        """
        if self.client.exists(self._meta_key(session_id)):
            self.client.rpush(self._commits_key(session_id), to_json(commit))

    def get_session(self, session_id: str) -> Session | None:
        """Get a full session by ID.

        Uses GET for meta and LRANGE 0 -1 for all lists.

        Args:
            session_id: ID of the session to retrieve.

        Returns:
            Session object or None if not found.
        """
        meta_json = self.client.get(self._meta_key(session_id))
        if meta_json is None:
            return None
        data = from_json(meta_json)
        metadata = SessionMetadata.from_dict(data.get("metadata", {}))
        statistics = SessionStatistics.from_dict(data.get("statistics", {}))

        # Get all items from lists
        events_json = self.client.lrange(self._events_key(session_id), 0, -1)
        outputs_json = self.client.lrange(self._outputs_key(session_id), 0, -1)
        transitions_json = self.client.lrange(
            self._transitions_key(session_id), 0, -1
        )
        commits_json = self.client.lrange(self._commits_key(session_id), 0, -1)

        return Session(
            metadata=metadata,
            statistics=statistics,
            events=[from_json(e, SessionEvent) for e in events_json],
            outputs=[from_json(o, ClaudeOutput) for o in outputs_json],
            transitions=[
                from_json(t, TaskTransition) for t in transitions_json
            ],
            commits=[from_json(c, GitCommitRecord) for c in commits_json],
        )

    def list_sessions(
        self, limit: int | None = None, offset: int = 0
    ) -> list[SessionMetadata]:
        """List session metadata using ZREVRANGE.

        Args:
            limit: Maximum number of sessions to return (None for all).
            offset: Number of sessions to skip.

        Returns:
            List of SessionMetadata, newest first.
        """
        # Get session IDs from sorted set (newest first)
        if limit is None:
            end = -1
        else:
            end = offset + limit - 1
        session_ids = self.client.zrevrange(self._index_key(), offset, end)

        result = []
        for session_id in session_ids:
            metadata = self.get_metadata(session_id)
            if metadata:
                result.append(metadata)
        return result

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data.

        Uses DEL for all keys and ZREM from index.

        Args:
            session_id: ID of the session to delete.

        Returns:
            True if session was deleted, False if not found.
        """
        meta_key = self._meta_key(session_id)
        if not self.client.exists(meta_key):
            return False

        # Delete all session keys
        self.client.delete(
            meta_key,
            self._events_key(session_id),
            self._outputs_key(session_id),
            self._transitions_key(session_id),
            self._commits_key(session_id),
        )
        # Remove from index
        self.client.zrem(self._index_key(), session_id)
        return True