"""Session storage interfaces for Zoyd.

Provides the abstract base class defining the storage interface for session data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
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


class SessionStorage(ABC):
    """Abstract base class for session storage backends.

    Defines the interface for storing and retrieving session data.
    Implementations can use different backends (memory, files, Redis, etc.).
    """

    @abstractmethod
    def create_session(self, metadata: SessionMetadata) -> str:
        """Create a new session.

        Args:
            metadata: Session metadata.

        Returns:
            Session ID of the created session.
        """
        pass

    @abstractmethod
    def end_session(
        self, session_id: str, ended_at: str | None = None
    ) -> None:
        """Mark a session as ended.

        Args:
            session_id: ID of the session to end.
            ended_at: ISO timestamp when session ended (default: now).
        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Session | None:
        """Get a full session by ID.

        Args:
            session_id: ID of the session to retrieve.

        Returns:
            Session object or None if not found.
        """
        pass

    @abstractmethod
    def get_metadata(self, session_id: str) -> SessionMetadata | None:
        """Get session metadata by ID.

        Args:
            session_id: ID of the session.

        Returns:
            SessionMetadata or None if not found.
        """
        pass

    @abstractmethod
    def update_statistics(
        self, session_id: str, statistics: SessionStatistics
    ) -> None:
        """Update session statistics.

        Args:
            session_id: ID of the session.
            statistics: New statistics to store.
        """
        pass

    @abstractmethod
    def add_event(self, session_id: str, event: SessionEvent) -> None:
        """Add an event to a session.

        Args:
            session_id: ID of the session.
            event: Event to add.
        """
        pass

    @abstractmethod
    def add_output(self, session_id: str, output: ClaudeOutput) -> None:
        """Add a Claude output to a session.

        Args:
            session_id: ID of the session.
            output: Output to add.
        """
        pass

    @abstractmethod
    def add_transition(
        self, session_id: str, transition: TaskTransition
    ) -> None:
        """Add a task transition to a session.

        Args:
            session_id: ID of the session.
            transition: Transition to add.
        """
        pass

    @abstractmethod
    def add_commit(self, session_id: str, commit: GitCommitRecord) -> None:
        """Add a git commit record to a session.

        Args:
            session_id: ID of the session.
            commit: Commit record to add.
        """
        pass

    @abstractmethod
    def list_sessions(
        self, limit: int | None = None, offset: int = 0
    ) -> list[SessionMetadata]:
        """List session metadata.

        Args:
            limit: Maximum number of sessions to return (None for all).
            offset: Number of sessions to skip.

        Returns:
            List of SessionMetadata, newest first.
        """
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data.

        Args:
            session_id: ID of the session to delete.

        Returns:
            True if session was deleted, False if not found.
        """
        pass