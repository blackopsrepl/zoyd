"""Tests for session data models serialization."""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from zoyd.session.models import (
    ClaudeOutput,
    GitCommitRecord,
    Session,
    SessionEvent,
    SessionMetadata,
    SessionStatistics,
    TaskTransition,
    _generate_uuid,
    _now_isoformat,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_generate_uuid_returns_string(self):
        """Test that _generate_uuid returns a string."""
        result = _generate_uuid()
        assert isinstance(result, str)

    def test_generate_uuid_is_valid_uuid_format(self):
        """Test that _generate_uuid returns valid UUID format."""
        result = _generate_uuid()
        # UUID format: 8-4-4-4-12 hex characters
        parts = result.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_generate_uuid_is_unique(self):
        """Test that _generate_uuid generates unique values."""
        uuids = [_generate_uuid() for _ in range(100)]
        assert len(set(uuids)) == 100

    def test_now_isoformat_returns_string(self):
        """Test that _now_isoformat returns a string."""
        result = _now_isoformat()
        assert isinstance(result, str)

    def test_now_isoformat_is_valid_isoformat(self):
        """Test that _now_isoformat returns valid ISO format."""
        result = _now_isoformat()
        # Should be parseable as datetime
        datetime.fromisoformat(result)


class TestSessionMetadata:
    """Tests for SessionMetadata serialization."""

    def test_default_values(self):
        """Test that SessionMetadata has correct defaults."""
        meta = SessionMetadata()
        assert meta.session_id  # Should have a generated UUID
        assert meta.started_at  # Should have a timestamp
        assert meta.ended_at is None
        assert meta.prd_path == ""
        assert meta.progress_path == ""
        assert meta.model is None
        assert meta.max_iterations == 10
        assert meta.max_cost is None
        assert meta.auto_commit is True
        assert meta.fail_fast is False
        assert meta.working_dir == ""

    def test_to_dict(self):
        """Test to_dict serialization."""
        meta = SessionMetadata(
            session_id="test-uuid",
            started_at="2024-01-01T00:00:00",
            ended_at="2024-01-01T01:00:00",
            prd_path="PRD.md",
            progress_path="progress.txt",
            model="opus",
            max_iterations=20,
            max_cost=10.0,
            auto_commit=False,
            fail_fast=True,
            working_dir="/test",
        )
        result = meta.to_dict()
        assert result == {
            "session_id": "test-uuid",
            "started_at": "2024-01-01T00:00:00",
            "ended_at": "2024-01-01T01:00:00",
            "prd_path": "PRD.md",
            "progress_path": "progress.txt",
            "model": "opus",
            "max_iterations": 20,
            "max_cost": 10.0,
            "auto_commit": False,
            "fail_fast": True,
            "working_dir": "/test",
        }

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "session_id": "test-uuid",
            "started_at": "2024-01-01T00:00:00",
            "ended_at": "2024-01-01T01:00:00",
            "prd_path": "PRD.md",
            "progress_path": "progress.txt",
            "model": "opus",
            "max_iterations": 20,
            "max_cost": 10.0,
            "auto_commit": False,
            "fail_fast": True,
            "working_dir": "/test",
        }
        meta = SessionMetadata.from_dict(data)
        assert meta.session_id == "test-uuid"
        assert meta.started_at == "2024-01-01T00:00:00"
        assert meta.ended_at == "2024-01-01T01:00:00"
        assert meta.prd_path == "PRD.md"
        assert meta.progress_path == "progress.txt"
        assert meta.model == "opus"
        assert meta.max_iterations == 20
        assert meta.max_cost == 10.0
        assert meta.auto_commit is False
        assert meta.fail_fast is True
        assert meta.working_dir == "/test"

    def test_from_dict_with_defaults(self):
        """Test from_dict with missing fields uses defaults."""
        data = {}
        meta = SessionMetadata.from_dict(data)
        assert meta.session_id  # Generated
        assert meta.started_at  # Generated
        assert meta.ended_at is None
        assert meta.prd_path == ""
        assert meta.max_iterations == 10
        assert meta.auto_commit is True
        assert meta.fail_fast is False

    def test_roundtrip(self):
        """Test that to_dict -> from_dict preserves data."""
        original = SessionMetadata(
            session_id="test-uuid",
            started_at="2024-01-01T00:00:00",
            prd_path="PRD.md",
            model="sonnet",
            max_cost=5.0,
        )
        roundtrip = SessionMetadata.from_dict(original.to_dict())
        assert roundtrip.session_id == original.session_id
        assert roundtrip.started_at == original.started_at
        assert roundtrip.prd_path == original.prd_path
        assert roundtrip.model == original.model
        assert roundtrip.max_cost == original.max_cost

    def test_to_dict_is_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        meta = SessionMetadata(
            session_id="test-uuid",
            started_at="2024-01-01T00:00:00",
            model="opus",
        )
        # Should not raise
        json_str = json.dumps(meta.to_dict())
        assert "test-uuid" in json_str

    def test_from_config(self):
        """Test from_config class method."""
        # Create a mock config
        from zoyd.config import ZoydConfig

        config = ZoydConfig(
            prd="test.md",
            progress="prog.txt",
            model="opus",
            max_iterations=15,
            max_cost=8.0,
            auto_commit=False,
            fail_fast=True,
        )
        meta = SessionMetadata.from_config(config, working_dir="/work")
        assert meta.prd_path == "test.md"
        assert meta.progress_path == "prog.txt"
        assert meta.model == "opus"
        assert meta.max_iterations == 15
        assert meta.max_cost == 8.0
        assert meta.auto_commit is False
        assert meta.fail_fast is True
        assert meta.working_dir == "/work"


