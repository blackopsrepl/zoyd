"""Tests for session storage backends."""

import json
import tempfile
from pathlib import Path

import pytest

from zoyd.config import load_config
from zoyd.session.models import (
    ClaudeOutput,
    GitCommitRecord,
    Session,
    SessionEvent,
    SessionMetadata,
    SessionStatistics,
    TaskTransition,
)
from zoyd.session.storage import (
    FileStorage,
    InMemoryStorage,
    RedisStorage,
    SessionStorage,
    append_jsonl,
    create_storage,
    from_json,
    read_json,
    read_jsonl,
    to_json,
    write_json,
)


# =============================================================================
# Serialization Helper Tests
# =============================================================================


class TestToJson:
    """Tests for to_json helper function."""

    def test_to_json_dict(self):
        """Test to_json with a plain dict."""
        data = {"key": "value", "number": 42}
        result = to_json(data)
        assert json.loads(result) == data

    def test_to_json_with_to_dict_method(self):
        """Test to_json with object having to_dict method."""
        meta = SessionMetadata(session_id="test-id")
        result = to_json(meta)
        parsed = json.loads(result)
        assert parsed["session_id"] == "test-id"

    def test_to_json_with_indent(self):
        """Test to_json with indentation."""
        data = {"key": "value"}
        result = to_json(data, indent=2)
        assert "\n" in result
        assert "  " in result

    def test_to_json_compact(self):
        """Test to_json without indentation is compact."""
        data = {"key": "value"}
        result = to_json(data)
        assert "\n" not in result

    def test_to_json_handles_datetime(self):
        """Test to_json uses default=str for non-serializable types."""
        from datetime import datetime

        data = {"time": datetime(2024, 1, 1, 12, 0)}
        result = to_json(data)
        assert "2024" in result


class TestFromJson:
    """Tests for from_json helper function."""

    def test_from_json_dict(self):
        """Test from_json returns dict when no class specified."""
        json_str = '{"key": "value"}'
        result = from_json(json_str)
        assert result == {"key": "value"}

    def test_from_json_with_class(self):
        """Test from_json creates class instance."""
        json_str = '{"session_id": "test-id", "started_at": "2024-01-01T00:00:00"}'
        result = from_json(json_str, SessionMetadata)
        assert isinstance(result, SessionMetadata)
        assert result.session_id == "test-id"

    def test_from_json_invalid_json_raises(self):
        """Test from_json raises on invalid JSON."""
        with pytest.raises(json.JSONDecodeError):
            from_json("not valid json")


class TestAppendJsonl:
    """Tests for append_jsonl helper function."""

    def test_append_jsonl_creates_file(self, tmp_path):
        """Test append_jsonl creates new file."""
        path = tmp_path / "test.jsonl"
        append_jsonl(path, {"key": "value"})
        assert path.exists()

    def test_append_jsonl_appends(self, tmp_path):
        """Test append_jsonl appends to existing file."""
        path = tmp_path / "test.jsonl"
        append_jsonl(path, {"key": "value1"})
        append_jsonl(path, {"key": "value2"})
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_append_jsonl_with_to_dict(self, tmp_path):
        """Test append_jsonl with object having to_dict."""
        path = tmp_path / "test.jsonl"
        event = SessionEvent(event_type="TEST")
        append_jsonl(path, event)
        content = path.read_text()
        assert "TEST" in content

    def test_append_jsonl_creates_parent_dirs(self, tmp_path):
        """Test append_jsonl creates parent directories."""
        path = tmp_path / "subdir" / "deep" / "test.jsonl"
        append_jsonl(path, {"key": "value"})
        assert path.exists()


class TestReadJsonl:
    """Tests for read_jsonl helper function."""

    def test_read_jsonl_empty_list_if_no_file(self, tmp_path):
        """Test read_jsonl returns empty list if file doesn't exist."""
        path = tmp_path / "nonexistent.jsonl"
        result = read_jsonl(path)
        assert result == []

    def test_read_jsonl_reads_all_lines(self, tmp_path):
        """Test read_jsonl reads all lines."""
        path = tmp_path / "test.jsonl"
        path.write_text('{"key": "value1"}\n{"key": "value2"}\n')
        result = read_jsonl(path)
        assert len(result) == 2
        assert result[0]["key"] == "value1"
        assert result[1]["key"] == "value2"

    def test_read_jsonl_with_class(self, tmp_path):
        """Test read_jsonl creates class instances."""
        path = tmp_path / "test.jsonl"
        path.write_text('{"event_type": "E1"}\n{"event_type": "E2"}\n')
        result = read_jsonl(path, SessionEvent)
        assert len(result) == 2
        assert isinstance(result[0], SessionEvent)
        assert result[0].event_type == "E1"

    def test_read_jsonl_skips_empty_lines(self, tmp_path):
        """Test read_jsonl skips empty lines."""
        path = tmp_path / "test.jsonl"
        path.write_text('{"key": "value1"}\n\n{"key": "value2"}\n')
        result = read_jsonl(path)
        assert len(result) == 2


