"""Tests for session logger event handling."""

import time
from unittest.mock import Mock, patch

import pytest

from zoyd.config import ZoydConfig
from zoyd.session.logger import SessionLogger, create_session_logger
from zoyd.session.models import (
    ClaudeOutput,
    GitCommitRecord,
    SessionEvent,
    SessionStatistics,
    TaskTransition,
)
from zoyd.session.storage import InMemoryStorage
from zoyd.tui.events import Event, EventEmitter, EventType


@pytest.fixture
def storage():
    """Create an in-memory storage for testing."""
    return InMemoryStorage()


@pytest.fixture
def logger(storage):
    """Create a session logger with in-memory storage."""
    return SessionLogger(storage=storage)


@pytest.fixture
def emitter():
    """Create an event emitter for testing."""
    return EventEmitter()


class TestSessionLoggerInit:
    """Tests for SessionLogger initialization."""

    def test_default_storage_is_file_storage(self, tmp_path):
        """Test that default storage is FileStorage."""
        from zoyd.session.storage import FileStorage

        with patch.object(FileStorage, "__init__", return_value=None):
            logger = SessionLogger()
            assert logger.storage is not None

    def test_custom_storage(self, storage):
        """Test that custom storage is used."""
        logger = SessionLogger(storage=storage)
        assert logger.storage is storage

    def test_initial_state(self, logger):
        """Test initial state is correct."""
        assert logger.session_id is None
        assert logger._emitter is None
        assert logger._total_iterations == 0
        assert logger._successful_iterations == 0
        assert logger._failed_iterations == 0


class TestStartSession:
    """Tests for SessionLogger.start_session."""

    def test_start_session_returns_id(self, logger):
        """Test start_session returns session ID."""
        session_id = logger.start_session(prd_path="PRD.md")
        assert session_id is not None
        assert logger.session_id == session_id

    def test_start_session_with_config(self, logger):
        """Test start_session with ZoydConfig."""
        config = ZoydConfig(
            prd="test.md",
            progress="prog.txt",
            model="opus",
            max_iterations=20,
        )
        session_id = logger.start_session(config=config, working_dir="/work")
        session = logger.storage.get_session(session_id)
        assert session.metadata.prd_path == "test.md"
        assert session.metadata.model == "opus"
        assert session.metadata.working_dir == "/work"

    def test_start_session_with_explicit_params(self, logger):
        """Test start_session with explicit parameters."""
        session_id = logger.start_session(
            prd_path="PRD.md",
            progress_path="prog.txt",
            model="sonnet",
            max_iterations=15,
            max_cost=5.0,
            auto_commit=False,
            fail_fast=True,
            working_dir="/test",
        )
        session = logger.storage.get_session(session_id)
        assert session.metadata.prd_path == "PRD.md"
        assert session.metadata.model == "sonnet"
        assert session.metadata.max_cost == 5.0
        assert session.metadata.auto_commit is False
        assert session.metadata.fail_fast is True

    def test_start_session_resets_tracking_state(self, logger):
        """Test start_session resets tracking state."""
        logger._total_iterations = 10
        logger._successful_iterations = 5
        logger._tasks_completed = 3
        logger._total_cost = 1.5
        logger.start_session(prd_path="PRD.md")
        assert logger._total_iterations == 0
        assert logger._successful_iterations == 0
        assert logger._tasks_completed == 0
        assert logger._total_cost == 0.0

    def test_start_session_sets_start_time(self, logger):
        """Test start_session sets start time."""
        logger.start_session(prd_path="PRD.md")
        assert logger._start_time is not None


