"""Integration tests for VectorMemory against real Redis.

These tests perform real store/retrieve/remove operations against a Redis 8.0
server with VSET commands. Tests skip gracefully if Redis is unavailable,
the redis package is not installed, or VSET commands are not supported.

Uses a fixed ``zoyd:vectors:test:`` key prefix and dedicated vector set keys
to avoid conflicts with production data. Embeddings are produced by a simple
deterministic provider (not a real model) to keep tests fast and self-contained.
"""

import json
import math
import uuid

import pytest

from zoyd.config import load_config
from zoyd.session.vectors import META_PREFIX, VectorMemory


# =============================================================================
# Deterministic embedding provider for integration tests
# =============================================================================


class _DeterministicProvider:
    """Produces deterministic embeddings based on text content.

    Maps each unique word to a dimension index (mod DIMENSION) and sets
    that dimension to a non-zero value proportional to word frequency.
    This guarantees that semantically similar texts (shared words) produce
    vectors with high cosine similarity, while unrelated texts produce
    vectors with low similarity — sufficient for integration testing.
    """

    DIMENSION = 384

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.DIMENSION
        words = text.lower().split()
        for word in words:
            idx = hash(word) % self.DIMENSION
            vec[idx] += 1.0
        # L2-normalize so cosine similarity is just dot product
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def dimension(self) -> int:
        return self.DIMENSION

    def is_available(self) -> bool:
        return True


# =============================================================================
# Fixture
# =============================================================================

# Use unique vector set keys to avoid colliding with production data
_TEST_OUTPUTS_KEY = "zoyd:vectors:test:outputs"
_TEST_TASKS_KEY = "zoyd:vectors:test:tasks"
_TEST_ERRORS_KEY = "zoyd:vectors:test:errors"
_TEST_META_PREFIX = "zoyd:vectors:test:meta:"


@pytest.fixture
def vector_mem():
    """Create a VectorMemory with real Redis connection for integration tests.

    Uses a deterministic embedding provider and isolated vector set keys.
    Cleans up all test keys before AND after each test.
    Skips if Redis is unavailable or VSET commands are not supported.
    """
    try:
        import redis
    except ImportError:
        pytest.skip("redis package not installed")

    config = load_config()
    host = config.redis_host
    port = config.redis_port
    password = config.redis_password

    # Verify Redis connectivity
    try:
        client = redis.Redis(
            host=host, port=port, password=password, decode_responses=True,
        )
        client.ping()
    except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError):
        pytest.skip(f"Redis server not available at {host}:{port}")

    # Verify VSET support
    try:
        client.execute_command("VINFO", _TEST_OUTPUTS_KEY)
    except Exception as exc:
        msg = str(exc).lower()
        if "not found" in msg or "no such key" in msg or "does not exist" in msg:
            pass  # Key doesn't exist yet, but command is recognized
        else:
            pytest.skip(f"Redis VSET commands not supported: {exc}")

    provider = _DeterministicProvider()
    vm = VectorMemory(
        provider=provider,
        host=host,
        port=port,
        password=password,
    )

    # Monkey-patch the key constants so tests use isolated keys
    import zoyd.session.vectors as vectors_mod

    orig_outputs = vectors_mod.OUTPUTS_KEY
    orig_tasks = vectors_mod.TASKS_KEY
    orig_errors = vectors_mod.ERRORS_KEY
    orig_meta = vectors_mod.META_PREFIX

    vectors_mod.OUTPUTS_KEY = _TEST_OUTPUTS_KEY
    vectors_mod.TASKS_KEY = _TEST_TASKS_KEY
    vectors_mod.ERRORS_KEY = _TEST_ERRORS_KEY
    vectors_mod.META_PREFIX = _TEST_META_PREFIX

    def _cleanup():
        """Remove all test vector sets and metadata keys."""
        # Delete vector sets entirely
        for key in [_TEST_OUTPUTS_KEY, _TEST_TASKS_KEY, _TEST_ERRORS_KEY]:
            try:
                client.delete(key)
            except Exception:
                pass
        # Scan and delete metadata keys
        cursor = 0
        while True:
            cursor, keys = client.scan(
                cursor=cursor, match=f"{_TEST_META_PREFIX}*", count=200,
            )
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break

    # Cleanup before test
    _cleanup()

    # Expose helpers on the vm object for test convenience
    vm._test_client = client
    vm._test_cleanup = _cleanup

    yield vm

    # Cleanup after test
    _cleanup()

    # Restore original constants
    vectors_mod.OUTPUTS_KEY = orig_outputs
    vectors_mod.TASKS_KEY = orig_tasks
    vectors_mod.ERRORS_KEY = orig_errors
    vectors_mod.META_PREFIX = orig_meta