class TestSessionEvent:
    """Tests for SessionEvent serialization."""

    def test_default_values(self):
        """Test that SessionEvent has correct defaults."""
        event = SessionEvent()
        assert event.timestamp  # Should have a timestamp
        assert event.event_type == ""
        assert event.data == {}
        assert event.iteration is None

    def test_to_dict(self):
        """Test to_dict serialization."""
        event = SessionEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="ITERATION_START",
            data={"iteration": 1, "task": "Test task"},
            iteration=1,
        )
        result = event.to_dict()
        assert result == {
            "timestamp": "2024-01-01T00:00:00",
            "event_type": "ITERATION_START",
            "data": {"iteration": 1, "task": "Test task"},
            "iteration": 1,
        }

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "timestamp": "2024-01-01T00:00:00",
            "event_type": "CLAUDE_RESPONSE",
            "data": {"return_code": 0, "cost": 0.05},
            "iteration": 2,
        }
        event = SessionEvent.from_dict(data)
        assert event.timestamp == "2024-01-01T00:00:00"
        assert event.event_type == "CLAUDE_RESPONSE"
        assert event.data == {"return_code": 0, "cost": 0.05}
        assert event.iteration == 2

    def test_from_dict_with_defaults(self):
        """Test from_dict with missing fields uses defaults."""
        data = {}
        event = SessionEvent.from_dict(data)
        assert event.timestamp  # Generated
        assert event.event_type == ""
        assert event.data == {}
        assert event.iteration is None

    def test_roundtrip(self):
        """Test that to_dict -> from_dict preserves data."""
        original = SessionEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="TASK_COMPLETE",
            data={"task": "Implement feature"},
            iteration=3,
        )
        roundtrip = SessionEvent.from_dict(original.to_dict())
        assert roundtrip.timestamp == original.timestamp
        assert roundtrip.event_type == original.event_type
        assert roundtrip.data == original.data
        assert roundtrip.iteration == original.iteration

    def test_to_dict_is_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        event = SessionEvent(
            event_type="TEST",
            data={"nested": {"key": "value"}},
        )
        json_str = json.dumps(event.to_dict())
        assert "TEST" in json_str


