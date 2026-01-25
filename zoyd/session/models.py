"""Session data models for Zoyd.

Provides dataclasses for persisting session information:
- SessionMetadata: Core session info (UUID, timestamps, config)
- SessionEvent: Individual event records from the EventEmitter
- ClaudeOutput: Full Claude response storage
- TaskTransition: Task state change records
- GitCommitRecord: Git commit metadata
- SessionStatistics: Aggregated statistics
- Session: Complete session combining metadata and statistics
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from zoyd.config import ZoydConfig


def _generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def _now_isoformat() -> str:
    """Generate current timestamp in ISO format."""
    return datetime.now().isoformat()


@dataclass
class SessionMetadata:
    """Metadata about a Zoyd session.

    Attributes:
        session_id: Unique identifier for the session.
        started_at: ISO format timestamp when session started.
        ended_at: ISO format timestamp when session ended (None if ongoing).
        prd_path: Path to the PRD file.
        progress_path: Path to the progress file.
        model: Claude model used (e.g., "opus", "sonnet").
        max_iterations: Maximum iterations configured.
        max_cost: Maximum cost limit in USD (None if unlimited).
        auto_commit: Whether auto-commit was enabled.
        fail_fast: Whether fail-fast mode was enabled.
        working_dir: Working directory for the session.
    """

    session_id: str = field(default_factory=_generate_uuid)
    started_at: str = field(default_factory=_now_isoformat)
    ended_at: str | None = None
    prd_path: str = ""
    progress_path: str = ""
    model: str | None = None
    max_iterations: int = 10
    max_cost: float | None = None
    auto_commit: bool = True
    fail_fast: bool = False
    working_dir: str = ""

    @classmethod
    def from_config(
        cls, config: "ZoydConfig", working_dir: str = ""
    ) -> "SessionMetadata":
        """Create metadata from a ZoydConfig.

        Args:
            config: The Zoyd configuration.
            working_dir: Working directory path.

        Returns:
            SessionMetadata populated from config.
        """
        return cls(
            prd_path=config.prd,
            progress_path=config.progress,
            model=config.model,
            max_iterations=config.max_iterations,
            max_cost=config.max_cost,
            auto_commit=config.auto_commit,
            fail_fast=config.fail_fast,
            working_dir=working_dir,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the metadata.
        """
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "prd_path": self.prd_path,
            "progress_path": self.progress_path,
            "model": self.model,
            "max_iterations": self.max_iterations,
            "max_cost": self.max_cost,
            "auto_commit": self.auto_commit,
            "fail_fast": self.fail_fast,
            "working_dir": self.working_dir,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMetadata":
        """Create from a dictionary.

        Args:
            data: Dictionary with metadata fields.

        Returns:
            SessionMetadata instance.
        """
        return cls(
            session_id=data.get("session_id", _generate_uuid()),
            started_at=data.get("started_at", _now_isoformat()),
            ended_at=data.get("ended_at"),
            prd_path=data.get("prd_path", ""),
            progress_path=data.get("progress_path", ""),
            model=data.get("model"),
            max_iterations=data.get("max_iterations", 10),
            max_cost=data.get("max_cost"),
            auto_commit=data.get("auto_commit", True),
            fail_fast=data.get("fail_fast", False),
            working_dir=data.get("working_dir", ""),
        )