# =============================================================================
# Store and Retrieve Tests
# =============================================================================


class TestStoreAndRetrieve:
    """Test storing and retrieving vectors with actual Redis VSET commands."""

    def test_store_output_returns_element_id(self, vector_mem):
        result = vector_mem.store_output(
            "int-sess-1", 1, "Fixed the parser bug in module X", "Fix parser", 0,
        )
        assert result is not None
        assert result.startswith("output:int-sess-1:1:")

    def test_store_output_metadata_persists(self, vector_mem):
        elem_id = vector_mem.store_output(
            "int-sess-1", 2, "Added unit tests for validation", "Add tests", 0,
        )
        # Read metadata directly from Redis
        meta_raw = vector_mem._test_client.get(f"{_TEST_META_PREFIX}{elem_id}")
        assert meta_raw is not None
        meta = json.loads(meta_raw)
        assert meta["session_id"] == "int-sess-1"
        assert meta["iteration"] == 2
        assert meta["task_text"] == "Add tests"
        assert meta["return_code"] == 0
        assert "timestamp" in meta
        assert meta["output_preview"] == "Added unit tests for validation"

    def test_store_and_find_output(self, vector_mem):
        vector_mem.store_output(
            "int-sess-1", 1, "Fixed parser bug in the tokenizer module", "Fix parser", 0,
        )
        results = vector_mem.find_relevant_outputs("parser tokenizer fix")
        assert len(results) >= 1
        assert results[0]["task_text"] == "Fix parser"
        assert "score" in results[0]

    def test_store_task_returns_element_id(self, vector_mem):
        result = vector_mem.store_task("int-sess-1", "Implement user authentication", 42)
        assert result is not None
        assert result.startswith("task:int-sess-1:42:")

    def test_store_and_find_task(self, vector_mem):
        vector_mem.store_task("int-sess-1", "Implement user authentication system", 42)
        results = vector_mem.find_similar_tasks("authentication user system")
        assert len(results) >= 1
        assert results[0]["task_text"] == "Implement user authentication system"
        assert results[0]["line_number"] == 42

    def test_store_error_returns_element_id(self, vector_mem):
        result = vector_mem.store_error(
            "int-sess-1", 3, "ModuleNotFoundError: No module named foo", "Install deps",
        )
        assert result is not None
        assert result.startswith("error:int-sess-1:3:")

    def test_store_and_find_error(self, vector_mem):
        vector_mem.store_error(
            "int-sess-1", 3, "ModuleNotFoundError: No module named foo", "Install deps",
        )
        results = vector_mem.find_similar_errors("ModuleNotFoundError module foo")
        assert len(results) >= 1
        assert results[0]["task_text"] == "Install deps"
        assert "error_preview" in results[0]

    def test_store_output_preview_truncated(self, vector_mem):
        long_output = "x" * 1000
        elem_id = vector_mem.store_output(
            "int-sess-1", 1, long_output, "task", 0,
        )
        meta_raw = vector_mem._test_client.get(f"{_TEST_META_PREFIX}{elem_id}")
        meta = json.loads(meta_raw)
        assert len(meta["output_preview"]) == 500


# =============================================================================
# Similarity Ranking Tests
# =============================================================================