class TestClaudeOutput:
    """Tests for ClaudeOutput serialization."""

    def test_default_values(self):
        """Test that ClaudeOutput has correct defaults."""
        output = ClaudeOutput()
        assert output.timestamp  # Should have a timestamp
        assert output.iteration == 0
        assert output.output == ""
        assert output.return_code == 0
        assert output.cost_usd is None
        assert output.duration_seconds is None
        assert output.task_text == ""

    def test_to_dict(self):
        """Test to_dict serialization."""
        output = ClaudeOutput(
            timestamp="2024-01-01T00:00:00",
            iteration=5,
            output="Here is my solution...",
            return_code=0,
            cost_usd=0.15,
            duration_seconds=30.5,
            task_text="Implement feature X",
        )
        result = output.to_dict()
        assert result == {
            "timestamp": "2024-01-01T00:00:00",
            "iteration": 5,
            "output": "Here is my solution...",
            "return_code": 0,
            "cost_usd": 0.15,
            "duration_seconds": 30.5,
            "task_text": "Implement feature X",
        }

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "timestamp": "2024-01-01T00:00:00",
            "iteration": 3,
            "output": "Task completed",
            "return_code": 1,
            "cost_usd": 0.25,
            "duration_seconds": 45.0,
            "task_text": "Fix bug",
        }
        output = ClaudeOutput.from_dict(data)
        assert output.timestamp == "2024-01-01T00:00:00"
        assert output.iteration == 3
        assert output.output == "Task completed"
        assert output.return_code == 1
        assert output.cost_usd == 0.25
        assert output.duration_seconds == 45.0
        assert output.task_text == "Fix bug"

    def test_from_dict_with_defaults(self):
        """Test from_dict with missing fields uses defaults."""
        data = {}
        output = ClaudeOutput.from_dict(data)
        assert output.timestamp  # Generated
        assert output.iteration == 0
        assert output.output == ""
        assert output.return_code == 0
        assert output.cost_usd is None
        assert output.duration_seconds is None
        assert output.task_text == ""

    def test_roundtrip(self):
        """Test that to_dict -> from_dict preserves data."""
        original = ClaudeOutput(
            timestamp="2024-01-01T00:00:00",
            iteration=7,
            output="Long output here...",
            return_code=0,
            cost_usd=0.08,
            duration_seconds=22.5,
            task_text="Write tests",
        )
        roundtrip = ClaudeOutput.from_dict(original.to_dict())
        assert roundtrip.timestamp == original.timestamp
        assert roundtrip.iteration == original.iteration
        assert roundtrip.output == original.output
        assert roundtrip.return_code == original.return_code
        assert roundtrip.cost_usd == original.cost_usd
        assert roundtrip.duration_seconds == original.duration_seconds
        assert roundtrip.task_text == original.task_text

    def test_to_dict_is_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        output = ClaudeOutput(
            output="Code:\n```python\nprint('hello')\n```",
        )
        json_str = json.dumps(output.to_dict())
        assert "python" in json_str