class TestEndSession:
    """Tests for SessionLogger.end_session."""

    def test_end_session_updates_statistics(self, logger):
        """Test end_session updates statistics."""
        session_id = logger.start_session(prd_path="PRD.md")
        logger._total_iterations = 5
        logger._successful_iterations = 4
        logger._failed_iterations = 1
        logger._tasks_completed = 3
        logger._total_cost = 1.25
        logger._commits_made = 3
        logger.end_session(exit_code=0, exit_reason="complete")
        session = logger.storage.get_session(session_id)
        assert session.statistics.total_iterations == 5
        assert session.statistics.successful_iterations == 4
        assert session.statistics.failed_iterations == 1
        assert session.statistics.tasks_completed == 3
        assert session.statistics.total_cost_usd == 1.25
        assert session.statistics.commits_made == 3
        assert session.statistics.exit_code == 0
        assert session.statistics.exit_reason == "complete"

    def test_end_session_sets_ended_at(self, logger):
        """Test end_session sets ended_at timestamp."""
        session_id = logger.start_session(prd_path="PRD.md")
        logger.end_session(exit_code=0, exit_reason="complete")
        session = logger.storage.get_session(session_id)
        assert session.metadata.ended_at is not None

    def test_end_session_calculates_duration(self, logger):
        """Test end_session calculates total duration."""
        session_id = logger.start_session(prd_path="PRD.md")
        time.sleep(0.1)  # Small delay
        logger.end_session(exit_code=0, exit_reason="complete")
        session = logger.storage.get_session(session_id)
        assert session.statistics.total_duration_seconds >= 0.1

    def test_end_session_unsubscribes_from_emitter(self, logger, emitter):
        """Test end_session unsubscribes from emitter."""
        logger.subscribe_to(emitter)
        logger.start_session(prd_path="PRD.md")
        assert logger._emitter is emitter
        logger.end_session(exit_code=0, exit_reason="complete")
        assert logger._emitter is None

    def test_end_session_without_session_does_nothing(self, logger):
        """Test end_session without active session does nothing."""
        logger.end_session(exit_code=0, exit_reason="test")  # Should not raise


class TestSubscribeTo:
    """Tests for SessionLogger.subscribe_to."""

    def test_subscribe_to_stores_emitter(self, logger, emitter):
        """Test subscribe_to stores the emitter."""
        logger.subscribe_to(emitter)
        assert logger._emitter is emitter

    def test_subscribe_to_returns_self(self, logger, emitter):
        """Test subscribe_to returns self for chaining."""
        result = logger.subscribe_to(emitter)
        assert result is logger

    def test_subscribe_to_registers_handler(self, logger, emitter):
        """Test subscribe_to registers the event handler."""
        logger.subscribe_to(emitter)
        logger.start_session(prd_path="PRD.md")
        # Emit an event
        emitter.emit(EventType.ITERATION_START, {"iteration": 1})
        # Should have been handled
        assert logger._current_iteration == 1


class TestHandleEvent:
    """Tests for SessionLogger.handle_event."""

    def test_handle_event_dispatches_to_handler(self, logger):
        """Test handle_event dispatches to correct handler."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.ITERATION_START, {"iteration": 5})
        logger.handle_event(event)
        assert logger._current_iteration == 5

    def test_handle_event_stores_raw_event(self, logger):
        """Test handle_event stores the raw event."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.LOG_MESSAGE, {"message": "test"})
        logger.handle_event(event)
        session = logger.storage.get_session(logger.session_id)
        assert len(session.events) == 1
        assert session.events[0].event_type == "LOG_MESSAGE"

    def test_handle_event_without_session_does_nothing(self, logger):
        """Test handle_event without session does nothing."""
        event = Event(EventType.ITERATION_START, {"iteration": 1})
        logger.handle_event(event)  # Should not raise

    def test_handle_event_unknown_type_just_stores(self, logger):
        """Test handle_event with unknown type just stores event."""
        logger.start_session(prd_path="PRD.md")
        # Use a valid event type but one with no special handling
        event = Event(EventType.LOG_MESSAGE, {"message": "test"})
        logger.handle_event(event)
        session = logger.storage.get_session(logger.session_id)
        assert len(session.events) == 1


class TestIterationHandlers:
    """Tests for iteration event handlers."""

    def test_iteration_start_sets_current_iteration(self, logger):
        """Test ITERATION_START sets current iteration."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.ITERATION_START, {"iteration": 3, "total": 10})
        logger.handle_event(event)
        assert logger._current_iteration == 3
        assert logger._total_iterations == 1

    def test_iteration_start_updates_task_totals(self, logger):
        """Test ITERATION_START updates task totals."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.ITERATION_START, {"iteration": 1, "total": 15})
        logger.handle_event(event)
        assert logger._tasks_total == 15

    def test_iteration_end_success_increments_successful(self, logger):
        """Test ITERATION_END with success increments successful count."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.ITERATION_END, {"success": True})
        logger.handle_event(event)
        assert logger._successful_iterations == 1
        assert logger._failed_iterations == 0

    def test_iteration_end_failure_increments_failed(self, logger):
        """Test ITERATION_END with failure increments failed count."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.ITERATION_END, {"success": False})
        logger.handle_event(event)
        assert logger._failed_iterations == 1
        assert logger._successful_iterations == 0


