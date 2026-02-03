"""In-memory session storage for Zoyd.

Provides in-memory storage for testing and development.
Data is lost when the storage instance is garbage collected.
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
from .interfaces import SessionStorage


class InMemoryStorage(SessionStorage):
    """In-memory session storage for testing.

    Stores all session data in Python dictionaries. Data is lost when
    the storage instance is garbage collected.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        self._sessions: dict[str, Session] = {}

    def create_session(self, metadata: SessionMetadata) -> str:
        """Create a new session in memory.

        Args:
            metadata: Session metadata.

        Returns:
            Session ID of the created session.
        """
        session = Session(
            metadata=metadata,
            statistics=SessionStatistics(),
            events=[],
            outputs=[],
            transitions=[],
            commits=[],
        )
        self._sessions[metadata.session_id] = session
        return metadata.session_id

    def end_session(
        self, session_id: str, ended_at: str | None = None
    ) -> None:
        """Mark a session as ended.

        Args:
            session_id: ID of the session to end.
            ended_at: ISO timestamp when session ended (default: now).
        """
        if session_id in self._sessions:
            if ended_at is None:
                ended_at = datetime.now().isoformat()
            self._sessions[session_id].metadata.ended_at = ended_at

    def get_session(self, session_id: str) -> Session | None:
        """Get a full session by ID.

        Args:
            session_id: ID of the session to retrieve.

        Returns:
            Session object or None if not found.
        """
        return self._sessions.get(session_id)

    def get_metadata(self, session_id: str) -> SessionMetadata | None:
        """Get session metadata by ID.

        Args:
            session_id: ID of the session.

        Returns:
            SessionMetadata or None if not found.
        """
        session = self._sessions.get(session_id)
        if session:
            return session.metadata
        return None

    def update_statistics(
        self, session_id: str, statistics: SessionStatistics
    ) -> None:
        """Update session statistics.

        Args:
            session_id: ID of the session.
            statistics: New statistics to store.
        """
        if session_id in self._sessions:
            self._sessions[session_id].statistics = statistics

    def add_event(self, session_id: str, event: SessionEvent) -> None:
        """Add an event to a session.

        Args:
            session_id: ID of the session.
            event: Event to add.
        """
        if session_id in self._sessions:
            self._sessions[session_id].events.append(event)

    def add_output(self, session_id: str, output: ClaudeOutput) -> None:
        """Add a Claude output to a session.

        Args:
            session_id: ID of the session.
            output: Output to add.
        """
        if session_id in self._sessions:
            self._sessions[session_id].outputs.append(output)

    def add_transition(
        self, session_id: str, transition: TaskTransition
    ) -> None:
        """Add a task transition to a session.

        Args:
            session_id: ID of the session.
            transition: Transition to add.
        """
        if session_id in self._sessions:
            self._sessions[session_id].transitions.append(transition)

    def add_commit(self, session_id: str, commit: GitCommitRecord) -> None:
        """Add a git commit record to a session.

        Args:
            session_id: ID of the session.
            commit: Commit record to add.
        """
        if session_id in self._sessions:
            self._sessions[session_id].commits.append(commit)

    def list_sessions(
        self, limit: int | None = None, offset: int = 0
    ) -> list[SessionMetadata]:
        """List session metadata.

        Args:
            limit: Maximum number of sessions to return (None for all).
            offset: Number of sessions to skip.

        Returns:
            List of SessionMetadata, newest first by started_at.
        """
        all_metadata = [s.metadata for s in self._sessions.values()]
        # Sort by started_at descending (newest first)
        all_metadata.sort(key=lambda m: m.started_at, reverse=True)
        # Apply offset
        all_metadata = all_metadata[offset:]
        # Apply limit
        if limit is not None:
            all_metadata = all_metadata[:limit]
        return all_metadata

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data.

        Args:
            session_id: ID of the session to delete.

        Returns:
            True if session was deleted, False if not found.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all sessions from memory (for testing)."""
        self._sessions.clear()