class TestTaskTransition:
    """Tests for TaskTransition serialization."""

    def test_default_values(self):
        """Test that TaskTransition has correct defaults."""
        trans = TaskTransition()
        assert trans.timestamp  # Should have a timestamp
        assert trans.iteration == 0
        assert trans.task_text == ""
        assert trans.task_line == 0
        assert trans.from_state == "incomplete"
        assert trans.to_state == "complete"

    def test_to_dict(self):
        """Test to_dict serialization."""
        trans = TaskTransition(
            timestamp="2024-01-01T00:00:00",
            iteration=2,
            task_text="Add tests",
            task_line=42,
            from_state="incomplete",
            to_state="complete",
        )
        result = trans.to_dict()
        assert result == {
            "timestamp": "2024-01-01T00:00:00",
            "iteration": 2,
            "task_text": "Add tests",
            "task_line": 42,
            "from_state": "incomplete",
            "to_state": "complete",
        }

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "timestamp": "2024-01-01T00:00:00",
            "iteration": 5,
            "task_text": "Fix bug",
            "task_line": 15,
            "from_state": "incomplete",
            "to_state": "complete",
        }
        trans = TaskTransition.from_dict(data)
        assert trans.timestamp == "2024-01-01T00:00:00"
        assert trans.iteration == 5
        assert trans.task_text == "Fix bug"
        assert trans.task_line == 15
        assert trans.from_state == "incomplete"
        assert trans.to_state == "complete"

    def test_from_dict_with_defaults(self):
        """Test from_dict with missing fields uses defaults."""
        data = {}
        trans = TaskTransition.from_dict(data)
        assert trans.timestamp  # Generated
        assert trans.iteration == 0
        assert trans.task_text == ""
        assert trans.task_line == 0
        assert trans.from_state == "incomplete"
        assert trans.to_state == "complete"

    def test_roundtrip(self):
        """Test that to_dict -> from_dict preserves data."""
        original = TaskTransition(
            timestamp="2024-01-01T00:00:00",
            iteration=3,
            task_text="Implement API",
            task_line=99,
            from_state="incomplete",
            to_state="complete",
        )
        roundtrip = TaskTransition.from_dict(original.to_dict())
        assert roundtrip.timestamp == original.timestamp
        assert roundtrip.iteration == original.iteration
        assert roundtrip.task_text == original.task_text
        assert roundtrip.task_line == original.task_line
        assert roundtrip.from_state == original.from_state
        assert roundtrip.to_state == original.to_state

    def test_to_dict_is_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        trans = TaskTransition(task_text="Task with special chars: <>&")
        json_str = json.dumps(trans.to_dict())
        assert "special chars" in json_str


class TestGitCommitRecord:
    """Tests for GitCommitRecord serialization."""

    def test_default_values(self):
        """Test that GitCommitRecord has correct defaults."""
        commit = GitCommitRecord()
        assert commit.timestamp  # Should have a timestamp
        assert commit.iteration == 0
        assert commit.commit_hash == ""
        assert commit.message == ""
        assert commit.files_changed == 0
        assert commit.task_text == ""

    def test_to_dict(self):
        """Test to_dict serialization."""
        commit = GitCommitRecord(
            timestamp="2024-01-01T00:00:00",
            iteration=4,
            commit_hash="abc123def456",
            message="feat: add new feature",
            files_changed=3,
            task_text="Add feature X",
        )
        result = commit.to_dict()
        assert result == {
            "timestamp": "2024-01-01T00:00:00",
            "iteration": 4,
            "commit_hash": "abc123def456",
            "message": "feat: add new feature",
            "files_changed": 3,
            "task_text": "Add feature X",
        }

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "timestamp": "2024-01-01T00:00:00",
            "iteration": 6,
            "commit_hash": "xyz789",
            "message": "fix: resolve issue",
            "files_changed": 5,
            "task_text": "Fix bug Y",
        }
        commit = GitCommitRecord.from_dict(data)
        assert commit.timestamp == "2024-01-01T00:00:00"
        assert commit.iteration == 6
        assert commit.commit_hash == "xyz789"
        assert commit.message == "fix: resolve issue"
        assert commit.files_changed == 5
        assert commit.task_text == "Fix bug Y"

    def test_from_dict_with_defaults(self):
        """Test from_dict with missing fields uses defaults."""
        data = {}
        commit = GitCommitRecord.from_dict(data)
        assert commit.timestamp  # Generated
        assert commit.iteration == 0
        assert commit.commit_hash == ""
        assert commit.message == ""
        assert commit.files_changed == 0
        assert commit.task_text == ""

    def test_roundtrip(self):
        """Test that to_dict -> from_dict preserves data."""
        original = GitCommitRecord(
            timestamp="2024-01-01T00:00:00",
            iteration=8,
            commit_hash="full-sha-hash-here",
            message="chore: update deps",
            files_changed=10,
            task_text="Update dependencies",
        )
        roundtrip = GitCommitRecord.from_dict(original.to_dict())
        assert roundtrip.timestamp == original.timestamp
        assert roundtrip.iteration == original.iteration
        assert roundtrip.commit_hash == original.commit_hash
        assert roundtrip.message == original.message
        assert roundtrip.files_changed == original.files_changed
        assert roundtrip.task_text == original.task_text

    def test_to_dict_is_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        commit = GitCommitRecord(message="Commit message\nwith newline")
        json_str = json.dumps(commit.to_dict())
        assert "newline" in json_str