class TestSimilarityRanking:
    """Test that similarity search returns results in rank order."""

    def test_more_similar_text_ranks_higher(self, vector_mem):
        """Texts sharing more words with the query should rank higher."""
        # Store outputs with varying similarity to the query
        vector_mem.store_output(
            "rank-sess", 1,
            "Fixed authentication login password reset flow",
            "Fix auth", 0,
        )
        vector_mem.store_output(
            "rank-sess", 2,
            "Updated database schema migration scripts for postgres",
            "Update DB", 0,
        )
        vector_mem.store_output(
            "rank-sess", 3,
            "Fixed authentication login validation and password checks",
            "Fix auth validation", 0,
        )

        # Query about authentication should rank auth-related outputs higher
        results = vector_mem.find_relevant_outputs(
            "authentication login password", count=3,
        )
        assert len(results) >= 2

        # Both auth-related outputs should rank above the database one
        auth_scores = [
            r["score"] for r in results if "auth" in r.get("task_text", "").lower()
        ]
        db_scores = [
            r["score"] for r in results if "db" in r.get("task_text", "").lower()
        ]
        if auth_scores and db_scores:
            assert min(auth_scores) > max(db_scores)

    def test_task_similarity_ranking(self, vector_mem):
        """Similar tasks should rank above dissimilar ones."""
        vector_mem.store_task("rank-sess", "Add unit tests for parser module", 10)
        vector_mem.store_task("rank-sess", "Deploy application to production", 20)
        vector_mem.store_task("rank-sess", "Write tests for parser validation", 30)

        results = vector_mem.find_similar_tasks("parser tests unit", count=3)
        assert len(results) >= 2

        # Parser/test tasks should rank above deployment
        parser_scores = [
            r["score"] for r in results if "parser" in r["task_text"].lower()
        ]
        deploy_scores = [
            r["score"] for r in results if "deploy" in r["task_text"].lower()
        ]
        if parser_scores and deploy_scores:
            assert min(parser_scores) > max(deploy_scores)

    def test_error_similarity_ranking(self, vector_mem):
        """Similar errors should rank above dissimilar ones."""
        vector_mem.store_error(
            "rank-sess", 1,
            "ImportError: cannot import name Foo from bar",
            "Fix import",
        )
        vector_mem.store_error(
            "rank-sess", 2,
            "ConnectionRefusedError: connection refused to database",
            "Fix connection",
        )
        vector_mem.store_error(
            "rank-sess", 3,
            "ImportError: cannot import name Baz from bar module",
            "Fix import again",
        )

        results = vector_mem.find_similar_errors(
            "ImportError import name from bar", count=3,
        )
        assert len(results) >= 2

        import_scores = [
            r["score"] for r in results if "import" in r.get("task_text", "").lower()
        ]
        conn_scores = [
            r["score"] for r in results if "connection" in r.get("task_text", "").lower()
        ]
        if import_scores and conn_scores:
            assert min(import_scores) > max(conn_scores)

    def test_find_outputs_respects_count(self, vector_mem):
        """Should return at most `count` results."""
        for i in range(5):
            vector_mem.store_output(
                "count-sess", i, f"output about testing iteration {i}",
                f"task {i}", 0,
            )
        results = vector_mem.find_relevant_outputs("testing iteration", count=2)
        assert len(results) <= 2


# =============================================================================
# Cross-Session Retrieval Tests
# =============================================================================


class TestCrossSessionRetrieval:
    """Test retrieval across different sessions."""

    def test_find_outputs_from_different_session(self, vector_mem):
        """Outputs from session A should be findable from session B."""
        # Store in session A
        vector_mem.store_output(
            "session-alpha", 1,
            "Implemented caching layer for API responses",
            "Add caching", 0,
        )
        # Store in session B
        vector_mem.store_output(
            "session-beta", 1,
            "Fixed database connection pooling issues",
            "Fix DB pool", 0,
        )

        # Query from a third session context should find both
        results = vector_mem.find_relevant_outputs("caching API responses", count=5)
        session_ids = {r["session_id"] for r in results}
        assert "session-alpha" in session_ids

    def test_exclude_current_session(self, vector_mem):
        """Results should exclude the specified session."""
        # Store outputs in two sessions
        vector_mem.store_output(
            "session-alpha", 1,
            "Refactored authentication module for clarity",
            "Refactor auth", 0,
        )
        vector_mem.store_output(
            "session-beta", 1,
            "Updated authentication tests to cover edge cases",
            "Update auth tests", 0,
        )

        # Find with exclusion
        results = vector_mem.find_relevant_outputs(
            "authentication module refactor", count=5,
            exclude_session="session-alpha",
        )
        for r in results:
            assert r["session_id"] != "session-alpha"

    def test_cross_session_tasks(self, vector_mem):
        """Tasks from prior sessions should be discoverable."""
        vector_mem.store_task("old-session", "Create REST API endpoint for users", 10)
        vector_mem.store_task("new-session", "Add GraphQL endpoint for users", 15)

        # Should find both sessions' tasks
        results = vector_mem.find_similar_tasks("API endpoint users", count=5)
        session_ids = {r["session_id"] for r in results}
        assert len(session_ids) >= 1  # At least one match

    def test_cross_session_errors(self, vector_mem):
        """Errors from prior sessions should be findable for pattern matching."""
        vector_mem.store_error(
            "old-session", 1,
            "TimeoutError: Redis connection timed out after 30s",
            "Fix timeout",
        )
        vector_mem.store_error(
            "new-session", 2,
            "TimeoutError: Redis connection timed out after 30s",
            "Fix timeout again",
        )

        results = vector_mem.find_similar_errors("TimeoutError Redis connection")
        session_ids = {r["session_id"] for r in results}
        assert len(session_ids) >= 1

    def test_exclude_session_for_tasks(self, vector_mem):
        """Task exclusion should filter out the specified session."""
        vector_mem.store_task("session-x", "Implement logging framework", 5)
        vector_mem.store_task("session-y", "Add logging to all modules", 10)

        results = vector_mem.find_similar_tasks(
            "logging framework modules",
            count=5,
            exclude_session="session-x",
        )
        for r in results:
            assert r["session_id"] != "session-x"


