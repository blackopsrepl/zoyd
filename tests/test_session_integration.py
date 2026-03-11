"""Integration tests for full loop with session logging."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zoyd.config import ZoydConfig
from zoyd.loop import LoopRunner
from zoyd.session.storage import FileStorage, InMemoryStorage


@pytest.fixture
def prd_file(tmp_path):
    """Create a test PRD file."""
    prd = tmp_path / "PRD.md"
    prd.write_text(
        """# Test PRD

## Tasks

- [ ] Task one
- [ ] Task two
- [ ] Task three
"""
    )
    return prd


@pytest.fixture
def progress_file(tmp_path):
    """Create a test progress file path."""
    return tmp_path / "progress.txt"


@pytest.fixture
def sessions_dir(tmp_path):
    """Create a sessions directory path."""
    return str(tmp_path / "sessions")


class TestLoopRunnerSessionLogging:
    """Tests for LoopRunner with session logging enabled."""

    def test_session_logging_enabled_by_default(self, prd_file, progress_file, sessions_dir):
        """Test session_logging is enabled by default (config default is True)."""
        with patch("zoyd.loop.loop.load_config", return_value=ZoydConfig()):
            runner = LoopRunner(
                prd_path=prd_file,
                progress_path=progress_file,
                sessions_dir=sessions_dir,
                tui_enabled=False,
            )
        assert runner.session_logging is True
        assert runner.session_logger is not None

    def test_session_logging_enabled_creates_logger(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test enabling session_logging creates a SessionLogger."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            tui_enabled=False,
        )
        assert runner.session_logging is True
        assert runner.session_logger is not None
        assert runner.sessions_dir == sessions_dir

    def test_session_logger_subscribes_to_events(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test session logger subscribes to runner events."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            tui_enabled=False,
        )
        # The logger should have subscribed to the emitter
        assert runner.session_logger._emitter is runner.events


class TestSessionLoggingOnComplete:
    """Tests for session logging when loop completes."""

    def test_session_created_on_run(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test session is created when run() is called."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=1,
            tui_enabled=False,
        )

        # Mock invoke_claude to return success
        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            mock_invoke.return_value = (0, "Done", 0.01)

            # Mock PRD updating (task completion)
            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [x] Task one
- [x] Task two
- [x] Task three
"""
                runner.run()

        # Session should exist in storage
        storage = FileStorage(sessions_dir)
        sessions = storage.list_sessions()
        assert len(sessions) == 1

    def test_session_ends_with_complete_status(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test session ends with complete status when all tasks done."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=1,
            tui_enabled=False,
        )

        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            mock_invoke.return_value = (0, "Done", 0.01)

            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [x] Task one
- [x] Task two
- [x] Task three
"""
                result = runner.run()

        # Should complete successfully
        assert result == 0

        # Check session statistics
        storage = FileStorage(sessions_dir)
        sessions = storage.list_sessions()
        session = storage.get_session(sessions[0].session_id)
        assert session.statistics.exit_code == 0
        assert session.statistics.exit_reason == "complete"
        assert session.metadata.ended_at is not None


class TestSessionLoggingOnMaxIterations:
    """Tests for session logging when max iterations reached."""

    def test_session_ends_on_max_iterations(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test session ends with max_iterations status."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=2,
            tui_enabled=False,
        )

        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            mock_invoke.return_value = (0, "Working on it", 0.01)

            # PRD never changes (tasks stay incomplete)
            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [ ] Task one
- [ ] Task two
- [ ] Task three
"""
                result = runner.run()

        # Should exit with code 1 (max iterations)
        assert result == 1

        storage = FileStorage(sessions_dir)
        sessions = storage.list_sessions()
        session = storage.get_session(sessions[0].session_id)
        assert session.statistics.exit_code == 1
        assert session.statistics.exit_reason == "max_iterations"
        assert session.statistics.total_iterations == 2


class TestSessionLoggingOnFailure:
    """Tests for session logging on failures."""

    def test_session_ends_on_fail_fast(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test session ends with fail_fast status."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=5,
            fail_fast=True,
            tui_enabled=False,
        )

        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            # Return failure
            mock_invoke.return_value = (1, "Error occurred", 0.0)

            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [ ] Task one
