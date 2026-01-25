"""Session storage backends for Zoyd.

Provides storage interfaces and implementations for persisting session data:
- SessionStorage: Abstract base class defining the storage interface
- InMemoryStorage: In-memory storage for testing
- FileStorage: JSONL-based file storage for production
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from zoyd.session.models import (
    ClaudeOutput,
    GitCommitRecord,
    Session,
    SessionEvent,
    SessionMetadata,
    SessionStatistics,
    TaskTransition,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Serialization Helpers
# =============================================================================


def to_json(obj: Any, indent: int | None = None) -> str:
    """Convert an object to JSON string.

    Args:
        obj: Object to serialize. If it has a to_dict() method, that's used.
        indent: Indentation level for pretty printing (None for compact).

    Returns:
        JSON string representation.
    """
    if hasattr(obj, "to_dict"):
        data = obj.to_dict()
    else:
        data = obj
    return json.dumps(data, indent=indent, default=str)


def from_json(json_str: str, cls: type | None = None) -> Any:
    """Parse JSON string into an object.

    Args:
        json_str: JSON string to parse.
        cls: Optional class with from_dict() method to create instance.

    Returns:
        Parsed object (dict if cls is None, instance of cls otherwise).
    """
    data = json.loads(json_str)
    if cls is not None and hasattr(cls, "from_dict"):
        return cls.from_dict(data)
    return data


def append_jsonl(path: Path, obj: Any) -> None:
    """Append an object as a single JSON line to a file.

    Args:
        path: Path to the JSONL file.
        obj: Object to append (must have to_dict() or be serializable).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(to_json(obj) + "\n")


def read_jsonl(path: Path, cls: type | None = None) -> list[Any]:
    """Read all objects from a JSONL file.

    Args:
        path: Path to the JSONL file.
        cls: Optional class with from_dict() method to create instances.

    Returns:
        List of parsed objects.
    """
    if not path.exists():
        return []
    results = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(from_json(line, cls))
    return results