class TestClaudeHandlers:
    """Tests for Claude response/error handlers."""

    def test_claude_invoke_sets_task_text(self, logger):
        """Test CLAUDE_INVOKE sets current task text."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.CLAUDE_INVOKE, {"task": "Implement feature"})
        logger.handle_event(event)
        assert logger._current_task_text == "Implement feature"

    def test_claude_response_stores_output(self, logger):
        """Test CLAUDE_RESPONSE stores output record."""
        logger.start_session(prd_path="PRD.md")
        logger._current_iteration = 2
        logger._current_task_text = "Test task"
        logger._iteration_start_time = time.time() - 10  # 10 seconds ago
        event = Event(
            EventType.CLAUDE_RESPONSE,
            {"output": "Hello", "return_code": 0, "cost_usd": 0.05},
        )
        logger.handle_event(event)
        session = logger.storage.get_session(logger.session_id)
        assert len(session.outputs) == 1
        output = session.outputs[0]
        assert output.output == "Hello"
        assert output.return_code == 0
        assert output.cost_usd == 0.05
        assert output.iteration == 2
        assert output.task_text == "Test task"
        assert output.duration_seconds >= 10

    def test_claude_error_stores_output(self, logger):
        """Test CLAUDE_ERROR stores output record."""
        logger.start_session(prd_path="PRD.md")
        logger._current_iteration = 3
        event = Event(
            EventType.CLAUDE_ERROR,
            {"output": "Error occurred", "return_code": 1},
        )
        logger.handle_event(event)
        session = logger.storage.get_session(logger.session_id)
        assert len(session.outputs) == 1
        output = session.outputs[0]
        assert output.output == "Error occurred"
        assert output.return_code == 1


class TestTaskHandlers:
    """Tests for task event handlers."""

    def test_task_start_sets_task_text(self, logger):
        """Test TASK_START sets current task text."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.TASK_START, {"task": "New task"})
        logger.handle_event(event)
        assert logger._current_task_text == "New task"

    def test_task_complete_increments_count(self, logger):
        """Test TASK_COMPLETE increments tasks completed."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.TASK_COMPLETE, {"task": "Done task", "line": 10})
        logger.handle_event(event)
        assert logger._tasks_completed == 1

    def test_task_complete_stores_transition(self, logger):
        """Test TASK_COMPLETE stores transition record."""
        logger.start_session(prd_path="PRD.md")
        logger._current_iteration = 5
        event = Event(EventType.TASK_COMPLETE, {"task": "Completed task", "line": 42})
        logger.handle_event(event)
        session = logger.storage.get_session(logger.session_id)
        assert len(session.transitions) == 1
        trans = session.transitions[0]
        assert trans.task_text == "Completed task"
        assert trans.task_line == 42
        assert trans.from_state == "incomplete"
        assert trans.to_state == "complete"
        assert trans.iteration == 5

    def test_task_blocked_stores_transition(self, logger):
        """Test TASK_BLOCKED stores transition record."""
        logger.start_session(prd_path="PRD.md")
        logger._current_iteration = 2
        event = Event(EventType.TASK_BLOCKED, {"task": "Blocked task", "line": 15})
        logger.handle_event(event)
        session = logger.storage.get_session(logger.session_id)
        assert len(session.transitions) == 1
        trans = session.transitions[0]
        assert trans.to_state == "blocked"


class TestCostHandlers:
    """Tests for cost event handlers."""

    def test_cost_update_sets_total_cost(self, logger):
        """Test COST_UPDATE sets total cost."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.COST_UPDATE, {"total_cost": 1.50})
        logger.handle_event(event)
        assert logger._total_cost == 1.50

    def test_cost_limit_exceeded_sets_total_cost(self, logger):
        """Test COST_LIMIT_EXCEEDED sets total cost."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.COST_LIMIT_EXCEEDED, {"total_cost": 5.00})
        logger.handle_event(event)
        assert logger._total_cost == 5.00


class TestCommitHandlers:
    """Tests for commit event handlers."""

    def test_commit_success_increments_count(self, logger):
        """Test COMMIT_SUCCESS increments commits made."""
        logger.start_session(prd_path="PRD.md")
        event = Event(
            EventType.COMMIT_SUCCESS,
            {"hash": "abc123", "message": "feat: add feature"},
        )
        logger.handle_event(event)
        assert logger._commits_made == 1

    def test_commit_success_stores_record(self, logger):
        """Test COMMIT_SUCCESS stores commit record."""
        logger.start_session(prd_path="PRD.md")
        logger._current_iteration = 7
        logger._current_task_text = "Implement feature"
        event = Event(
            EventType.COMMIT_SUCCESS,
            {"hash": "abc123def456", "message": "feat: add feature", "files_changed": 3},
        )
        logger.handle_event(event)
        session = logger.storage.get_session(logger.session_id)
        assert len(session.commits) == 1
        commit = session.commits[0]
        assert commit.commit_hash == "abc123def456"
        assert commit.message == "feat: add feature"
        assert commit.files_changed == 3
        assert commit.iteration == 7
        assert commit.task_text == "Implement feature"

    def test_commit_failed_does_not_store_record(self, logger):
        """Test COMMIT_FAILED does not store commit record."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.COMMIT_FAILED, {"error": "pre-commit hook failed"})
        logger.handle_event(event)
        session = logger.storage.get_session(logger.session_id)
        assert len(session.commits) == 0
        # But event is still stored
        assert len(session.events) > 0