- [ ] Task two
"""
                result = runner.run()

        # Should exit with code 2 (failure)
        assert result == 2

        storage = FileStorage(sessions_dir)
        sessions = storage.list_sessions()
        session = storage.get_session(sessions[0].session_id)
        assert session.statistics.exit_code == 2
        assert session.statistics.exit_reason == "fail_fast"

    def test_session_ends_on_max_failures(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test session ends with max_failures status."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=10,
            fail_fast=False,
            tui_enabled=False,
        )

        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            mock_invoke.return_value = (1, "Error", 0.0)

            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [ ] Task one
"""
                result = runner.run()

        # Should exit with code 2 (max failures)
        assert result == 2

        storage = FileStorage(sessions_dir)
        sessions = storage.list_sessions()
        session = storage.get_session(sessions[0].session_id)
        assert session.statistics.exit_code == 2
        assert session.statistics.exit_reason == "max_failures"
        # Total iterations should be 3 (3 attempts before giving up)
        assert session.statistics.total_iterations == 3


class TestSessionLoggingEvents:
    """Tests for session logging event recording."""

    def test_events_recorded_during_loop(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test that events are recorded during the loop."""
        # Use side_effect list: first call incomplete, second call complete
        prd_incomplete = """# Test PRD

## Tasks

- [ ] Task one
- [ ] Task two
- [ ] Task three
"""
        prd_complete = """# Test PRD

## Tasks

- [x] Task one
- [x] Task two
- [x] Task three
"""

        # Patch read_prd BEFORE creating LoopRunner
        # Side effect needs: call 1 (init stats), call 2 (loop start), call 3 (after invoke)
        with patch("zoyd.prd.read_prd", side_effect=[prd_incomplete, prd_incomplete, prd_complete, prd_complete]) as mock_read:
            with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
                mock_invoke.return_value = (0, "Done", 0.01)

                runner = LoopRunner(
                    prd_path=prd_file,
                    progress_path=progress_file,
                    session_logging=True,
                    sessions_dir=sessions_dir,
                    max_iterations=2,  # Allow 2 iterations
                    tui_enabled=False,
                )
                runner.run()

        storage = FileStorage(sessions_dir)
        sessions = storage.list_sessions()
        session = storage.get_session(sessions[0].session_id)

        # Should have recorded events
        event_types = [e.event_type for e in session.events]
        assert "LOOP_START" in event_types
        assert "ITERATION_START" in event_types
        assert "CLAUDE_INVOKE" in event_types
        assert "CLAUDE_RESPONSE" in event_types
        assert "ITERATION_END" in event_types
        assert "LOOP_END" in event_types


class TestSessionLoggingOutputs:
    """Tests for Claude output recording."""

    def test_claude_outputs_recorded(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test that Claude outputs are recorded."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=2,
            tui_enabled=False,
        )

        prd_incomplete = """# Test PRD

## Tasks

- [ ] Task one
- [ ] Task two
- [ ] Task three
"""
        prd_complete = """# Test PRD

## Tasks

- [x] Task one
- [x] Task two
- [x] Task three
"""

        # Need to create runner INSIDE the mock context since __init__ doesn't read PRD
        # but run() does, and we need consistent mock behavior
        with patch("zoyd.prd.read_prd", side_effect=[prd_incomplete, prd_incomplete, prd_complete, prd_complete]):
            with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
                mock_invoke.return_value = (0, "I completed the task", 0.05)
                runner.run()

        storage = FileStorage(sessions_dir)
        sessions = storage.list_sessions()
        session = storage.get_session(sessions[0].session_id)

        # Should have recorded outputs
        assert len(session.outputs) >= 1
        output = session.outputs[0]
        assert output.return_code == 0
        assert output.cost_usd == 0.05


class TestSessionLoggingCostTracking:
    """Tests for cost tracking during session."""

    def test_cost_tracked_in_session(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test that cost is tracked in session statistics."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=2,
            max_cost=1.0,  # Enable cost tracking
            tui_enabled=False,
        )

        prd_incomplete = """# Test PRD

## Tasks

- [ ] Task one
- [ ] Task two
- [ ] Task three
"""
        prd_complete = """# Test PRD

## Tasks

- [x] Task one
- [x] Task two
- [x] Task three
"""

        # Side effect needs 4 values: init stats, loop iteration 1 start, after invoke, completion check
        with patch("zoyd.prd.read_prd", side_effect=[prd_incomplete, prd_incomplete, prd_complete, prd_complete]):
            with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
                mock_invoke.return_value = (0, "Done", 0.15)
                runner.run()

        storage = FileStorage(sessions_dir)
        sessions = storage.list_sessions()
        session = storage.get_session(sessions[0].session_id)

        # Cost should be recorded
        assert session.statistics.total_cost_usd >= 0.15


class TestSessionLoggingFileStructure:
    """Tests for session file structure."""

    def test_session_directory_created(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test that session directory is created."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=1,
            tui_enabled=False,
        )

        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            mock_invoke.return_value = (0, "Done", 0.01)

            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [x] Task one
"""
                runner.run()

        # Session directory should exist
        sessions_path = Path(sessions_dir)
        assert sessions_path.exists()
        session_dirs = list(sessions_path.iterdir())
        assert len(session_dirs) == 1
        assert session_dirs[0].is_dir()

    def test_session_json_created(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test that session.json is created."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=1,
            tui_enabled=False,
        )

        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            mock_invoke.return_value = (0, "Done", 0.01)

            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [x] Task one
"""
                runner.run()

        sessions_path = Path(sessions_dir)
        session_dirs = list(sessions_path.iterdir())
        session_json = session_dirs[0] / "session.json"
        assert session_json.exists()

        # Verify content
        with open(session_json) as f:
            data = json.load(f)
        assert "metadata" in data
        assert "statistics" in data

    def test_events_jsonl_created(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test that events.jsonl is created."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=1,
            tui_enabled=False,
        )

        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            mock_invoke.return_value = (0, "Done", 0.01)

            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [x] Task one
"""
                runner.run()

        sessions_path = Path(sessions_dir)
        session_dirs = list(sessions_path.iterdir())
        events_jsonl = session_dirs[0] / "events.jsonl"
        assert events_jsonl.exists()

        # Verify it has content
        content = events_jsonl.read_text()
        assert len(content) > 0


class TestSessionLoggingMetadata:
    """Tests for session metadata recording."""

    def test_prd_path_recorded(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test PRD path is recorded in session metadata."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=1,
            tui_enabled=False,
        )

        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            mock_invoke.return_value = (0, "Done", 0.01)

            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [x] Task one
"""
                runner.run()

        storage = FileStorage(sessions_dir)
        sessions = storage.list_sessions()
        session = storage.get_session(sessions[0].session_id)

        assert session.metadata.prd_path == str(prd_file.resolve())

    def test_model_recorded(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test model is recorded in session metadata."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=True,
            sessions_dir=sessions_dir,
            max_iterations=1,
            model="opus",
            tui_enabled=False,
        )

        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            mock_invoke.return_value = (0, "Done", 0.01)

            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [x] Task one
"""
                runner.run()

        storage = FileStorage(sessions_dir)
        sessions = storage.list_sessions()
        session = storage.get_session(sessions[0].session_id)

        assert session.metadata.model == "opus"


class TestSessionLoggingDisabled:
    """Tests for when session logging is disabled."""

    def test_no_sessions_created_when_disabled(
        self, prd_file, progress_file, sessions_dir
    ):
        """Test no sessions are created when logging is disabled."""
        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            session_logging=False,
            sessions_dir=sessions_dir,
            max_iterations=1,
            tui_enabled=False,
        )

        with patch("zoyd.loop.loop.invoke_claude") as mock_invoke:
            mock_invoke.return_value = (0, "Done", 0.01)

            with patch("zoyd.prd.read_prd") as mock_read:
                mock_read.return_value = """# Test PRD

## Tasks

- [x] Task one
"""
                runner.run()

        # Sessions directory should not be created
        sessions_path = Path(sessions_dir)
        assert not sessions_path.exists() or len(list(sessions_path.iterdir())) == 0