class TestSessionStatistics:
    """Tests for SessionStatistics serialization."""

    def test_default_values(self):
        """Test that SessionStatistics has correct defaults."""
        stats = SessionStatistics()
        assert stats.total_iterations == 0
        assert stats.successful_iterations == 0
        assert stats.failed_iterations == 0
        assert stats.tasks_completed == 0
        assert stats.tasks_total == 0
        assert stats.total_cost_usd == 0.0
        assert stats.total_duration_seconds == 0.0
        assert stats.commits_made == 0
        assert stats.exit_code == 0
        assert stats.exit_reason == ""

    def test_to_dict(self):
        """Test to_dict serialization."""
        stats = SessionStatistics(
            total_iterations=10,
            successful_iterations=8,
            failed_iterations=2,
            tasks_completed=5,
            tasks_total=7,
            total_cost_usd=1.25,
            total_duration_seconds=300.0,
            commits_made=5,
            exit_code=0,
            exit_reason="complete",
        )
        result = stats.to_dict()
        assert result == {
            "total_iterations": 10,
            "successful_iterations": 8,
            "failed_iterations": 2,
            "tasks_completed": 5,
            "tasks_total": 7,
            "total_cost_usd": 1.25,
            "total_duration_seconds": 300.0,
            "commits_made": 5,
            "exit_code": 0,
            "exit_reason": "complete",
        }

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "total_iterations": 15,
            "successful_iterations": 12,
            "failed_iterations": 3,
            "tasks_completed": 8,
            "tasks_total": 10,
            "total_cost_usd": 2.50,
            "total_duration_seconds": 600.0,
            "commits_made": 8,
            "exit_code": 1,
            "exit_reason": "max_iterations",
        }
        stats = SessionStatistics.from_dict(data)
        assert stats.total_iterations == 15
        assert stats.successful_iterations == 12
        assert stats.failed_iterations == 3
        assert stats.tasks_completed == 8
        assert stats.tasks_total == 10
        assert stats.total_cost_usd == 2.50
        assert stats.total_duration_seconds == 600.0
        assert stats.commits_made == 8
        assert stats.exit_code == 1
        assert stats.exit_reason == "max_iterations"

    def test_from_dict_with_defaults(self):
        """Test from_dict with missing fields uses defaults."""
        data = {}
        stats = SessionStatistics.from_dict(data)
        assert stats.total_iterations == 0
        assert stats.successful_iterations == 0
        assert stats.failed_iterations == 0
        assert stats.tasks_completed == 0
        assert stats.tasks_total == 0
        assert stats.total_cost_usd == 0.0
        assert stats.total_duration_seconds == 0.0
        assert stats.commits_made == 0
        assert stats.exit_code == 0
        assert stats.exit_reason == ""

    def test_roundtrip(self):
        """Test that to_dict -> from_dict preserves data."""
        original = SessionStatistics(
            total_iterations=20,
            successful_iterations=18,
            failed_iterations=2,
            tasks_completed=15,
            tasks_total=15,
            total_cost_usd=3.75,
            total_duration_seconds=900.0,
            commits_made=15,
            exit_code=0,
            exit_reason="complete",
        )
        roundtrip = SessionStatistics.from_dict(original.to_dict())
        assert roundtrip.total_iterations == original.total_iterations
        assert roundtrip.successful_iterations == original.successful_iterations
        assert roundtrip.failed_iterations == original.failed_iterations
        assert roundtrip.tasks_completed == original.tasks_completed
        assert roundtrip.tasks_total == original.tasks_total
        assert roundtrip.total_cost_usd == original.total_cost_usd
        assert roundtrip.total_duration_seconds == original.total_duration_seconds
        assert roundtrip.commits_made == original.commits_made
        assert roundtrip.exit_code == original.exit_code
        assert roundtrip.exit_reason == original.exit_reason

    def test_to_dict_is_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        stats = SessionStatistics(
            total_iterations=5,
            total_cost_usd=0.5,
        )
        json_str = json.dumps(stats.to_dict())
        assert "total_iterations" in json_str