class TestLoopHandlers:
    """Tests for loop lifecycle handlers."""

    def test_loop_start_sets_task_totals(self, logger):
        """Test LOOP_START sets task totals."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.LOOP_START, {"total": 20})
        logger.handle_event(event)
        assert logger._tasks_total == 20

    def test_loop_end_is_no_op(self, logger):
        """Test LOOP_END is handled without error."""
        logger.start_session(prd_path="PRD.md")
        event = Event(EventType.LOOP_END, {"status": "complete"})
        logger.handle_event(event)  # Should not raise


class TestIntegrationWithEmitter:
    """Integration tests with EventEmitter."""

    def test_full_session_workflow(self, storage):
        """Test full session workflow with events."""
        logger = SessionLogger(storage=storage)
        emitter = EventEmitter()
        logger.subscribe_to(emitter)

        # Start session
        session_id = logger.start_session(prd_path="PRD.md")

        # Emit loop start
        emitter.emit(EventType.LOOP_START, {"total": 5})

        # Emit iteration events
        emitter.emit(EventType.ITERATION_START, {"iteration": 1, "total": 5})
        emitter.emit(EventType.CLAUDE_INVOKE, {"task": "Task 1"})
        emitter.emit(EventType.CLAUDE_RESPONSE, {"output": "Done", "return_code": 0})
        emitter.emit(EventType.TASK_COMPLETE, {"task": "Task 1", "line": 10})
        emitter.emit(EventType.COMMIT_SUCCESS, {"hash": "abc", "message": "feat"})
        emitter.emit(EventType.ITERATION_END, {"success": True})

        # End session
        logger.end_session(exit_code=0, exit_reason="complete")

        # Verify session data
        session = storage.get_session(session_id)
        assert session.statistics.total_iterations == 1
        assert session.statistics.successful_iterations == 1
        assert session.statistics.tasks_completed == 1
        assert session.statistics.commits_made == 1
        assert session.statistics.exit_code == 0
        assert session.statistics.exit_reason == "complete"

        # Verify event records
        assert len(session.events) > 0
        assert len(session.outputs) == 1
        assert len(session.transitions) == 1
        assert len(session.commits) == 1


class TestCreateSessionLogger:
    """Tests for create_session_logger factory function."""

    def test_create_session_logger_default(self, tmp_path):
        """Test create_session_logger with defaults."""
        from zoyd.session.storage import FileStorage

        with patch.object(FileStorage, "__init__", return_value=None):
            logger = create_session_logger()
            assert logger is not None

    def test_create_session_logger_with_storage(self, storage):
        """Test create_session_logger with custom storage."""
        logger = create_session_logger(storage=storage)
        assert logger.storage is storage

    def test_create_session_logger_with_sessions_dir(self, tmp_path):
        """Test create_session_logger with sessions_dir."""
        from zoyd.session.storage import FileStorage

        logger = create_session_logger(sessions_dir=str(tmp_path / "sessions"))
        assert isinstance(logger.storage, FileStorage)


class TestModuleExports:
    """Tests for module exports."""

    def test_session_logger_exported(self):
        """Test SessionLogger is exported."""
        from zoyd.session import SessionLogger

        assert SessionLogger is not None

    def test_create_session_logger_exported(self):
        """Test create_session_logger is exported."""
        from zoyd.session import create_session_logger

        assert create_session_logger is not None