class TestWriteJson:
    """Tests for write_json helper function."""

    def test_write_json_creates_file(self, tmp_path):
        """Test write_json creates new file."""
        path = tmp_path / "test.json"
        write_json(path, {"key": "value"})
        assert path.exists()

    def test_write_json_overwrites(self, tmp_path):
        """Test write_json overwrites existing file."""
        path = tmp_path / "test.json"
        write_json(path, {"old": "value"})
        write_json(path, {"new": "value"})
        content = path.read_text()
        assert "new" in content
        assert "old" not in content

    def test_write_json_with_indent(self, tmp_path):
        """Test write_json with indentation."""
        path = tmp_path / "test.json"
        write_json(path, {"key": "value"}, indent=4)
        content = path.read_text()
        assert "\n" in content

    def test_write_json_creates_parent_dirs(self, tmp_path):
        """Test write_json creates parent directories."""
        path = tmp_path / "subdir" / "test.json"
        write_json(path, {"key": "value"})
        assert path.exists()


class TestReadJson:
    """Tests for read_json helper function."""

    def test_read_json_returns_none_if_no_file(self, tmp_path):
        """Test read_json returns None if file doesn't exist."""
        path = tmp_path / "nonexistent.json"
        result = read_json(path)
        assert result is None

    def test_read_json_reads_file(self, tmp_path):
        """Test read_json reads file contents."""
        path = tmp_path / "test.json"
        path.write_text('{"key": "value"}')
        result = read_json(path)
        assert result == {"key": "value"}

    def test_read_json_with_class(self, tmp_path):
        """Test read_json creates class instance."""
        path = tmp_path / "test.json"
        path.write_text('{"session_id": "test-id"}')
        result = read_json(path, SessionMetadata)
        assert isinstance(result, SessionMetadata)
        assert result.session_id == "test-id"


# =============================================================================
# InMemoryStorage Tests
# =============================================================================


class TestInMemoryStorageCreate:
    """Tests for InMemoryStorage.create_session."""

    def test_create_session_returns_id(self):
        """Test create_session returns session ID."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        result = storage.create_session(meta)
        assert result == "test-id"

    def test_create_session_stores_session(self):
        """Test create_session stores the session."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        assert storage.get_session("test-id") is not None

    def test_create_session_initializes_empty_lists(self):
        """Test create_session initializes empty lists."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        session = storage.get_session("test-id")
        assert session.events == []
        assert session.outputs == []
        assert session.transitions == []
        assert session.commits == []


class TestInMemoryStorageEndSession:
    """Tests for InMemoryStorage.end_session."""

    def test_end_session_sets_ended_at(self):
        """Test end_session sets ended_at timestamp."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        storage.end_session("test-id", "2024-01-01T01:00:00")
        session = storage.get_session("test-id")
        assert session.metadata.ended_at == "2024-01-01T01:00:00"

    def test_end_session_with_default_timestamp(self):
        """Test end_session uses current time if not provided."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        storage.end_session("test-id")
        session = storage.get_session("test-id")
        assert session.metadata.ended_at is not None

    def test_end_session_nonexistent_does_nothing(self):
        """Test end_session on nonexistent session does nothing."""
        storage = InMemoryStorage()
        storage.end_session("nonexistent")  # Should not raise


class TestInMemoryStorageGetSession:
    """Tests for InMemoryStorage.get_session."""

    def test_get_session_returns_session(self):
        """Test get_session returns stored session."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id", prd_path="PRD.md")
        storage.create_session(meta)
        session = storage.get_session("test-id")
        assert session.metadata.prd_path == "PRD.md"

    def test_get_session_returns_none_if_not_found(self):
        """Test get_session returns None for unknown ID."""
        storage = InMemoryStorage()
        assert storage.get_session("unknown") is None


class TestInMemoryStorageGetMetadata:
    """Tests for InMemoryStorage.get_metadata."""

    def test_get_metadata_returns_metadata(self):
        """Test get_metadata returns session metadata."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id", prd_path="PRD.md")
        storage.create_session(meta)
        result = storage.get_metadata("test-id")
        assert result.prd_path == "PRD.md"

    def test_get_metadata_returns_none_if_not_found(self):
        """Test get_metadata returns None for unknown ID."""
        storage = InMemoryStorage()
        assert storage.get_metadata("unknown") is None


class TestInMemoryStorageUpdateStatistics:
    """Tests for InMemoryStorage.update_statistics."""

    def test_update_statistics_replaces_stats(self):
        """Test update_statistics replaces statistics."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        new_stats = SessionStatistics(total_iterations=10)
        storage.update_statistics("test-id", new_stats)
        session = storage.get_session("test-id")
        assert session.statistics.total_iterations == 10

    def test_update_statistics_nonexistent_does_nothing(self):
        """Test update_statistics on nonexistent session does nothing."""
        storage = InMemoryStorage()
        storage.update_statistics("nonexistent", SessionStatistics())


class TestInMemoryStorageAddEvent:
    """Tests for InMemoryStorage.add_event."""

    def test_add_event_appends(self):
        """Test add_event appends to events list."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        event = SessionEvent(event_type="TEST")
        storage.add_event("test-id", event)
        session = storage.get_session("test-id")
        assert len(session.events) == 1
        assert session.events[0].event_type == "TEST"

    def test_add_event_multiple(self):
        """Test add_event appends multiple events."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        storage.add_event("test-id", SessionEvent(event_type="E1"))
        storage.add_event("test-id", SessionEvent(event_type="E2"))
        session = storage.get_session("test-id")
        assert len(session.events) == 2