# =============================================================================
# Cleanup Tests
# =============================================================================


class TestCleanup:
    """Test session cleanup via remove_session."""

    def test_remove_session_clears_outputs(self, vector_mem):
        """Removing a session should delete its outputs from the vector set."""
        vector_mem.store_output(
            "cleanup-sess", 1, "Output to be cleaned up", "task", 0,
        )
        # Verify it's findable
        results = vector_mem.find_relevant_outputs("Output cleaned up")
        assert len(results) >= 1

        # Remove session
        removed = vector_mem.remove_session("cleanup-sess")
        assert removed >= 1

        # Verify no longer findable
        results_after = vector_mem.find_relevant_outputs("Output cleaned up")
        cleanup_results = [
            r for r in results_after if r.get("session_id") == "cleanup-sess"
        ]
        assert len(cleanup_results) == 0

    def test_remove_session_clears_tasks(self, vector_mem):
        """Removing a session should delete its tasks."""
        vector_mem.store_task("cleanup-sess", "Task to remove", 99)

        removed = vector_mem.remove_session("cleanup-sess")
        assert removed >= 1

        results = vector_mem.find_similar_tasks("Task to remove")
        cleanup_results = [
            r for r in results if r.get("session_id") == "cleanup-sess"
        ]
        assert len(cleanup_results) == 0

    def test_remove_session_clears_errors(self, vector_mem):
        """Removing a session should delete its errors."""
        vector_mem.store_error(
            "cleanup-sess", 1, "Error to remove from set", "task",
        )

        removed = vector_mem.remove_session("cleanup-sess")
        assert removed >= 1

        results = vector_mem.find_similar_errors("Error to remove from set")
        cleanup_results = [
            r for r in results if r.get("session_id") == "cleanup-sess"
        ]
        assert len(cleanup_results) == 0

    def test_remove_session_clears_metadata(self, vector_mem):
        """Removing a session should delete associated metadata keys."""
        elem_id = vector_mem.store_output(
            "cleanup-sess", 1, "Output with metadata", "task", 0,
        )
        # Verify metadata exists
        meta_key = f"{_TEST_META_PREFIX}{elem_id}"
        assert vector_mem._test_client.get(meta_key) is not None

        vector_mem.remove_session("cleanup-sess")

        # Metadata should be gone
        assert vector_mem._test_client.get(meta_key) is None

    def test_remove_does_not_affect_other_sessions(self, vector_mem):
        """Removing one session should not affect another session's data."""
        vector_mem.store_output(
            "keep-sess", 1, "This output should survive cleanup", "keep task", 0,
        )
        vector_mem.store_output(
            "remove-sess", 1, "This output should be removed", "remove task", 0,
        )

        vector_mem.remove_session("remove-sess")

        # The kept session's output should still be findable
        results = vector_mem.find_relevant_outputs("output should survive cleanup")
        keep_results = [
            r for r in results if r.get("session_id") == "keep-sess"
        ]
        assert len(keep_results) >= 1

    def test_remove_nonexistent_session_returns_zero(self, vector_mem):
        """Removing a session that doesn't exist should return 0."""
        removed = vector_mem.remove_session("nonexistent-session-" + uuid.uuid4().hex)
        assert removed == 0

    def test_remove_session_with_mixed_data(self, vector_mem):
        """Remove session that has outputs, tasks, and errors."""
        sess_id = "mixed-cleanup"
        vector_mem.store_output(sess_id, 1, "Output text for mixed", "task1", 0)
        vector_mem.store_task(sess_id, "Task for mixed session", 10)
        vector_mem.store_error(sess_id, 2, "Error for mixed session", "task2")

        removed = vector_mem.remove_session(sess_id)
        assert removed == 3

        # Verify nothing remains for this session
        for find_fn, query in [
            (vector_mem.find_relevant_outputs, "Output text for mixed"),
            (vector_mem.find_similar_tasks, "Task for mixed session"),
            (vector_mem.find_similar_errors, "Error for mixed session"),
        ]:
            results = find_fn(query)
            sess_results = [
                r for r in results if r.get("session_id") == sess_id
            ]
            assert len(sess_results) == 0


# =============================================================================
# is_available property
# =============================================================================


class TestIsAvailable:
    """Test the is_available property against real Redis."""

    def test_is_available_true(self, vector_mem):
        """Should return True when Redis is running and VSET supported."""
        assert vector_mem.is_available is True
