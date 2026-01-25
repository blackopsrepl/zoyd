"""Session logger for Zoyd.

Provides SessionLogger class that subscribes to LoopRunner events and
persists session data to storage backends.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING

from zoyd.session.models import (
    ClaudeOutput,
    GitCommitRecord,
    SessionEvent,
    SessionMetadata,
    SessionStatistics,
    TaskTransition,
)
from zoyd.session.storage import FileStorage, InMemoryStorage, SessionStorage
from zoyd.tui.events import Event, EventEmitter, EventType

if TYPE_CHECKING:
    from zoyd.config import ZoydConfig


class SessionLogger:
    """Logger that persists session data from LoopRunner events.

    Subscribes to EventEmitter events and persists them to a SessionStorage
    backend. Tracks session metadata, statistics, events, Claude outputs,
    task transitions, and git commits.

    Example:
        logger = SessionLogger(storage=FileStorage(".zoyd/sessions"))
        logger.subscribe_to(runner.events)
        logger.start_session(config, working_dir="/path/to/repo")
        # ... run loop ...
        logger.end_session(exit_code=0, exit_reason="complete")
    """

    def __init__(
        self,
        storage: SessionStorage | None = None,
        sessions_dir: str = ".zoyd/sessions",
    ) -> None:
        """Initialize the session logger.

        Args:
            storage: Storage backend to use. If None, creates FileStorage.
            sessions_dir: Directory for file storage (if storage is None).
        """
        self.storage = storage or FileStorage(sessions_dir)
        self.session_id: str | None = None
        self._emitter: EventEmitter | None = None

        # Tracking state for statistics
        self._total_iterations = 0
        self._successful_iterations = 0
        self._failed_iterations = 0
        self._tasks_completed = 0
        self._tasks_total = 0
        self._total_cost = 0.0
        self._commits_made = 0
        self._start_time: float | None = None

        # Current iteration state
        self._current_iteration = 0
        self._iteration_start_time: float | None = None
        self._current_task_text = ""

    def start_session(
        self,
        config: "ZoydConfig | None" = None,
        working_dir: str = "",
        prd_path: str = "",
        progress_path: str = "",
        model: str | None = None,
        max_iterations: int = 10,
        max_cost: float | None = None,
        auto_commit: bool = True,
        fail_fast: bool = False,
    ) -> str:
        """Start a new logging session.

        Args:
            config: Optional ZoydConfig to pull settings from.
            working_dir: Working directory path.
            prd_path: Path to PRD file (used if config is None).
            progress_path: Path to progress file (used if config is None).
            model: Claude model name (used if config is None).
            max_iterations: Max iterations (used if config is None).
            max_cost: Max cost in USD (used if config is None).
            auto_commit: Auto-commit flag (used if config is None).
            fail_fast: Fail-fast flag (used if config is None).

        Returns:
            The session ID for the new session.
        """
        # Create metadata from config or explicit parameters
        if config is not None:
            metadata = SessionMetadata.from_config(config, working_dir)
        else:
            metadata = SessionMetadata(
                prd_path=prd_path,
                progress_path=progress_path,
                model=model,
                max_iterations=max_iterations,
                max_cost=max_cost,
                auto_commit=auto_commit,
                fail_fast=fail_fast,
                working_dir=working_dir,
            )

        # Create session in storage
        self.session_id = self.storage.create_session(metadata)
        self._start_time = time.time()

        # Reset statistics tracking
        self._total_iterations = 0
        self._successful_iterations = 0
        self._failed_iterations = 0
        self._tasks_completed = 0
        self._tasks_total = 0
        self._total_cost = 0.0
        self._commits_made = 0

        return self.session_id

    def end_session(
        self,
        exit_code: int = 0,
        exit_reason: str = "",
    ) -> None:
        """End the current session and finalize statistics.

        Args:
            exit_code: The exit code of the loop.
            exit_reason: Reason for exit (e.g., "complete", "max_iterations").
        """
        if self.session_id is None:
            return

        # Calculate total duration
        total_duration = 0.0
        if self._start_time is not None:
            total_duration = time.time() - self._start_time

        # Create final statistics
        statistics = SessionStatistics(
            total_iterations=self._total_iterations,
            successful_iterations=self._successful_iterations,
            failed_iterations=self._failed_iterations,
            tasks_completed=self._tasks_completed,
            tasks_total=self._tasks_total,
            total_cost_usd=self._total_cost,
            total_duration_seconds=total_duration,
            commits_made=self._commits_made,
            exit_code=exit_code,
            exit_reason=exit_reason,
        )

        # Update storage
        self.storage.update_statistics(self.session_id, statistics)
        self.storage.end_session(self.session_id)

        # Clean up subscriptions
        if self._emitter is not None:
            self._unsubscribe()

    def handle_event(self, event: Event) -> None:
        """Handle an event from the EventEmitter.

        Dispatches to specific handlers based on event type.

        Args:
            event: The event to handle.
        """
        if self.session_id is None:
            return

        # Map event types to handlers
        handlers = {
            EventType.LOOP_START: self._handle_loop_start,
            EventType.LOOP_END: self._handle_loop_end,
            EventType.ITERATION_START: self._handle_iteration_start,
            EventType.ITERATION_END: self._handle_iteration_end,
            EventType.CLAUDE_INVOKE: self._handle_claude_invoke,
            EventType.CLAUDE_RESPONSE: self._handle_claude_response,
            EventType.CLAUDE_ERROR: self._handle_claude_error,
            EventType.TASK_START: self._handle_task_start,
            EventType.TASK_COMPLETE: self._handle_task_complete,
            EventType.TASK_BLOCKED: self._handle_task_blocked,
            EventType.COST_UPDATE: self._handle_cost_update,
            EventType.COST_LIMIT_EXCEEDED: self._handle_cost_limit_exceeded,
            EventType.COMMIT_START: self._handle_commit_start,
            EventType.COMMIT_SUCCESS: self._handle_commit_success,
            EventType.COMMIT_FAILED: self._handle_commit_failed,
            EventType.LOG_MESSAGE: self._handle_log_message,
        }

        handler = handlers.get(event.type)
        if handler:
            handler(event)

        # Also store the raw event
        self._store_event(event)

    def subscribe_to(self, emitter: EventEmitter) -> "SessionLogger":
        """Subscribe to events from an EventEmitter.

        Args:
            emitter: The EventEmitter to subscribe to.

        Returns:
            Self for method chaining.
        """
        self._emitter = emitter
        emitter.on_any(self.handle_event)
        return self

    def _unsubscribe(self) -> None:
        """Unsubscribe from the current EventEmitter."""
        if self._emitter is not None:
            self._emitter.off_any(self.handle_event)
            self._emitter = None

    def _store_event(self, event: Event) -> None:
        """Store an event to the session.

        Args:
            event: The event to store.
        """
        if self.session_id is None:
            return

        session_event = SessionEvent(
            event_type=event.type.name,
            data=event.data,
            iteration=self._current_iteration if self._current_iteration > 0 else None,
        )
        self.storage.add_event(self.session_id, session_event)

    # =========================================================================
    # Loop Lifecycle Handlers
    # =========================================================================

    def _handle_loop_start(self, event: Event) -> None:
        """Handle LOOP_START event.

        Args:
            event: The event containing loop start data.
        """
        # Extract task totals if available
        self._tasks_total = event.get("total", 0)

    def _handle_loop_end(self, event: Event) -> None:
        """Handle LOOP_END event.

        Args:
            event: The event containing loop end data.
        """
        # End session will be called explicitly with exit info
        pass

    # =========================================================================
    # Iteration Handlers
    # =========================================================================

    def _handle_iteration_start(self, event: Event) -> None:
        """Handle ITERATION_START event.

        Args:
            event: The event containing iteration start data.
        """
        self._current_iteration = event.get("iteration", 0)
        self._iteration_start_time = time.time()
        self._total_iterations += 1

        # Update task totals
        total = event.get("total")
        if total is not None:
            self._tasks_total = total

    def _handle_iteration_end(self, event: Event) -> None:
        """Handle ITERATION_END event.

        Args:
            event: The event containing iteration end data.
        """
        success = event.get("success", True)
        if success:
            self._successful_iterations += 1
        else:
            self._failed_iterations += 1

    # =========================================================================
    # Claude Response/Error Handlers
    # =========================================================================

    def _handle_claude_invoke(self, event: Event) -> None:
        """Handle CLAUDE_INVOKE event.

        Args:
            event: The event containing invoke data.
        """
        self._current_task_text = event.get("task", "")

    def _handle_claude_response(self, event: Event) -> None:
        """Handle CLAUDE_RESPONSE event.

        Args:
            event: The event containing Claude response data.
        """
        if self.session_id is None:
            return

        # Calculate duration
        duration = None
        if self._iteration_start_time is not None:
            duration = time.time() - self._iteration_start_time

        # Create output record
        output = ClaudeOutput(
            iteration=self._current_iteration,
            output=event.get("output", ""),
            return_code=event.get("return_code", 0),
            cost_usd=event.get("cost_usd"),
            duration_seconds=duration,
            task_text=self._current_task_text,
        )
        self.storage.add_output(self.session_id, output)

    def _handle_claude_error(self, event: Event) -> None:
        """Handle CLAUDE_ERROR event.

        Args:
            event: The event containing error data.
        """
        if self.session_id is None:
            return

        # Calculate duration
        duration = None
        if self._iteration_start_time is not None:
            duration = time.time() - self._iteration_start_time

        # Create output record for the error
        output = ClaudeOutput(
            iteration=self._current_iteration,
            output=event.get("output", ""),
            return_code=event.get("return_code", 1),
            cost_usd=event.get("cost_usd"),
            duration_seconds=duration,
            task_text=self._current_task_text,
        )
        self.storage.add_output(self.session_id, output)

    # =========================================================================
    # Task Handlers
    # =========================================================================

    def _handle_task_start(self, event: Event) -> None:
        """Handle TASK_START event.

        Args:
            event: The event containing task start data.
        """
        self._current_task_text = event.get("task", "")

    def _handle_task_complete(self, event: Event) -> None:
        """Handle TASK_COMPLETE event.

        Args:
            event: The event containing task completion data.
        """
        if self.session_id is None:
            return

        self._tasks_completed += 1

        # Create transition record
        transition = TaskTransition(
            iteration=self._current_iteration,
            task_text=event.get("task", self._current_task_text),
            task_line=event.get("line", 0),
            from_state="incomplete",
            to_state="complete",
        )
        self.storage.add_transition(self.session_id, transition)

    def _handle_task_blocked(self, event: Event) -> None:
        """Handle TASK_BLOCKED event.

        Args:
            event: The event containing task blocked data.
        """
        if self.session_id is None:
            return

        # Create transition record for blocked task
        transition = TaskTransition(
            iteration=self._current_iteration,
            task_text=event.get("task", self._current_task_text),
            task_line=event.get("line", 0),
            from_state="incomplete",
            to_state="blocked",
        )
        self.storage.add_transition(self.session_id, transition)

    # =========================================================================
    # Cost Handlers
    # =========================================================================

    def _handle_cost_update(self, event: Event) -> None:
        """Handle COST_UPDATE event.

        Args:
            event: The event containing cost update data.
        """
        total_cost = event.get("total_cost")
        if total_cost is not None:
            self._total_cost = total_cost

    def _handle_cost_limit_exceeded(self, event: Event) -> None:
        """Handle COST_LIMIT_EXCEEDED event.

        Args:
            event: The event containing cost limit data.
        """
        total_cost = event.get("total_cost")
        if total_cost is not None:
            self._total_cost = total_cost

    # =========================================================================
    # Commit Handlers
    # =========================================================================

    def _handle_commit_start(self, event: Event) -> None:
        """Handle COMMIT_START event.

        Args:
            event: The event containing commit start data.
        """
        # Nothing to track at commit start
        pass

    def _handle_commit_success(self, event: Event) -> None:
        """Handle COMMIT_SUCCESS event.

        Args:
            event: The event containing commit success data.
        """
        if self.session_id is None:
            return

        self._commits_made += 1

        # Create commit record
        commit = GitCommitRecord(
            iteration=self._current_iteration,
            commit_hash=event.get("hash", ""),
            message=event.get("message", ""),
            files_changed=event.get("files_changed", 0),
            task_text=self._current_task_text,
        )
        self.storage.add_commit(self.session_id, commit)

    def _handle_commit_failed(self, event: Event) -> None:
        """Handle COMMIT_FAILED event.

        Args:
            event: The event containing commit failure data.
        """
        # Track as event only, no commit record
        pass

    # =========================================================================
    # Log Message Handler
    # =========================================================================

    def _handle_log_message(self, event: Event) -> None:
        """Handle LOG_MESSAGE event.

        Args:
            event: The event containing log message data.
        """
        # Log messages are stored as regular events via _store_event
        pass


def create_session_logger(
    storage: SessionStorage | None = None,
    sessions_dir: str = ".zoyd/sessions",
) -> SessionLogger:
    """Create a new session logger.

    Factory function for creating SessionLogger instances.

    Args:
        storage: Optional storage backend.
        sessions_dir: Directory for file storage (if storage is None).

    Returns:
        A new SessionLogger instance.
    """
    return SessionLogger(storage=storage, sessions_dir=sessions_dir)