class TestInMemoryStorageAddOutput:
    """Tests for InMemoryStorage.add_output."""

    def test_add_output_appends(self):
        """Test add_output appends to outputs list."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        output = ClaudeOutput(output="test output")
        storage.add_output("test-id", output)
        session = storage.get_session("test-id")
        assert len(session.outputs) == 1


class TestInMemoryStorageAddTransition:
    """Tests for InMemoryStorage.add_transition."""

    def test_add_transition_appends(self):
        """Test add_transition appends to transitions list."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        trans = TaskTransition(task_text="test task")
        storage.add_transition("test-id", trans)
        session = storage.get_session("test-id")
        assert len(session.transitions) == 1


class TestInMemoryStorageAddCommit:
    """Tests for InMemoryStorage.add_commit."""

    def test_add_commit_appends(self):
        """Test add_commit appends to commits list."""
        storage = InMemoryStorage()
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        commit = GitCommitRecord(message="test commit")
        storage.add_commit("test-id", commit)
        session = storage.get_session("test-id")
        assert len(session.commits) == 1


class TestInMemoryStorageListSessions:
    """Tests for InMemoryStorage.list_sessions."""

    def test_list_sessions_empty(self):
        """Test list_sessions returns empty list when no sessions."""
        storage = InMemoryStorage()
        assert storage.list_sessions() == []

    def test_list_sessions_returns_all(self):
        """Test list_sessions returns all sessions."""
        storage = InMemoryStorage()
        storage.create_session(SessionMetadata(session_id="s1"))
        storage.create_session(SessionMetadata(session_id="s2"))
        result = storage.list_sessions()
        assert len(result) == 2

    def test_list_sessions_sorted_newest_first(self):
        """Test list_sessions returns newest first."""
        storage = InMemoryStorage()
        storage.create_session(
            SessionMetadata(session_id="old", started_at="2024-01-01T00:00:00")
        )
        storage.create_session(
            SessionMetadata(session_id="new", started_at="2024-01-02T00:00:00")
        )
        result = storage.list_sessions()
        assert result[0].session_id == "new"
        assert result[1].session_id == "old"

    def test_list_sessions_with_limit(self):
        """Test list_sessions with limit."""
        storage = InMemoryStorage()
        for i in range(5):
            storage.create_session(SessionMetadata(session_id=f"s{i}"))
        result = storage.list_sessions(limit=3)
        assert len(result) == 3

    def test_list_sessions_with_offset(self):
        """Test list_sessions with offset."""
        storage = InMemoryStorage()
        storage.create_session(
            SessionMetadata(session_id="s0", started_at="2024-01-01T00:00:00")
        )
        storage.create_session(
            SessionMetadata(session_id="s1", started_at="2024-01-02T00:00:00")
        )
        storage.create_session(
            SessionMetadata(session_id="s2", started_at="2024-01-03T00:00:00")
        )
        result = storage.list_sessions(offset=1)
        assert len(result) == 2
        assert result[0].session_id == "s1"


class TestInMemoryStorageDeleteSession:
    """Tests for InMemoryStorage.delete_session."""

    def test_delete_session_removes(self):
        """Test delete_session removes the session."""
        storage = InMemoryStorage()
        storage.create_session(SessionMetadata(session_id="test-id"))
        result = storage.delete_session("test-id")
        assert result is True
        assert storage.get_session("test-id") is None

    def test_delete_session_returns_false_if_not_found(self):
        """Test delete_session returns False if not found."""
        storage = InMemoryStorage()
        result = storage.delete_session("nonexistent")
        assert result is False


class TestInMemoryStorageClear:
    """Tests for InMemoryStorage.clear."""

    def test_clear_removes_all(self):
        """Test clear removes all sessions."""
        storage = InMemoryStorage()
        storage.create_session(SessionMetadata(session_id="s1"))
        storage.create_session(SessionMetadata(session_id="s2"))
        storage.clear()
        assert storage.list_sessions() == []


# =============================================================================
# FileStorage Tests
# =============================================================================


