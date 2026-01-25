"""Integration tests for Redis CRUD operations using zebedo: key prefix.

These tests perform real CRUD operations against Redis to verify the storage
backend works correctly. Uses a fixed `zebedo:` key prefix for predictable
and inspectable data.
"""

import json
import time
from datetime import datetime

import pytest

from zoyd.config import load_config
from zoyd.session.models import (
    ClaudeOutput,
    GitCommitRecord,
    SessionEvent,
    SessionMetadata,
    SessionStatistics,
    TaskTransition,
)
from zoyd.session.storage import RedisStorage


# =============================================================================
# Fixture
# =============================================================================


@pytest.fixture
def zebedo_storage():
    """Create a RedisStorage instance with zebedo: key prefix for testing.

    Uses fixed `zebedo:` prefix (not random UUID) so data is predictable
    and inspectable. Cleans up zebedo:* keys before AND after tests to
    handle interrupted runs.

    Skips tests if Redis is not available or the redis package is not installed.
    Reads Redis config (host, port, password) from zoyd.toml via load_config().
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

    # Fixed prefix for predictable, inspectable data
    test_prefix = "zebedo:"

    try:
        client = redis.Redis(
            host=host, port=port, password=password, decode_responses=True
        )
        client.ping()
    except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError):
        pytest.skip(f"Redis server not available at {host}:{port}")

    # Cleanup BEFORE test to handle interrupted runs
    keys = client.keys(f"{test_prefix}*")
    if keys:
        client.delete(*keys)

    # Create storage with zebedo: prefix
    storage = RedisStorage(
        host=host, port=port, password=password, key_prefix=test_prefix
    )

    # Store the raw client for direct Redis verification
    storage._raw_client = client

    yield storage

    # Cleanup AFTER test
    keys = client.keys(f"{test_prefix}*")
    if keys:
        client.delete(*keys)


# =============================================================================
# Create Operations
# =============================================================================


class TestCreateOperations:
    """Tests for creating sessions in Redis."""

    def test_create_session(self, zebedo_storage):
        """Create session, verify exists in Redis."""
        # Create a session
        meta = SessionMetadata(
            session_id="zebedo-create-test",
            prd_path="/path/to/prd.md",
            progress_path="/path/to/progress.txt",
            model="sonnet",
            max_iterations=10,
        )
        result = zebedo_storage.create_session(meta)

        # Verify via storage API
        assert result == "zebedo-create-test"

        # Verify directly in Redis
        client = zebedo_storage._raw_client
        meta_key = f"zebedo:session:zebedo-create-test:meta"
        raw_data = client.get(meta_key)
        assert raw_data is not None
        data = json.loads(raw_data)
        assert data["metadata"]["session_id"] == "zebedo-create-test"
        assert data["metadata"]["prd_path"] == "/path/to/prd.md"
        assert data["metadata"]["model"] == "sonnet"

        # Verify session is in the index
        index_key = "zebedo:sessions:index"
        members = client.zrange(index_key, 0, -1)
        assert "zebedo-create-test" in members

    def test_create_multiple_sessions(self, zebedo_storage):
        """Create several sessions, verify all stored."""
        session_ids = ["zebedo-multi-1", "zebedo-multi-2", "zebedo-multi-3"]

        # Create multiple sessions
        for sid in session_ids:
            meta = SessionMetadata(
                session_id=sid,
                prd_path=f"/path/to/{sid}/prd.md",
            )
            result = zebedo_storage.create_session(meta)
            assert result == sid

        # Verify all exist in Redis directly
        client = zebedo_storage._raw_client
        for sid in session_ids:
            meta_key = f"zebedo:session:{sid}:meta"
            raw_data = client.get(meta_key)
            assert raw_data is not None
            data = json.loads(raw_data)
            assert data["metadata"]["session_id"] == sid

        # Verify all in index
        index_key = "zebedo:sessions:index"
        members = client.zrange(index_key, 0, -1)
        for sid in session_ids:
            assert sid in members


# =============================================================================
# Read Operations
# =============================================================================


class TestReadOperations:
    """Tests for reading session data from Redis."""

    def test_read_session_metadata(self, zebedo_storage):
        """Read back session metadata."""
        # Create a session with metadata
        meta = SessionMetadata(
            session_id="zebedo-read-meta",
            prd_path="/path/to/prd.md",
            progress_path="/path/to/progress.txt",
            model="opus",
            max_iterations=20,
            max_cost=5.0,
            auto_commit=True,
            fail_fast=False,
            working_dir="/work/dir",
        )
        zebedo_storage.create_session(meta)

        # Read back via storage API
        retrieved = zebedo_storage.get_metadata("zebedo-read-meta")

        # Verify metadata matches
        assert retrieved is not None
        assert retrieved.session_id == "zebedo-read-meta"
        assert retrieved.prd_path == "/path/to/prd.md"
        assert retrieved.progress_path == "/path/to/progress.txt"
        assert retrieved.model == "opus"
        assert retrieved.max_iterations == 20
        assert retrieved.max_cost == 5.0
        assert retrieved.auto_commit is True
        assert retrieved.fail_fast is False
        assert retrieved.working_dir == "/work/dir"

    def test_read_session_with_events(self, zebedo_storage):
        """Create with events, read full session."""
        # Create session
        meta = SessionMetadata(session_id="zebedo-read-events")
        zebedo_storage.create_session(meta)

        # Add events
        event1 = SessionEvent(
            event_type="ITERATION_START",
            data={"iteration": 1},
            iteration=1,
        )
        event2 = SessionEvent(
            event_type="CLAUDE_INVOKE",
            data={"task": "Fix bug"},
            iteration=1,
        )
        event3 = SessionEvent(
            event_type="ITERATION_END",
            data={"success": True},
            iteration=1,
        )
        zebedo_storage.add_event("zebedo-read-events", event1)
        zebedo_storage.add_event("zebedo-read-events", event2)
        zebedo_storage.add_event("zebedo-read-events", event3)

        # Read full session
        session = zebedo_storage.get_session("zebedo-read-events")

        # Verify session and events
        assert session is not None
        assert session.metadata.session_id == "zebedo-read-events"
        assert len(session.events) == 3
        assert session.events[0].event_type == "ITERATION_START"
        assert session.events[1].event_type == "CLAUDE_INVOKE"
        assert session.events[2].event_type == "ITERATION_END"

        # Also verify in Redis directly
        client = zebedo_storage._raw_client
        events_key = "zebedo:session:zebedo-read-events:events"
        raw_events = client.lrange(events_key, 0, -1)
        assert len(raw_events) == 3

    def test_read_nonexistent_returns_none(self, zebedo_storage):
        """Verify None for missing session."""
        # Try to read a session that doesn't exist
        result = zebedo_storage.get_session("zebedo-nonexistent-session")
        assert result is None

        meta_result = zebedo_storage.get_metadata("zebedo-nonexistent-metadata")
        assert meta_result is None


# =============================================================================
# Update Operations
# =============================================================================


class TestUpdateOperations:
    """Tests for updating session data in Redis."""

    def test_update_statistics(self, zebedo_storage):
        """Update stats, verify persisted."""
        # Create session
        meta = SessionMetadata(session_id="zebedo-update-stats")
        zebedo_storage.create_session(meta)

        # Create and add statistics
        stats = SessionStatistics(
            total_iterations=5,
            successful_iterations=4,
            failed_iterations=1,
            tasks_completed=3,
            tasks_total=5,
            total_cost_usd=1.25,
            total_duration_seconds=120.5,
            commits_made=3,
            exit_code=0,
            exit_reason="complete",
        )
        zebedo_storage.update_statistics("zebedo-update-stats", stats)

        # Verify via storage API
        session = zebedo_storage.get_session("zebedo-update-stats")
        assert session.statistics is not None
        assert session.statistics.total_iterations == 5
        assert session.statistics.successful_iterations == 4
        assert session.statistics.failed_iterations == 1
        assert session.statistics.tasks_completed == 3
        assert session.statistics.tasks_total == 5
        assert session.statistics.total_cost_usd == 1.25
        assert session.statistics.total_duration_seconds == 120.5
        assert session.statistics.commits_made == 3
        assert session.statistics.exit_code == 0
        assert session.statistics.exit_reason == "complete"

        # Verify directly in Redis
        client = zebedo_storage._raw_client
        meta_key = "zebedo:session:zebedo-update-stats:meta"
        raw_data = client.get(meta_key)
        data = json.loads(raw_data)
        assert data["statistics"]["total_iterations"] == 5
        assert data["statistics"]["total_cost_usd"] == 1.25

    def test_end_session(self, zebedo_storage):
        """End session, verify ended_at timestamp."""
        # Create session
        meta = SessionMetadata(session_id="zebedo-end-session")
        zebedo_storage.create_session(meta)

        # Verify ended_at is None initially
        session_before = zebedo_storage.get_session("zebedo-end-session")
        assert session_before.metadata.ended_at is None

        # End the session
        zebedo_storage.end_session("zebedo-end-session")

        # Verify ended_at is set
        session_after = zebedo_storage.get_session("zebedo-end-session")
        assert session_after.metadata.ended_at is not None
        assert isinstance(session_after.metadata.ended_at, str)

        # Verify directly in Redis
        client = zebedo_storage._raw_client
        meta_key = "zebedo:session:zebedo-end-session:meta"
        raw_data = client.get(meta_key)
        data = json.loads(raw_data)
        assert data["metadata"]["ended_at"] is not None

    def test_add_events_incremental(self, zebedo_storage):
        """Add multiple events, verify stored."""
        # Create session
        meta = SessionMetadata(session_id="zebedo-incremental-events")
        zebedo_storage.create_session(meta)

        # Add events incrementally
        for i in range(1, 6):
            event = SessionEvent(
                event_type=f"EVENT_{i}",
                data={"iteration": i},
                iteration=i,
            )
            zebedo_storage.add_event("zebedo-incremental-events", event)

            # Verify count after each addition
            client = zebedo_storage._raw_client
            events_key = "zebedo:session:zebedo-incremental-events:events"
            count = client.llen(events_key)
            assert count == i

        # Verify all events in order
        session = zebedo_storage.get_session("zebedo-incremental-events")
        assert len(session.events) == 5
        for i, event in enumerate(session.events, 1):
            assert event.event_type == f"EVENT_{i}"

    def test_add_outputs_transitions_commits(self, zebedo_storage):
        """Add all record types."""
        # Create session
        meta = SessionMetadata(session_id="zebedo-all-records")
        zebedo_storage.create_session(meta)

        # Add output
        output = ClaudeOutput(
            iteration=1,
            output="Fixed the bug in parser.py",
            return_code=0,
            cost_usd=0.15,
            duration_seconds=30.5,
            task_text="Fix parser bug",
        )
        zebedo_storage.add_output("zebedo-all-records", output)

        # Add transition
        transition = TaskTransition(
            iteration=1,
            task_text="Fix parser bug",
            task_line=10,
            from_state="pending",
            to_state="complete",
        )
        zebedo_storage.add_transition("zebedo-all-records", transition)

        # Add commit
        commit = GitCommitRecord(
            iteration=1,
            commit_hash="abc1234",
            message="Fixed parser bug",
            files_changed=["parser.py"],
            task_text="Fix parser bug",
        )
        zebedo_storage.add_commit("zebedo-all-records", commit)

        # Verify all records via storage API
        session = zebedo_storage.get_session("zebedo-all-records")
        assert len(session.outputs) == 1
        assert session.outputs[0].output == "Fixed the bug in parser.py"
        assert session.outputs[0].cost_usd == 0.15

        assert len(session.transitions) == 1
        assert session.transitions[0].task_text == "Fix parser bug"
        assert session.transitions[0].from_state == "pending"
        assert session.transitions[0].to_state == "complete"

        assert len(session.commits) == 1
        assert session.commits[0].commit_hash == "abc1234"
        assert session.commits[0].message == "Fixed parser bug"

        # Verify directly in Redis
        client = zebedo_storage._raw_client

        outputs_key = "zebedo:session:zebedo-all-records:outputs"
        raw_outputs = client.lrange(outputs_key, 0, -1)
        assert len(raw_outputs) == 1

        transitions_key = "zebedo:session:zebedo-all-records:transitions"
        raw_transitions = client.lrange(transitions_key, 0, -1)
        assert len(raw_transitions) == 1

        commits_key = "zebedo:session:zebedo-all-records:commits"
        raw_commits = client.lrange(commits_key, 0, -1)
        assert len(raw_commits) == 1


# =============================================================================
# Delete Operations
# =============================================================================


class TestDeleteOperations:
    """Tests for deleting sessions from Redis."""

    def test_delete_session(self, zebedo_storage):
        """Delete session, verify gone."""
        # Create session
        meta = SessionMetadata(session_id="zebedo-delete-test")
        zebedo_storage.create_session(meta)

        # Verify it exists
        assert zebedo_storage.get_session("zebedo-delete-test") is not None

        # Delete it
        result = zebedo_storage.delete_session("zebedo-delete-test")
        assert result is True

        # Verify it's gone via storage API
        assert zebedo_storage.get_session("zebedo-delete-test") is None

        # Verify directly in Redis
        client = zebedo_storage._raw_client
        meta_key = "zebedo:session:zebedo-delete-test:meta"
        assert client.get(meta_key) is None

        # Verify removed from index
        index_key = "zebedo:sessions:index"
        members = client.zrange(index_key, 0, -1)
        assert "zebedo-delete-test" not in members

    def test_delete_removes_all_data(self, zebedo_storage):
        """Verify events/outputs also deleted."""
        # Create session with all data types
        meta = SessionMetadata(session_id="zebedo-delete-all")
        zebedo_storage.create_session(meta)

        # Add various data
        zebedo_storage.add_event(
            "zebedo-delete-all",
            SessionEvent(event_type="TEST", data={}, iteration=1),
        )
        zebedo_storage.add_output(
            "zebedo-delete-all",
            ClaudeOutput(iteration=1, output="test", return_code=0),
        )
        zebedo_storage.add_transition(
            "zebedo-delete-all",
            TaskTransition(
                iteration=1, task_text="task", task_line=1, from_state="a", to_state="b"
            ),
        )
        zebedo_storage.add_commit(
            "zebedo-delete-all",
            GitCommitRecord(iteration=1, commit_hash="abc", message="msg"),
        )

        # Verify all keys exist
        client = zebedo_storage._raw_client
        assert client.get("zebedo:session:zebedo-delete-all:meta") is not None
        assert client.llen("zebedo:session:zebedo-delete-all:events") > 0
        assert client.llen("zebedo:session:zebedo-delete-all:outputs") > 0
        assert client.llen("zebedo:session:zebedo-delete-all:transitions") > 0
        assert client.llen("zebedo:session:zebedo-delete-all:commits") > 0

        # Delete session
        zebedo_storage.delete_session("zebedo-delete-all")

        # Verify all keys are gone
        assert client.get("zebedo:session:zebedo-delete-all:meta") is None
        assert client.llen("zebedo:session:zebedo-delete-all:events") == 0
        assert client.llen("zebedo:session:zebedo-delete-all:outputs") == 0
        assert client.llen("zebedo:session:zebedo-delete-all:transitions") == 0
        assert client.llen("zebedo:session:zebedo-delete-all:commits") == 0

    def test_delete_nonexistent_returns_false(self, zebedo_storage):
        """Delete missing returns False."""
        result = zebedo_storage.delete_session("zebedo-nonexistent-delete")
        assert result is False


# =============================================================================
# List/Query Operations
# =============================================================================


class TestListQueryOperations:
    """Tests for listing and querying sessions in Redis."""

    def test_list_sessions_pagination(self, zebedo_storage):
        """Test limit/offset for pagination."""
        # Create 5 sessions with slight delays to ensure ordering
        for i in range(1, 6):
            meta = SessionMetadata(session_id=f"zebedo-page-{i}")
            zebedo_storage.create_session(meta)
            time.sleep(0.01)  # Small delay for timestamp ordering

        # Test limit
        first_two = zebedo_storage.list_sessions(limit=2)
        assert len(first_two) == 2

        # Test offset
        next_two = zebedo_storage.list_sessions(limit=2, offset=2)
        assert len(next_two) == 2

        # Verify different sessions
        first_ids = {m.session_id for m in first_two}
        next_ids = {m.session_id for m in next_two}
        assert first_ids.isdisjoint(next_ids)

        # Test getting all
        all_sessions = zebedo_storage.list_sessions(limit=10)
        assert len(all_sessions) == 5

    def test_list_sessions_sorted_by_date(self, zebedo_storage):
        """Verify newest-first ordering."""
        # Create sessions in known order with delays
        session_ids = []
        for i in range(1, 4):
            sid = f"zebedo-sort-{i}"
            meta = SessionMetadata(session_id=sid)
            zebedo_storage.create_session(meta)
            session_ids.append(sid)
            time.sleep(0.05)  # Ensure distinct timestamps

        # List sessions (should be newest first)
        sessions = zebedo_storage.list_sessions(limit=10)

        # Extract session IDs from results
        result_ids = [s.session_id for s in sessions]

        # The most recently created should be first (reverse order)
        assert result_ids[0] == "zebedo-sort-3"
        assert result_ids[1] == "zebedo-sort-2"
        assert result_ids[2] == "zebedo-sort-1"