class TestSession:
    """Tests for Session serialization."""

    def test_default_values(self):
        """Test that Session has correct defaults."""
        session = Session()
        assert session.metadata is not None
        assert session.statistics is not None
        assert session.events == []
        assert session.outputs == []
        assert session.transitions == []
        assert session.commits == []

    def test_session_id_property(self):
        """Test session_id property."""
        session = Session(
            metadata=SessionMetadata(session_id="test-id"),
        )
        assert session.session_id == "test-id"

    def test_is_complete_property_false(self):
        """Test is_complete property when not ended."""
        session = Session(
            metadata=SessionMetadata(ended_at=None),
        )
        assert session.is_complete is False

    def test_is_complete_property_true(self):
        """Test is_complete property when ended."""
        session = Session(
            metadata=SessionMetadata(ended_at="2024-01-01T01:00:00"),
        )
        assert session.is_complete is True

    def test_to_dict_without_details(self):
        """Test to_dict without details."""
        session = Session(
            metadata=SessionMetadata(session_id="test-id"),
            statistics=SessionStatistics(total_iterations=5),
            events=[SessionEvent(event_type="TEST")],
            outputs=[ClaudeOutput(output="test output")],
            transitions=[TaskTransition(task_text="test task")],
            commits=[GitCommitRecord(message="test commit")],
        )
        result = session.to_dict(include_details=False)
        assert "metadata" in result
        assert "statistics" in result
        assert "events" not in result
        assert "outputs" not in result
        assert "transitions" not in result
        assert "commits" not in result

    def test_to_dict_with_details(self):
        """Test to_dict with details."""
        session = Session(
            metadata=SessionMetadata(session_id="test-id"),
            statistics=SessionStatistics(total_iterations=5),
            events=[SessionEvent(event_type="TEST")],
            outputs=[ClaudeOutput(output="test output")],
            transitions=[TaskTransition(task_text="test task")],
            commits=[GitCommitRecord(message="test commit")],
        )
        result = session.to_dict(include_details=True)
        assert "metadata" in result
        assert "statistics" in result
        assert "events" in result
        assert len(result["events"]) == 1
        assert result["events"][0]["event_type"] == "TEST"
        assert "outputs" in result
        assert len(result["outputs"]) == 1
        assert result["outputs"][0]["output"] == "test output"
        assert "transitions" in result
        assert len(result["transitions"]) == 1
        assert result["transitions"][0]["task_text"] == "test task"
        assert "commits" in result
        assert len(result["commits"]) == 1
        assert result["commits"][0]["message"] == "test commit"

    def test_from_dict_without_details(self):
        """Test from_dict without details."""
        data = {
            "metadata": {
                "session_id": "test-id",
                "started_at": "2024-01-01T00:00:00",
            },
            "statistics": {
                "total_iterations": 10,
            },
        }
        session = Session.from_dict(data)
        assert session.metadata.session_id == "test-id"
        assert session.statistics.total_iterations == 10
        assert session.events == []
        assert session.outputs == []
        assert session.transitions == []
        assert session.commits == []

    def test_from_dict_with_details(self):
        """Test from_dict with details."""
        data = {
            "metadata": {"session_id": "test-id"},
            "statistics": {"total_iterations": 10},
            "events": [{"event_type": "TEST", "timestamp": "2024-01-01T00:00:00"}],
            "outputs": [{"output": "hello", "iteration": 1}],
            "transitions": [{"task_text": "task", "iteration": 1}],
            "commits": [{"message": "commit", "iteration": 1}],
        }
        session = Session.from_dict(data)
        assert session.metadata.session_id == "test-id"
        assert len(session.events) == 1
        assert session.events[0].event_type == "TEST"
        assert len(session.outputs) == 1
        assert session.outputs[0].output == "hello"
        assert len(session.transitions) == 1
        assert session.transitions[0].task_text == "task"
        assert len(session.commits) == 1
        assert session.commits[0].message == "commit"

    def test_from_dict_with_empty_dict(self):
        """Test from_dict with empty dict."""
        session = Session.from_dict({})
        assert session.metadata is not None
        assert session.statistics is not None
        assert session.events == []
        assert session.outputs == []

    def test_roundtrip_without_details(self):
        """Test roundtrip serialization without details."""
        original = Session(
            metadata=SessionMetadata(
                session_id="test-id",
                prd_path="PRD.md",
            ),
            statistics=SessionStatistics(
                total_iterations=5,
                exit_reason="complete",
            ),
        )
        roundtrip = Session.from_dict(original.to_dict(include_details=False))
        assert roundtrip.metadata.session_id == original.metadata.session_id
        assert roundtrip.metadata.prd_path == original.metadata.prd_path
        assert roundtrip.statistics.total_iterations == original.statistics.total_iterations
        assert roundtrip.statistics.exit_reason == original.statistics.exit_reason

    def test_roundtrip_with_details(self):
        """Test roundtrip serialization with details."""
        original = Session(
            metadata=SessionMetadata(session_id="test-id"),
            statistics=SessionStatistics(total_iterations=5),
            events=[SessionEvent(event_type="E1"), SessionEvent(event_type="E2")],
            outputs=[ClaudeOutput(output="O1")],
            transitions=[TaskTransition(task_text="T1")],
            commits=[GitCommitRecord(message="C1")],
        )
        roundtrip = Session.from_dict(original.to_dict(include_details=True))
        assert len(roundtrip.events) == 2
        assert roundtrip.events[0].event_type == "E1"
        assert roundtrip.events[1].event_type == "E2"
        assert len(roundtrip.outputs) == 1
        assert roundtrip.outputs[0].output == "O1"
        assert len(roundtrip.transitions) == 1
        assert roundtrip.transitions[0].task_text == "T1"
        assert len(roundtrip.commits) == 1
        assert roundtrip.commits[0].message == "C1"

    def test_to_dict_is_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        session = Session(
            metadata=SessionMetadata(session_id="test-id"),
            statistics=SessionStatistics(total_iterations=5),
            events=[SessionEvent(event_type="TEST")],
            outputs=[ClaudeOutput(output="test")],
            transitions=[TaskTransition(task_text="task")],
            commits=[GitCommitRecord(message="commit")],
        )
        # Both versions should be serializable
        json.dumps(session.to_dict(include_details=False))
        json.dumps(session.to_dict(include_details=True))

    def test_to_dict_empty_lists_with_details(self):
        """Test to_dict with empty lists includes them when include_details is True."""
        session = Session()
        result = session.to_dict(include_details=True)
        assert result["events"] == []
        assert result["outputs"] == []
        assert result["transitions"] == []
        assert result["commits"] == []


class TestModuleExports:
    """Tests for module exports."""

    def test_session_metadata_exported(self):
        """Test SessionMetadata is exported."""
        from zoyd.session import SessionMetadata

        assert SessionMetadata is not None

    def test_session_event_exported(self):
        """Test SessionEvent is exported."""
        from zoyd.session import SessionEvent

        assert SessionEvent is not None

    def test_claude_output_exported(self):
        """Test ClaudeOutput is exported."""
        from zoyd.session import ClaudeOutput

        assert ClaudeOutput is not None

    def test_task_transition_exported(self):
        """Test TaskTransition is exported."""
        from zoyd.session import TaskTransition

        assert TaskTransition is not None

    def test_git_commit_record_exported(self):
        """Test GitCommitRecord is exported."""
        from zoyd.session import GitCommitRecord

        assert GitCommitRecord is not None

    def test_session_statistics_exported(self):
        """Test SessionStatistics is exported."""
        from zoyd.session import SessionStatistics

        assert SessionStatistics is not None

    def test_session_exported(self):
        """Test Session is exported."""
        from zoyd.session import Session

        assert Session is not None
