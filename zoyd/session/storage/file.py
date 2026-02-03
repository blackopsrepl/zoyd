"""File-based session storage for Zoyd.

Provides JSONL-based file storage for session data with a directory
structure that allows for efficient append-only writes and easy querying.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from zoyd.session.models import (
    ClaudeOutput,
    GitCommitRecord,
    Session,
    SessionEvent,
    SessionMetadata,
    SessionStatistics,
    TaskTransition,
)
from .helpers import append_jsonl, read_json, read_jsonl, write_json
from .interfaces import SessionStorage


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