@dataclass
class SessionEvent:
    """An event record from the session.

    Attributes:
        timestamp: ISO format timestamp when event occurred.
        event_type: Name of the event type (e.g., "ITERATION_START").
        data: Event payload data.
        iteration: Iteration number when event occurred (if applicable).
    """

    timestamp: str = field(default_factory=_now_isoformat)
    event_type: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    iteration: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the event.
        """
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "data": self.data,
            "iteration": self.iteration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionEvent":
        """Create from a dictionary.

        Args:
            data: Dictionary with event fields.

        Returns:
            SessionEvent instance.
        """
        return cls(
            timestamp=data.get("timestamp", _now_isoformat()),
            event_type=data.get("event_type", ""),
            data=data.get("data", {}),
            iteration=data.get("iteration"),
        )


@dataclass
class ClaudeOutput:
    """Full Claude response storage.

    Attributes:
        timestamp: ISO format timestamp when response received.
        iteration: Iteration number.
        output: Full text output from Claude.
        return_code: Return code from Claude invocation.
        cost_usd: Cost of this invocation in USD.
        duration_seconds: How long the invocation took.
        task_text: The task being worked on.
    """

    timestamp: str = field(default_factory=_now_isoformat)
    iteration: int = 0
    output: str = ""
    return_code: int = 0
    cost_usd: float | None = None
    duration_seconds: float | None = None
    task_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the output.
        """
        return {
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "output": self.output,
            "return_code": self.return_code,
            "cost_usd": self.cost_usd,
            "duration_seconds": self.duration_seconds,
            "task_text": self.task_text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClaudeOutput":
        """Create from a dictionary.

        Args:
            data: Dictionary with output fields.

        Returns:
            ClaudeOutput instance.
        """
        return cls(
            timestamp=data.get("timestamp", _now_isoformat()),
            iteration=data.get("iteration", 0),
            output=data.get("output", ""),
            return_code=data.get("return_code", 0),
            cost_usd=data.get("cost_usd"),
            duration_seconds=data.get("duration_seconds"),
            task_text=data.get("task_text", ""),
        )


@dataclass
class TaskTransition:
    """Record of a task state change.

    Attributes:
        timestamp: ISO format timestamp when transition occurred.
        iteration: Iteration number when transition occurred.
        task_text: Text of the task.
        task_line: Line number of the task in the PRD.
        from_state: Previous state ("incomplete" or "complete").
        to_state: New state ("incomplete" or "complete").
    """

    timestamp: str = field(default_factory=_now_isoformat)
    iteration: int = 0
    task_text: str = ""
    task_line: int = 0
    from_state: str = "incomplete"
    to_state: str = "complete"

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the transition.
        """
        return {
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "task_text": self.task_text,
            "task_line": self.task_line,
            "from_state": self.from_state,
            "to_state": self.to_state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskTransition":
        """Create from a dictionary.

        Args:
            data: Dictionary with transition fields.

        Returns:
            TaskTransition instance.
        """
        return cls(
            timestamp=data.get("timestamp", _now_isoformat()),
            iteration=data.get("iteration", 0),
            task_text=data.get("task_text", ""),
            task_line=data.get("task_line", 0),
            from_state=data.get("from_state", "incomplete"),
            to_state=data.get("to_state", "complete"),
        )


@dataclass
class GitCommitRecord:
    """Record of a git commit made during the session.

    Attributes:
        timestamp: ISO format timestamp when commit was made.
        iteration: Iteration number when commit was made.
        commit_hash: Full SHA hash of the commit.
        message: Commit message.
        files_changed: Number of files changed.
        task_text: Task text that was committed for.
    """

    timestamp: str = field(default_factory=_now_isoformat)
    iteration: int = 0
    commit_hash: str = ""
    message: str = ""
    files_changed: int = 0
    task_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the commit record.
        """
        return {
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "commit_hash": self.commit_hash,
            "message": self.message,
            "files_changed": self.files_changed,
            "task_text": self.task_text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GitCommitRecord":
        """Create from a dictionary.

        Args:
            data: Dictionary with commit record fields.

        Returns:
            GitCommitRecord instance.
        """
        return cls(
            timestamp=data.get("timestamp", _now_isoformat()),
            iteration=data.get("iteration", 0),
            commit_hash=data.get("commit_hash", ""),
            message=data.get("message", ""),
            files_changed=data.get("files_changed", 0),
            task_text=data.get("task_text", ""),
        )


@dataclass
class SessionStatistics:
    """Aggregated statistics for a session.

    Attributes:
        total_iterations: Total number of iterations run.
        successful_iterations: Number of successful iterations.
        failed_iterations: Number of failed iterations.
        tasks_completed: Number of tasks completed this session.
        tasks_total: Total number of tasks in PRD.
        total_cost_usd: Total cost in USD.
        total_duration_seconds: Total duration in seconds.
        commits_made: Number of git commits made.
        exit_code: Final exit code.
        exit_reason: Reason for exit (e.g., "complete", "max_iterations").
    """

    total_iterations: int = 0
    successful_iterations: int = 0
    failed_iterations: int = 0
    tasks_completed: int = 0
    tasks_total: int = 0
    total_cost_usd: float = 0.0
    total_duration_seconds: float = 0.0
    commits_made: int = 0
    exit_code: int = 0
    exit_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the statistics.
        """
        return {
            "total_iterations": self.total_iterations,
            "successful_iterations": self.successful_iterations,
            "failed_iterations": self.failed_iterations,
            "tasks_completed": self.tasks_completed,
            "tasks_total": self.tasks_total,
            "total_cost_usd": self.total_cost_usd,
            "total_duration_seconds": self.total_duration_seconds,
            "commits_made": self.commits_made,
            "exit_code": self.exit_code,
            "exit_reason": self.exit_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionStatistics":
        """Create from a dictionary.

        Args:
            data: Dictionary with statistics fields.

        Returns:
            SessionStatistics instance.
        """
        return cls(
            total_iterations=data.get("total_iterations", 0),
            successful_iterations=data.get("successful_iterations", 0),
            failed_iterations=data.get("failed_iterations", 0),
            tasks_completed=data.get("tasks_completed", 0),
            tasks_total=data.get("tasks_total", 0),
            total_cost_usd=data.get("total_cost_usd", 0.0),
            total_duration_seconds=data.get("total_duration_seconds", 0.0),
            commits_made=data.get("commits_made", 0),
            exit_code=data.get("exit_code", 0),
            exit_reason=data.get("exit_reason", ""),
        )


@dataclass
class Session:
    """Complete session data combining metadata and statistics.

    Attributes:
        metadata: Session metadata (UUID, timestamps, config).
        statistics: Aggregated session statistics.
        events: List of session events (optional, for full session load).
        outputs: List of Claude outputs (optional, for full session load).
        transitions: List of task transitions (optional, for full session load).
        commits: List of git commit records (optional, for full session load).
    """

    metadata: SessionMetadata = field(default_factory=SessionMetadata)
    statistics: SessionStatistics = field(default_factory=SessionStatistics)
    events: list[SessionEvent] = field(default_factory=list)
    outputs: list[ClaudeOutput] = field(default_factory=list)
    transitions: list[TaskTransition] = field(default_factory=list)
    commits: list[GitCommitRecord] = field(default_factory=list)

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self.metadata.session_id

    @property
    def is_complete(self) -> bool:
        """Check if the session has ended."""
        return self.metadata.ended_at is not None

    def to_dict(self, include_details: bool = False) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization.

        Args:
            include_details: If True, include events, outputs, etc.

        Returns:
            Dictionary representation of the session.
        """
        result: dict[str, Any] = {
            "metadata": self.metadata.to_dict(),
            "statistics": self.statistics.to_dict(),
        }
        if include_details:
            result["events"] = [e.to_dict() for e in self.events]
            result["outputs"] = [o.to_dict() for o in self.outputs]
            result["transitions"] = [t.to_dict() for t in self.transitions]
            result["commits"] = [c.to_dict() for c in self.commits]
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """Create from a dictionary.

        Args:
            data: Dictionary with session fields.

        Returns:
            Session instance.
        """
        return cls(
            metadata=SessionMetadata.from_dict(data.get("metadata", {})),
            statistics=SessionStatistics.from_dict(data.get("statistics", {})),
            events=[SessionEvent.from_dict(e) for e in data.get("events", [])],
            outputs=[ClaudeOutput.from_dict(o) for o in data.get("outputs", [])],
            transitions=[
                TaskTransition.from_dict(t) for t in data.get("transitions", [])
            ],
            commits=[GitCommitRecord.from_dict(c) for c in data.get("commits", [])],
        )