def write_json(path: Path, obj: Any, indent: int = 2) -> None:
    """Write an object as formatted JSON to a file.

    Args:
        path: Path to the JSON file.
        obj: Object to write (must have to_dict() or be serializable).
        indent: Indentation level for pretty printing.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(to_json(obj, indent=indent))


def read_json(path: Path, cls: type | None = None) -> Any:
    """Read a JSON file into an object.

    Args:
        path: Path to the JSON file.
        cls: Optional class with from_dict() method to create instance.

    Returns:
        Parsed object (dict if cls is None, instance of cls otherwise).
        None if file doesn't exist.
    """
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return from_json(f.read(), cls)


# =============================================================================
# Abstract Storage Interface
# =============================================================================


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


# =============================================================================
# In-Memory Storage (for testing)
# =============================================================================


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


# =============================================================================
# File Storage (JSONL-based)
# =============================================================================


class FileStorage(SessionStorage):
    """File-based session storage using JSONL format.

    Session data is stored in directories under the base path:
    - .zoyd/sessions/{session_id}/
      - session.json: Metadata and statistics
      - events.jsonl: Event records (one per line)
      - outputs.jsonl: Claude output records (one per line)
      - transitions.jsonl: Task transition records (one per line)
      - commits.jsonl: Git commit records (one per line)

    This format allows for:
    - Append-only logging during session
    - Efficient incremental writes
    - Human-readable files
    - Easy querying with standard tools (grep, jq)
    """

    def __init__(self, base_path: str | Path = ".zoyd/sessions") -> None:
        """Initialize file storage.

        Args:
            base_path: Base directory for session storage.
        """
        self.base_path = Path(base_path)

    def _session_dir(self, session_id: str) -> Path:
        """Get the directory path for a session.

        Args:
            session_id: Session ID.

        Returns:
            Path to the session directory.
        """
        return self.base_path / session_id

    def _session_file(self, session_id: str) -> Path:
        """Get the session.json file path.

        Args:
            session_id: Session ID.

        Returns:
            Path to session.json.
        """
        return self._session_dir(session_id) / "session.json"

    def _events_file(self, session_id: str) -> Path:
        """Get the events.jsonl file path.

        Args:
            session_id: Session ID.

        Returns:
            Path to events.jsonl.
        """
        return self._session_dir(session_id) / "events.jsonl"

    def _outputs_file(self, session_id: str) -> Path:
        """Get the outputs.jsonl file path.

        Args:
            session_id: Session ID.

        Returns:
            Path to outputs.jsonl.
        """
        return self._session_dir(session_id) / "outputs.jsonl"

    def _transitions_file(self, session_id: str) -> Path:
        """Get the transitions.jsonl file path.

        Args:
            session_id: Session ID.

        Returns:
            Path to transitions.jsonl.
        """
        return self._session_dir(session_id) / "transitions.jsonl"

    def _commits_file(self, session_id: str) -> Path:
        """Get the commits.jsonl file path.

        Args:
            session_id: Session ID.

        Returns:
            Path to commits.jsonl.
        """
        return self._session_dir(session_id) / "commits.jsonl"

    def _write_session_file(
        self, session_id: str, metadata: SessionMetadata,
        statistics: SessionStatistics | None = None
    ) -> None:
        """Write the session.json file.

        Args:
            session_id: Session ID.
            metadata: Session metadata.
            statistics: Optional statistics to include.
        """
        data = {
            "metadata": metadata.to_dict(),
            "statistics": (statistics or SessionStatistics()).to_dict(),
        }
        write_json(self._session_file(session_id), data)

    def _read_session_file(
        self, session_id: str
    ) -> tuple[SessionMetadata | None, SessionStatistics | None]:
        """Read the session.json file.

        Args:
            session_id: Session ID.

        Returns:
            Tuple of (metadata, statistics) or (None, None) if not found.
        """
        data = read_json(self._session_file(session_id))
        if data is None:
            return None, None
        metadata = SessionMetadata.from_dict(data.get("metadata", {}))
        statistics = SessionStatistics.from_dict(data.get("statistics", {}))
        return metadata, statistics

    def create_session(self, metadata: SessionMetadata) -> str:
        """Create a new session on disk.

        Args:
            metadata: Session metadata.

        Returns:
            Session ID of the created session.
        """
        session_dir = self._session_dir(metadata.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        self._write_session_file(metadata.session_id, metadata)
        return metadata.session_id

    def end_session(
        self, session_id: str, ended_at: str | None = None
    ) -> None:
        """Mark a session as ended.

        Args:
            session_id: ID of the session to end.
            ended_at: ISO timestamp when session ended (default: now).
        """
        metadata, statistics = self._read_session_file(session_id)
        if metadata is None:
            return
        if ended_at is None:
            ended_at = datetime.now().isoformat()
        metadata.ended_at = ended_at
        self._write_session_file(session_id, metadata, statistics)

    def get_session(self, session_id: str) -> Session | None:
        """Get a full session by ID.

        Args:
            session_id: ID of the session to retrieve.

        Returns:
            Session object or None if not found.
        """
        metadata, statistics = self._read_session_file(session_id)
        if metadata is None:
            return None
        return Session(
            metadata=metadata,
            statistics=statistics or SessionStatistics(),
            events=read_jsonl(self._events_file(session_id), SessionEvent),
            outputs=read_jsonl(self._outputs_file(session_id), ClaudeOutput),
            transitions=read_jsonl(
                self._transitions_file(session_id), TaskTransition
            ),
            commits=read_jsonl(self._commits_file(session_id), GitCommitRecord),
        )

    def get_metadata(self, session_id: str) -> SessionMetadata | None:
        """Get session metadata by ID.

        Args:
            session_id: ID of the session.

        Returns:
            SessionMetadata or None if not found.
        """
        metadata, _ = self._read_session_file(session_id)
        return metadata

    def update_statistics(
        self, session_id: str, statistics: SessionStatistics
    ) -> None:
        """Update session statistics.

        Args:
            session_id: ID of the session.
            statistics: New statistics to store.
        """
        metadata, _ = self._read_session_file(session_id)
        if metadata is None:
            return
        self._write_session_file(session_id, metadata, statistics)

    def add_event(self, session_id: str, event: SessionEvent) -> None:
        """Add an event to a session.

        Args:
            session_id: ID of the session.
            event: Event to add.
        """
        if self._session_dir(session_id).exists():
            append_jsonl(self._events_file(session_id), event)

    def add_output(self, session_id: str, output: ClaudeOutput) -> None:
        """Add a Claude output to a session.

        Args:
            session_id: ID of the session.
            output: Output to add.
        """
        if self._session_dir(session_id).exists():
            append_jsonl(self._outputs_file(session_id), output)

    def add_transition(
        self, session_id: str, transition: TaskTransition
    ) -> None:
        """Add a task transition to a session.

        Args:
            session_id: ID of the session.
            transition: Transition to add.
        """
        if self._session_dir(session_id).exists():
            append_jsonl(self._transitions_file(session_id), transition)

    def add_commit(self, session_id: str, commit: GitCommitRecord) -> None:
        """Add a git commit record to a session.

        Args:
            session_id: ID of the session.
            commit: Commit record to add.
        """
        if self._session_dir(session_id).exists():
            append_jsonl(self._commits_file(session_id), commit)

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
        if not self.base_path.exists():
            return []

        all_metadata = []
        for session_dir in self.base_path.iterdir():
            if session_dir.is_dir():
                metadata, _ = self._read_session_file(session_dir.name)
                if metadata:
                    all_metadata.append(metadata)

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
        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            return False

        # Delete all files in the session directory
        for file in session_dir.iterdir():
            file.unlink()
        # Delete the directory itself
        session_dir.rmdir()
        return True