class TestFileStorageCreate:
    """Tests for FileStorage.create_session."""

    def test_create_session_returns_id(self, tmp_path):
        """Test create_session returns session ID."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id")
        result = storage.create_session(meta)
        assert result == "test-id"

    def test_create_session_creates_directory(self, tmp_path):
        """Test create_session creates session directory."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        assert (tmp_path / "sessions" / "test-id").is_dir()

    def test_create_session_writes_session_json(self, tmp_path):
        """Test create_session writes session.json."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id", prd_path="PRD.md")
        storage.create_session(meta)
        session_file = tmp_path / "sessions" / "test-id" / "session.json"
        assert session_file.exists()
        content = json.loads(session_file.read_text())
        assert content["metadata"]["prd_path"] == "PRD.md"


class TestFileStorageEndSession:
    """Tests for FileStorage.end_session."""

    def test_end_session_sets_ended_at(self, tmp_path):
        """Test end_session sets ended_at timestamp."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        storage.end_session("test-id", "2024-01-01T01:00:00")
        session = storage.get_session("test-id")
        assert session.metadata.ended_at == "2024-01-01T01:00:00"

    def test_end_session_with_default_timestamp(self, tmp_path):
        """Test end_session uses current time if not provided."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        storage.end_session("test-id")
        session = storage.get_session("test-id")
        assert session.metadata.ended_at is not None

    def test_end_session_nonexistent_does_nothing(self, tmp_path):
        """Test end_session on nonexistent session does nothing."""
        storage = FileStorage(tmp_path / "sessions")
        storage.end_session("nonexistent")  # Should not raise


class TestFileStorageGetSession:
    """Tests for FileStorage.get_session."""

    def test_get_session_returns_full_session(self, tmp_path):
        """Test get_session returns full session with all data."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id", prd_path="PRD.md")
        storage.create_session(meta)
        storage.add_event("test-id", SessionEvent(event_type="TEST"))
        storage.add_output("test-id", ClaudeOutput(output="hello"))
        storage.add_transition("test-id", TaskTransition(task_text="task"))
        storage.add_commit("test-id", GitCommitRecord(message="commit"))

        session = storage.get_session("test-id")
        assert session.metadata.prd_path == "PRD.md"
        assert len(session.events) == 1
        assert len(session.outputs) == 1
        assert len(session.transitions) == 1
        assert len(session.commits) == 1

    def test_get_session_returns_none_if_not_found(self, tmp_path):
        """Test get_session returns None for unknown ID."""
        storage = FileStorage(tmp_path / "sessions")
        assert storage.get_session("unknown") is None


class TestFileStorageGetMetadata:
    """Tests for FileStorage.get_metadata."""

    def test_get_metadata_returns_metadata(self, tmp_path):
        """Test get_metadata returns session metadata."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id", prd_path="PRD.md")
        storage.create_session(meta)
        result = storage.get_metadata("test-id")
        assert result.prd_path == "PRD.md"

    def test_get_metadata_returns_none_if_not_found(self, tmp_path):
        """Test get_metadata returns None for unknown ID."""
        storage = FileStorage(tmp_path / "sessions")
        assert storage.get_metadata("unknown") is None


class TestFileStorageUpdateStatistics:
    """Tests for FileStorage.update_statistics."""

    def test_update_statistics_replaces_stats(self, tmp_path):
        """Test update_statistics replaces statistics."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        new_stats = SessionStatistics(total_iterations=10, exit_reason="complete")
        storage.update_statistics("test-id", new_stats)
        session = storage.get_session("test-id")
        assert session.statistics.total_iterations == 10
        assert session.statistics.exit_reason == "complete"

    def test_update_statistics_nonexistent_does_nothing(self, tmp_path):
        """Test update_statistics on nonexistent session does nothing."""
        storage = FileStorage(tmp_path / "sessions")
        storage.update_statistics("nonexistent", SessionStatistics())


class TestFileStorageAddEvent:
    """Tests for FileStorage.add_event."""

    def test_add_event_appends_to_jsonl(self, tmp_path):
        """Test add_event appends to events.jsonl."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        storage.add_event("test-id", SessionEvent(event_type="E1"))
        storage.add_event("test-id", SessionEvent(event_type="E2"))

        events_file = tmp_path / "sessions" / "test-id" / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_add_event_nonexistent_does_nothing(self, tmp_path):
        """Test add_event on nonexistent session does nothing."""
        storage = FileStorage(tmp_path / "sessions")
        storage.add_event("nonexistent", SessionEvent())  # Should not raise


class TestFileStorageAddOutput:
    """Tests for FileStorage.add_output."""

    def test_add_output_appends_to_jsonl(self, tmp_path):
        """Test add_output appends to outputs.jsonl."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        storage.add_output("test-id", ClaudeOutput(output="hello"))

        outputs_file = tmp_path / "sessions" / "test-id" / "outputs.jsonl"
        assert outputs_file.exists()
        content = outputs_file.read_text()
        assert "hello" in content


class TestFileStorageAddTransition:
    """Tests for FileStorage.add_transition."""

    def test_add_transition_appends_to_jsonl(self, tmp_path):
        """Test add_transition appends to transitions.jsonl."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        storage.add_transition("test-id", TaskTransition(task_text="task"))

        trans_file = tmp_path / "sessions" / "test-id" / "transitions.jsonl"
        assert trans_file.exists()


class TestFileStorageAddCommit:
    """Tests for FileStorage.add_commit."""

    def test_add_commit_appends_to_jsonl(self, tmp_path):
        """Test add_commit appends to commits.jsonl."""
        storage = FileStorage(tmp_path / "sessions")
        meta = SessionMetadata(session_id="test-id")
        storage.create_session(meta)
        storage.add_commit("test-id", GitCommitRecord(message="commit"))

        commits_file = tmp_path / "sessions" / "test-id" / "commits.jsonl"
        assert commits_file.exists()


class TestFileStorageListSessions:
    """Tests for FileStorage.list_sessions."""

    def test_list_sessions_empty(self, tmp_path):
        """Test list_sessions returns empty list when no sessions."""
        storage = FileStorage(tmp_path / "sessions")
        assert storage.list_sessions() == []

    def test_list_sessions_returns_all(self, tmp_path):
        """Test list_sessions returns all sessions."""
        storage = FileStorage(tmp_path / "sessions")
        storage.create_session(SessionMetadata(session_id="s1"))
        storage.create_session(SessionMetadata(session_id="s2"))
        result = storage.list_sessions()
        assert len(result) == 2

    def test_list_sessions_sorted_newest_first(self, tmp_path):
        """Test list_sessions returns newest first."""
        storage = FileStorage(tmp_path / "sessions")
        storage.create_session(
            SessionMetadata(session_id="old", started_at="2024-01-01T00:00:00")
        )
        storage.create_session(
            SessionMetadata(session_id="new", started_at="2024-01-02T00:00:00")
        )
        result = storage.list_sessions()
        assert result[0].session_id == "new"

    def test_list_sessions_with_limit(self, tmp_path):
        """Test list_sessions with limit."""
        storage = FileStorage(tmp_path / "sessions")
        for i in range(5):
            storage.create_session(SessionMetadata(session_id=f"s{i}"))
        result = storage.list_sessions(limit=3)
        assert len(result) == 3

    def test_list_sessions_with_offset(self, tmp_path):
        """Test list_sessions with offset."""
        storage = FileStorage(tmp_path / "sessions")
        storage.create_session(
            SessionMetadata(session_id="s0", started_at="2024-01-01T00:00:00")
        )
        storage.create_session(
            SessionMetadata(session_id="s1", started_at="2024-01-02T00:00:00")
        )
        storage.create_session(
            SessionMetadata(session_id="s2", started_at="2024-01-03T00:00:00")
        )
        result = storage.list_sessions(offset=1)
        assert len(result) == 2

    def test_list_sessions_ignores_non_directories(self, tmp_path):
        """Test list_sessions ignores non-directory entries."""
        storage = FileStorage(tmp_path / "sessions")
        storage.create_session(SessionMetadata(session_id="valid"))
        # Create a file (not a directory)
        (tmp_path / "sessions" / "not-a-session.txt").write_text("test")
        result = storage.list_sessions()
        assert len(result) == 1


class TestFileStorageDeleteSession:
    """Tests for FileStorage.delete_session."""

    def test_delete_session_removes(self, tmp_path):
        """Test delete_session removes the session directory."""
        storage = FileStorage(tmp_path / "sessions")
        storage.create_session(SessionMetadata(session_id="test-id"))
        storage.add_event("test-id", SessionEvent())
        result = storage.delete_session("test-id")
        assert result is True
        assert not (tmp_path / "sessions" / "test-id").exists()

    def test_delete_session_returns_false_if_not_found(self, tmp_path):
        """Test delete_session returns False if not found."""
        storage = FileStorage(tmp_path / "sessions")
        result = storage.delete_session("nonexistent")
        assert result is False


class TestFileStorageDirectoryPaths:
    """Tests for FileStorage directory path methods."""

    def test_session_dir(self, tmp_path):
        """Test _session_dir returns correct path."""
        storage = FileStorage(tmp_path / "sessions")
        path = storage._session_dir("test-id")
        assert path == tmp_path / "sessions" / "test-id"

    def test_events_file(self, tmp_path):
        """Test _events_file returns correct path."""
        storage = FileStorage(tmp_path / "sessions")
        path = storage._events_file("test-id")
        assert path.name == "events.jsonl"

    def test_outputs_file(self, tmp_path):
        """Test _outputs_file returns correct path."""
        storage = FileStorage(tmp_path / "sessions")
        path = storage._outputs_file("test-id")
        assert path.name == "outputs.jsonl"


# =============================================================================
# Module Export Tests
# =============================================================================


class TestModuleExports:
    """Tests for module exports."""

    def test_session_storage_exported(self):
        """Test SessionStorage is exported."""
        from zoyd.session import SessionStorage

        assert SessionStorage is not None

    def test_in_memory_storage_exported(self):
        """Test InMemoryStorage is exported."""
        from zoyd.session import InMemoryStorage

        assert InMemoryStorage is not None

    def test_file_storage_exported(self):
        """Test FileStorage is exported."""
        from zoyd.session import FileStorage

        assert FileStorage is not None

    def test_to_json_exported(self):
        """Test to_json is exported."""
        from zoyd.session import to_json

        assert to_json is not None

    def test_from_json_exported(self):
        """Test from_json is exported."""
        from zoyd.session import from_json

        assert from_json is not None

    def test_append_jsonl_exported(self):
        """Test append_jsonl is exported."""
        from zoyd.session import append_jsonl

        assert append_jsonl is not None

    def test_read_jsonl_exported(self):
        """Test read_jsonl is exported."""
        from zoyd.session import read_jsonl

        assert read_jsonl is not None

    def test_redis_storage_exported(self):
        """Test RedisStorage is exported."""
        from zoyd.session import RedisStorage

        assert RedisStorage is not None

    def test_create_storage_exported(self):
        """Test create_storage is exported."""
        from zoyd.session import create_storage

        assert create_storage is not None


# =============================================================================
# RedisStorage Tests
# =============================================================================


# Pytest fixture to skip Redis tests if Redis is not available
@pytest.fixture
def redis_storage():
    """Create a RedisStorage instance for testing.

    Skips tests if Redis is not available or the redis package is not installed.
    Uses a unique key prefix to isolate tests and cleans up after tests.

    Reads Redis password from zoyd.toml configuration.
    """
    # Skip if redis package is not installed
    try:
        import redis
    except ImportError:
        pytest.skip("redis package not installed")

    # Load Redis config from zoyd.toml
    config = load_config()
    host = config.redis_host
    port = config.redis_port
    password = config.redis_password
    test_prefix = f"zoyd:test:{pytest.importorskip('uuid').uuid4().hex[:8]}:"

    try:
        client = redis.Redis(
            host=host, port=port, password=password, decode_responses=True
        )
        client.ping()
    except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError):
        pytest.skip(f"Redis server not available at {host}:{port}")

    # Create storage with test prefix
    storage = RedisStorage(
        host=host, port=port, password=password, key_prefix=test_prefix
    )

    yield storage

    # Cleanup: delete all keys with our test prefix
    keys = client.keys(f"{test_prefix}*")
    if keys:
        client.delete(*keys)


class TestRedisStorageCreateAndGetSession:
    """Tests for RedisStorage.create_session and get_session."""

    def test_redis_create_session_returns_id(self, redis_storage):
        """Test create_session returns session ID."""
        meta = SessionMetadata(session_id="test-create-id")
        result = redis_storage.create_session(meta)
        assert result == "test-create-id"

    def test_redis_create_session_stores_in_redis(self, redis_storage):
        """Test create_session stores session in Redis."""
        meta = SessionMetadata(session_id="test-store-id", prd_path="PRD.md")
        redis_storage.create_session(meta)
        session = redis_storage.get_session("test-store-id")
        assert session is not None
        assert session.metadata.prd_path == "PRD.md"

    def test_redis_get_session_returns_full_session(self, redis_storage):
        """Test get_session returns full session with all data."""
        meta = SessionMetadata(session_id="test-full-id", prd_path="PRD.md")
        redis_storage.create_session(meta)
        redis_storage.add_event("test-full-id", SessionEvent(event_type="TEST"))
        redis_storage.add_output("test-full-id", ClaudeOutput(output="hello"))
        redis_storage.add_transition("test-full-id", TaskTransition(task_text="task"))
        redis_storage.add_commit("test-full-id", GitCommitRecord(message="commit"))

        session = redis_storage.get_session("test-full-id")
        assert session.metadata.prd_path == "PRD.md"
        assert len(session.events) == 1
        assert len(session.outputs) == 1
        assert len(session.transitions) == 1
        assert len(session.commits) == 1

    def test_redis_get_session_returns_none_if_not_found(self, redis_storage):
        """Test get_session returns None for unknown ID."""
        assert redis_storage.get_session("nonexistent-id") is None

    def test_redis_get_metadata_returns_metadata(self, redis_storage):
        """Test get_metadata returns session metadata."""
        meta = SessionMetadata(session_id="test-meta-id", prd_path="PRD.md")
        redis_storage.create_session(meta)
        result = redis_storage.get_metadata("test-meta-id")
        assert result.prd_path == "PRD.md"

    def test_redis_end_session_sets_ended_at(self, redis_storage):
        """Test end_session sets ended_at timestamp."""
        meta = SessionMetadata(session_id="test-end-id")
        redis_storage.create_session(meta)
        redis_storage.end_session("test-end-id", "2024-01-01T01:00:00")
        session = redis_storage.get_session("test-end-id")
        assert session.metadata.ended_at == "2024-01-01T01:00:00"


class TestRedisStorageAddEventsAndOutputs:
    """Tests for RedisStorage.add_event, add_output, add_transition, add_commit."""

    def test_redis_add_event_appends(self, redis_storage):
        """Test add_event appends to events list."""
        meta = SessionMetadata(session_id="test-event-id")
        redis_storage.create_session(meta)
        redis_storage.add_event("test-event-id", SessionEvent(event_type="E1"))
        redis_storage.add_event("test-event-id", SessionEvent(event_type="E2"))

        session = redis_storage.get_session("test-event-id")
        assert len(session.events) == 2
        assert session.events[0].event_type == "E1"
        assert session.events[1].event_type == "E2"

    def test_redis_add_output_appends(self, redis_storage):
        """Test add_output appends to outputs list."""
        meta = SessionMetadata(session_id="test-output-id")
        redis_storage.create_session(meta)
        redis_storage.add_output("test-output-id", ClaudeOutput(output="out1"))
        redis_storage.add_output("test-output-id", ClaudeOutput(output="out2"))

        session = redis_storage.get_session("test-output-id")
        assert len(session.outputs) == 2
        assert session.outputs[0].output == "out1"
        assert session.outputs[1].output == "out2"

    def test_redis_add_transition_appends(self, redis_storage):
        """Test add_transition appends to transitions list."""
        meta = SessionMetadata(session_id="test-trans-id")
        redis_storage.create_session(meta)
        redis_storage.add_transition("test-trans-id", TaskTransition(task_text="task1"))
        redis_storage.add_transition("test-trans-id", TaskTransition(task_text="task2"))

        session = redis_storage.get_session("test-trans-id")
        assert len(session.transitions) == 2
        assert session.transitions[0].task_text == "task1"

    def test_redis_add_commit_appends(self, redis_storage):
        """Test add_commit appends to commits list."""
        meta = SessionMetadata(session_id="test-commit-id")
        redis_storage.create_session(meta)
        redis_storage.add_commit("test-commit-id", GitCommitRecord(message="commit1"))
        redis_storage.add_commit("test-commit-id", GitCommitRecord(message="commit2"))

        session = redis_storage.get_session("test-commit-id")
        assert len(session.commits) == 2
        assert session.commits[0].message == "commit1"

    def test_redis_add_event_to_nonexistent_session_does_nothing(self, redis_storage):
        """Test add_event on nonexistent session does nothing."""
        # Should not raise
        redis_storage.add_event("nonexistent", SessionEvent(event_type="TEST"))


class TestRedisStorageListSessionsPagination:
    """Tests for RedisStorage.list_sessions with pagination."""

    def test_redis_list_sessions_empty(self, redis_storage):
        """Test list_sessions returns empty list when no sessions."""
        assert redis_storage.list_sessions() == []

    def test_redis_list_sessions_returns_all(self, redis_storage):
        """Test list_sessions returns all sessions."""
        redis_storage.create_session(SessionMetadata(session_id="list-s1"))
        redis_storage.create_session(SessionMetadata(session_id="list-s2"))
        result = redis_storage.list_sessions()
        assert len(result) == 2

    def test_redis_list_sessions_sorted_newest_first(self, redis_storage):
        """Test list_sessions returns newest first."""
        redis_storage.create_session(
            SessionMetadata(session_id="list-old", started_at="2024-01-01T00:00:00")
        )
        redis_storage.create_session(
            SessionMetadata(session_id="list-new", started_at="2024-01-02T00:00:00")
        )
        result = redis_storage.list_sessions()
        assert result[0].session_id == "list-new"
        assert result[1].session_id == "list-old"

    def test_redis_list_sessions_with_limit(self, redis_storage):
        """Test list_sessions with limit."""
        for i in range(5):
            redis_storage.create_session(
                SessionMetadata(
                    session_id=f"limit-s{i}",
                    started_at=f"2024-01-0{i+1}T00:00:00",
                )
            )
        result = redis_storage.list_sessions(limit=3)
        assert len(result) == 3

    def test_redis_list_sessions_with_offset(self, redis_storage):
        """Test list_sessions with offset."""
        redis_storage.create_session(
            SessionMetadata(session_id="offset-s0", started_at="2024-01-01T00:00:00")
        )
        redis_storage.create_session(
            SessionMetadata(session_id="offset-s1", started_at="2024-01-02T00:00:00")
        )
        redis_storage.create_session(
            SessionMetadata(session_id="offset-s2", started_at="2024-01-03T00:00:00")
        )
        result = redis_storage.list_sessions(offset=1)
        assert len(result) == 2
        assert result[0].session_id == "offset-s1"

    def test_redis_list_sessions_with_limit_and_offset(self, redis_storage):
        """Test list_sessions with both limit and offset."""
        for i in range(5):
            redis_storage.create_session(
                SessionMetadata(
                    session_id=f"both-s{i}",
                    started_at=f"2024-01-0{i+1}T00:00:00",
                )
            )
        result = redis_storage.list_sessions(limit=2, offset=1)
        assert len(result) == 2
        # Should skip the newest (s4) and get s3, s2
        assert result[0].session_id == "both-s3"
        assert result[1].session_id == "both-s2"


class TestRedisStorageDeleteSession:
    """Tests for RedisStorage.delete_session."""

    def test_redis_delete_session_removes(self, redis_storage):
        """Test delete_session removes the session."""
        redis_storage.create_session(SessionMetadata(session_id="delete-test-id"))
        redis_storage.add_event("delete-test-id", SessionEvent(event_type="TEST"))
        result = redis_storage.delete_session("delete-test-id")
        assert result is True
        assert redis_storage.get_session("delete-test-id") is None

    def test_redis_delete_session_returns_false_if_not_found(self, redis_storage):
        """Test delete_session returns False if not found."""
        result = redis_storage.delete_session("nonexistent")
        assert result is False

    def test_redis_delete_session_removes_from_index(self, redis_storage):
        """Test delete_session removes session from index."""
        redis_storage.create_session(SessionMetadata(session_id="idx-delete-id"))
        redis_storage.delete_session("idx-delete-id")
        result = redis_storage.list_sessions()
        ids = [m.session_id for m in result]
        assert "idx-delete-id" not in ids


class TestRedisStorageConnectionErrorHandling:
    """Tests for RedisStorage connection error handling."""

    def test_redis_connection_error_on_bad_host(self):
        """Test RedisStorage raises connection error on bad host."""
        # Skip if redis package is not installed
        redis_pkg = pytest.importorskip("redis")

        storage = RedisStorage(host="nonexistent-host-12345", port=6379)
        with pytest.raises((redis_pkg.ConnectionError, redis_pkg.TimeoutError, OSError)):
            # Accessing client property triggers connection
            storage.create_session(SessionMetadata(session_id="test"))

    def test_redis_key_prefix_isolation(self):
        """Test that different key prefixes isolate data."""
        # Skip if redis package is not installed
        try:
            import redis
        except ImportError:
            pytest.skip("redis package not installed")

        # Load Redis config from zoyd.toml
        config = load_config()
        host = config.redis_host
        port = config.redis_port
        password = config.redis_password
        prefix1 = f"zoyd:test:prefix1:{pytest.importorskip('uuid').uuid4().hex[:8]}:"
        prefix2 = f"zoyd:test:prefix2:{pytest.importorskip('uuid').uuid4().hex[:8]}:"

        try:
            client = redis.Redis(
                host=host, port=port, password=password, decode_responses=True
            )
            client.ping()
        except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError):
            pytest.skip(f"Redis server not available at {host}:{port}")

        try:
            storage1 = RedisStorage(
                host=host, port=port, password=password, key_prefix=prefix1
            )
            storage2 = RedisStorage(
                host=host, port=port, password=password, key_prefix=prefix2
            )

            storage1.create_session(SessionMetadata(session_id="shared-id"))
            storage2.create_session(SessionMetadata(session_id="shared-id"))

            # Each should see only its own session
            assert storage1.get_session("shared-id") is not None
            assert storage2.get_session("shared-id") is not None

            # Deleting from one shouldn't affect the other
            storage1.delete_session("shared-id")
            assert storage1.get_session("shared-id") is None
            assert storage2.get_session("shared-id") is not None
        finally:
            # Cleanup
            keys1 = client.keys(f"{prefix1}*")
            keys2 = client.keys(f"{prefix2}*")
            if keys1:
                client.delete(*keys1)
            if keys2:
                client.delete(*keys2)

    def test_redis_update_statistics(self):
        """Test update_statistics updates session statistics."""
        # Skip if redis package is not installed
        try:
            import redis
        except ImportError:
            pytest.skip("redis package not installed")

        # Load Redis config from zoyd.toml
        config = load_config()
        host = config.redis_host
        port = config.redis_port
        password = config.redis_password
        test_prefix = f"zoyd:test:stats:{pytest.importorskip('uuid').uuid4().hex[:8]}:"

        try:
            client = redis.Redis(
                host=host, port=port, password=password, decode_responses=True
            )
            client.ping()
        except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError):
            pytest.skip(f"Redis server not available at {host}:{port}")

        try:
            storage = RedisStorage(
                host=host, port=port, password=password, key_prefix=test_prefix
            )
            meta = SessionMetadata(session_id="stats-test-id")
            storage.create_session(meta)

            new_stats = SessionStatistics(
                total_iterations=10,
                successful_iterations=8,
                failed_iterations=2,
                exit_reason="complete",
            )
            storage.update_statistics("stats-test-id", new_stats)

            session = storage.get_session("stats-test-id")
            assert session.statistics.total_iterations == 10
            assert session.statistics.successful_iterations == 8
            assert session.statistics.exit_reason == "complete"
        finally:
            # Cleanup
            keys = client.keys(f"{test_prefix}*")
            if keys:
                client.delete(*keys)


class TestCreateStorageFactory:
    """Tests for create_storage factory function."""

    def test_create_storage_defaults_to_file(self, tmp_path):
        """Test create_storage defaults to FileStorage."""
        storage = create_storage(sessions_dir=str(tmp_path / "sessions"))
        assert isinstance(storage, FileStorage)

    def test_create_storage_with_file_backend(self, tmp_path):
        """Test create_storage with explicit file backend."""
        storage = create_storage(
            backend="file", sessions_dir=str(tmp_path / "sessions")
        )
        assert isinstance(storage, FileStorage)

    def test_create_storage_with_redis_backend(self):
        """Test create_storage with redis backend."""
        # This should create a RedisStorage even if Redis isn't available
        storage = create_storage(backend="redis", redis_host="localhost")
        assert isinstance(storage, RedisStorage)

    def test_create_storage_unknown_backend_raises(self):
        """Test create_storage raises ValueError for unknown backend."""
        with pytest.raises(ValueError, match="Unknown storage backend"):
            create_storage(backend="unknown")

    def test_create_storage_passes_redis_params(self):
        """Test create_storage passes Redis parameters correctly."""
        storage = create_storage(
            backend="redis",
            redis_host="custom-host",
            redis_port=6380,
            redis_db=2,
            redis_password="secret",
        )
        assert isinstance(storage, RedisStorage)
        assert storage.host == "custom-host"
        assert storage.port == 6380
        assert storage.db == 2
        assert storage.password == "secret"

    def test_create_storage_redis_import_error_message(self):
        """Test create_storage raises helpful ImportError when redis not installed."""
        import builtins
        import sys

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "redis":
                raise ImportError("No module named 'redis'")
            return original_import(name, *args, **kwargs)

        # Temporarily remove redis from sys.modules if present
        redis_module = sys.modules.pop("redis", None)
        try:
            builtins.__import__ = mock_import
            with pytest.raises(ImportError, match="pip install 'zoyd\\[redis\\]'"):
                create_storage(backend="redis")
        finally:
            builtins.__import__ = original_import
            if redis_module is not None:
                sys.modules["redis"] = redis_module
