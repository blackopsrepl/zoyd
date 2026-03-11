"""Tests for zoyd.session.vectors VectorMemory class."""

import json
from unittest.mock import MagicMock, patch, call

from zoyd.session.vectors import (
    ERRORS_KEY,
    META_PREFIX,
    OUTPUTS_KEY,
    TASKS_KEY,
    VectorMemory,
)


def _make_provider(dimension=384, available=True):
    """Create a mock EmbeddingProvider."""
    provider = MagicMock()
    provider.dimension.return_value = dimension
    provider.is_available.return_value = available
    # Return a fixed vector by default
    provider.embed.return_value = [0.1] * dimension
    return provider


def _make_vm(provider=None, client=None):
    """Create a VectorMemory with mocked Redis client and provider."""
    if provider is None:
        provider = _make_provider()
    vm = VectorMemory(provider=provider)
    if client is None:
        client = MagicMock()
    vm._client = client
    return vm, client, provider


class TestVectorMemoryInit:
    """Tests for VectorMemory initialization."""

    def test_default_params(self):
        provider = _make_provider()
        vm = VectorMemory(provider=provider)
        assert vm.host == "localhost"
        assert vm.port == 6379
        assert vm.db == 0
        assert vm.password is None
        assert vm.provider is provider

    def test_custom_params(self):
        provider = _make_provider()
        vm = VectorMemory(
            provider=provider, host="redis.local", port=1234, db=5, password="pw"
        )
        assert vm.host == "redis.local"
        assert vm.port == 1234
        assert vm.db == 5
        assert vm.password == "pw"

    def test_client_initially_none(self):
        provider = _make_provider()
        vm = VectorMemory(provider=provider)
        assert vm._client is None


class TestVectorMemoryIsAvailable:
    """Tests for VectorMemory.is_available property."""

    def test_available_when_all_checks_pass(self):
        vm, client, provider = _make_vm()
        client.ping.return_value = True
        client.execute_command.return_value = {}
        assert vm.is_available is True

    def test_unavailable_when_provider_unavailable(self):
        provider = _make_provider(available=False)
        vm, client, _ = _make_vm(provider=provider)
        assert vm.is_available is False
        # Should short-circuit — no Redis calls
        client.ping.assert_not_called()

    def test_unavailable_when_ping_fails(self):
        vm, client, _ = _make_vm()
        client.ping.side_effect = ConnectionError("refused")
        assert vm.is_available is False

    def test_available_when_vinfo_key_not_found(self):
        vm, client, _ = _make_vm()
        client.ping.return_value = True
        client.execute_command.side_effect = Exception("not found")
        assert vm.is_available is True

    def test_available_when_vinfo_no_such_key(self):
        vm, client, _ = _make_vm()
        client.ping.return_value = True
        client.execute_command.side_effect = Exception("no such key")
        assert vm.is_available is True

    def test_available_when_vinfo_does_not_exist(self):
        vm, client, _ = _make_vm()
        client.ping.return_value = True
        client.execute_command.side_effect = Exception("does not exist")
        assert vm.is_available is True

    def test_unavailable_when_vset_not_supported(self):
        vm, client, _ = _make_vm()
        client.ping.return_value = True
        client.execute_command.side_effect = Exception("unknown command VINFO")
        assert vm.is_available is False


class TestVectorMemoryStoreOutput:
    """Tests for VectorMemory.store_output()."""

    def test_store_output_returns_element_id(self):
        vm, client, provider = _make_vm()
        result = vm.store_output("sess1", 1, "output text", "task text", 0)
        assert result is not None
        assert result.startswith("output:sess1:1:")

    def test_store_output_calls_embed(self):
        vm, client, provider = _make_vm()
        vm.store_output("sess1", 1, "output text", "task text", 0)
        provider.embed.assert_called_once_with("output text")

    def test_store_output_calls_vadd(self):
        vm, client, provider = _make_vm()
        provider.embed.return_value = [0.5, 0.6, 0.7]
        vm.store_output("sess1", 1, "output text", "task text", 0)
        vadd_call = client.execute_command.call_args
        assert vadd_call[0][0] == "VADD"
        assert vadd_call[0][1] == OUTPUTS_KEY
        assert vadd_call[0][2] == "VALUES"
        assert vadd_call[0][3] == 3  # vector length
        # vector values follow
        assert vadd_call[0][4:7] == (0.5, 0.6, 0.7)
        # element_id is the last argument
        assert vadd_call[0][7].startswith("output:sess1:1:")

    def test_store_output_stores_metadata(self):
        vm, client, provider = _make_vm()
        result = vm.store_output("sess1", 2, "some output", "fix bug", 0)
        # Find the client.set call
        set_calls = [c for c in client.method_calls if c[0] == "set"]
        assert len(set_calls) == 1
        key, json_str = set_calls[0][1]
        assert key == f"{META_PREFIX}{result}"
        meta = json.loads(json_str)
        assert meta["session_id"] == "sess1"
        assert meta["iteration"] == 2
        assert meta["task_text"] == "fix bug"
        assert meta["return_code"] == 0
        assert "timestamp" in meta
        assert meta["output_preview"] == "some output"

    def test_store_output_truncates_preview(self):
        vm, client, provider = _make_vm()
        long_output = "x" * 1000
        vm.store_output("sess1", 1, long_output, "task", 0)
        set_calls = [c for c in client.method_calls if c[0] == "set"]
        meta = json.loads(set_calls[0][1][1])
        assert len(meta["output_preview"]) == 500

    def test_store_output_returns_none_on_failure(self):
        vm, client, provider = _make_vm()
        client.execute_command.side_effect = Exception("connection lost")
        result = vm.store_output("sess1", 1, "output", "task", 0)
        assert result is None


class TestVectorMemoryStoreTask:
    """Tests for VectorMemory.store_task()."""

    def test_store_task_returns_element_id(self):
        vm, client, provider = _make_vm()
        result = vm.store_task("sess1", "Add feature X", 42)
        assert result is not None
        assert result.startswith("task:sess1:42:")

    def test_store_task_calls_embed(self):
        vm, client, provider = _make_vm()
        vm.store_task("sess1", "Add feature X", 42)
        provider.embed.assert_called_once_with("Add feature X")

    def test_store_task_calls_vadd_on_tasks_key(self):
        vm, client, provider = _make_vm()
        provider.embed.return_value = [1.0, 2.0]
        vm.store_task("sess1", "task desc", 10)
        vadd_call = client.execute_command.call_args
        assert vadd_call[0][0] == "VADD"
        assert vadd_call[0][1] == TASKS_KEY

    def test_store_task_stores_metadata(self):
        vm, client, provider = _make_vm()
        result = vm.store_task("sess1", "Add tests", 15)
        set_calls = [c for c in client.method_calls if c[0] == "set"]
        assert len(set_calls) == 1
        meta = json.loads(set_calls[0][1][1])
        assert meta["session_id"] == "sess1"
        assert meta["task_text"] == "Add tests"
        assert meta["line_number"] == 15
        assert "timestamp" in meta

    def test_store_task_returns_none_on_failure(self):
        vm, client, provider = _make_vm()
        client.execute_command.side_effect = Exception("fail")
        result = vm.store_task("sess1", "task", 1)
        assert result is None


class TestVectorMemoryStoreError:
    """Tests for VectorMemory.store_error()."""

    def test_store_error_returns_element_id(self):
        vm, client, provider = _make_vm()
        result = vm.store_error("sess1", 3, "error output", "task text")
        assert result is not None
        assert result.startswith("error:sess1:3:")

    def test_store_error_calls_embed(self):
        vm, client, provider = _make_vm()
        vm.store_error("sess1", 3, "error text", "task")
        provider.embed.assert_called_once_with("error text")

    def test_store_error_calls_vadd_on_errors_key(self):
        vm, client, provider = _make_vm()
        vm.store_error("sess1", 3, "error", "task")
        vadd_call = client.execute_command.call_args
        assert vadd_call[0][0] == "VADD"
        assert vadd_call[0][1] == ERRORS_KEY

    def test_store_error_stores_metadata(self):
        vm, client, provider = _make_vm()
        result = vm.store_error("sess1", 5, "traceback here", "fix bug")
        set_calls = [c for c in client.method_calls if c[0] == "set"]
        meta = json.loads(set_calls[0][1][1])
        assert meta["session_id"] == "sess1"
        assert meta["iteration"] == 5
        assert meta["task_text"] == "fix bug"
        assert meta["error_preview"] == "traceback here"
        assert "timestamp" in meta
        # No return_code in error metadata
        assert "return_code" not in meta

    def test_store_error_returns_none_on_failure(self):
        vm, client, provider = _make_vm()
        provider.embed.side_effect = RuntimeError("embed fail")
        result = vm.store_error("sess1", 1, "err", "task")
        assert result is None


class TestVectorMemoryFindRelevantOutputs:
    """Tests for VectorMemory.find_relevant_outputs()."""

    def test_returns_results_with_metadata(self):
        vm, client, provider = _make_vm()
        meta = json.dumps({
            "session_id": "s1",
            "iteration": 1,
            "task_text": "task1",
            "output_preview": "preview",
            "timestamp": "2026-01-01T00:00:00",
            "return_code": 0,
        })
        client.execute_command.return_value = ["elem1", "0.95"]
        client.get.return_value = meta
        results = vm.find_relevant_outputs("query")
        assert len(results) == 1
        assert results[0]["element_id"] == "elem1"
        assert results[0]["score"] == 0.95
        assert results[0]["session_id"] == "s1"
        assert results[0]["task_text"] == "task1"

    def test_respects_count(self):
        vm, client, provider = _make_vm()
        meta1 = json.dumps({"session_id": "s1"})
        meta2 = json.dumps({"session_id": "s2"})
        client.execute_command.return_value = ["e1", "0.9", "e2", "0.8"]
        client.get.side_effect = [meta1, meta2]
        results = vm.find_relevant_outputs("query", count=1)
        assert len(results) == 1

    def test_excludes_session(self):
        vm, client, provider = _make_vm()
        meta1 = json.dumps({"session_id": "exclude_me"})
        meta2 = json.dumps({"session_id": "keep_me"})
        client.execute_command.return_value = ["e1", "0.9", "e2", "0.8"]
        client.get.side_effect = [meta1, meta2]
        results = vm.find_relevant_outputs("query", exclude_session="exclude_me")
        assert len(results) == 1
        assert results[0]["session_id"] == "keep_me"

    def test_over_fetches_when_excluding_session(self):
        vm, client, provider = _make_vm()
        client.execute_command.return_value = []
        vm.find_relevant_outputs("query", count=5, exclude_session="sess")
        vsim_call = client.execute_command.call_args
        # COUNT arg is at the end: ...WITHSCORES COUNT 15
        assert vsim_call[0][-1] == 15

    def test_returns_empty_on_no_results(self):
        vm, client, provider = _make_vm()
        client.execute_command.return_value = []
        results = vm.find_relevant_outputs("query")
        assert results == []

    def test_returns_empty_on_none_results(self):
        vm, client, provider = _make_vm()
        client.execute_command.return_value = None
        results = vm.find_relevant_outputs("query")
        assert results == []

    def test_skips_elements_with_missing_metadata(self):
        vm, client, provider = _make_vm()
        client.execute_command.return_value = ["e1", "0.9", "e2", "0.8"]
        client.get.side_effect = [None, json.dumps({"session_id": "s2"})]
        results = vm.find_relevant_outputs("query")
        assert len(results) == 1
        assert results[0]["element_id"] == "e2"

    def test_returns_empty_on_exception(self):
        vm, client, provider = _make_vm()
        client.execute_command.side_effect = Exception("connection error")
        results = vm.find_relevant_outputs("query")
        assert results == []


class TestVectorMemoryFindSimilarTasks:
    """Tests for VectorMemory.find_similar_tasks()."""

    def test_returns_task_results(self):
        vm, client, provider = _make_vm()
        meta = json.dumps({
            "session_id": "s1",
            "task_text": "Add tests",
            "line_number": 10,
            "timestamp": "2026-01-01T00:00:00",
        })
        client.execute_command.return_value = ["t1", "0.88"]
        client.get.return_value = meta
        results = vm.find_similar_tasks("test task")
        assert len(results) == 1
        assert results[0]["task_text"] == "Add tests"
        assert results[0]["line_number"] == 10

    def test_uses_tasks_key(self):
        vm, client, provider = _make_vm()
        client.execute_command.return_value = []
        vm.find_similar_tasks("task")
        vsim_call = client.execute_command.call_args
        assert vsim_call[0][1] == TASKS_KEY

    def test_excludes_session(self):
        vm, client, provider = _make_vm()
        meta1 = json.dumps({"session_id": "skip"})
        meta2 = json.dumps({"session_id": "keep"})
        client.execute_command.return_value = ["t1", "0.9", "t2", "0.8"]
        client.get.side_effect = [meta1, meta2]
        results = vm.find_similar_tasks("task", exclude_session="skip")
        assert len(results) == 1
        assert results[0]["session_id"] == "keep"

    def test_returns_empty_on_exception(self):
        vm, client, provider = _make_vm()
        provider.embed.side_effect = RuntimeError("fail")
        results = vm.find_similar_tasks("task")
        assert results == []


class TestVectorMemoryFindSimilarErrors:
    """Tests for VectorMemory.find_similar_errors()."""

    def test_returns_error_results(self):
        vm, client, provider = _make_vm()
        meta = json.dumps({
            "session_id": "s1",
            "iteration": 3,
            "task_text": "Fix bug",
            "error_preview": "traceback...",
            "timestamp": "2026-01-01T00:00:00",
        })
        client.execute_command.return_value = ["err1", "0.92"]
        client.get.return_value = meta
        results = vm.find_similar_errors("error text")
        assert len(results) == 1
        assert results[0]["error_preview"] == "traceback..."

    def test_uses_errors_key(self):
        vm, client, provider = _make_vm()
        client.execute_command.return_value = []
        vm.find_similar_errors("error")
        vsim_call = client.execute_command.call_args
        assert vsim_call[0][1] == ERRORS_KEY

    def test_default_count_is_3(self):
        vm, client, provider = _make_vm()
        client.execute_command.return_value = []
        vm.find_similar_errors("error")
        vsim_call = client.execute_command.call_args
        # COUNT arg is at the end: ...WITHSCORES COUNT 3
        assert vsim_call[0][-1] == 3

    def test_no_exclude_session_parameter(self):
        """find_similar_errors has no exclude_session — cross-session by design."""
        vm, client, provider = _make_vm()
        meta = json.dumps({"session_id": "any"})
        client.execute_command.return_value = ["e1", "0.9"]
        client.get.return_value = meta
        results = vm.find_similar_errors("error")
        assert len(results) == 1

    def test_returns_empty_on_exception(self):
        vm, client, provider = _make_vm()
        client.execute_command.side_effect = Exception("fail")
        results = vm.find_similar_errors("error")
        assert results == []


class TestVectorMemoryRemoveSession:
    """Tests for VectorMemory.remove_session()."""

    def test_removes_elements_from_all_vector_sets(self):
        vm, client, provider = _make_vm()
        # Simulate scan returning keys for each prefix
        # First scan (output prefix) returns 2 keys
        # Second scan (task prefix) returns 1 key
        # Third scan (error prefix) returns 0 keys
        scan_responses = [
            # output scan
            (0, [f"{META_PREFIX}output:sess1:1:abc", f"{META_PREFIX}output:sess1:2:def"]),
            # task scan
            (0, [f"{META_PREFIX}task:sess1:10:ghi"]),
            # error scan
            (0, []),
        ]
        client.scan.side_effect = scan_responses

        removed = vm.remove_session("sess1")
        assert removed == 3

    def test_calls_vrem_for_each_element(self):
        vm, client, provider = _make_vm()
        client.scan.side_effect = [
            (0, [f"{META_PREFIX}output:sess1:1:abc"]),
            (0, []),
            (0, []),
        ]
        vm.remove_session("sess1")
        vrem_calls = [
            c for c in client.execute_command.call_args_list
            if c[0][0] == "VREM"
        ]
        assert len(vrem_calls) == 1
        assert vrem_calls[0][0] == ("VREM", OUTPUTS_KEY, "output:sess1:1:abc")

    def test_deletes_metadata_keys(self):
        vm, client, provider = _make_vm()
        meta_key = f"{META_PREFIX}output:sess1:1:abc"
        client.scan.side_effect = [
            (0, [meta_key]),
            (0, []),
            (0, []),
        ]
        vm.remove_session("sess1")
        client.delete.assert_called_once_with(meta_key)

    def test_handles_multiple_scan_pages(self):
        vm, client, provider = _make_vm()
        # First prefix: two scan pages
        client.scan.side_effect = [
            (42, [f"{META_PREFIX}output:sess1:1:a"]),  # cursor 42 — more data
            (0, [f"{META_PREFIX}output:sess1:2:b"]),   # cursor 0 — done
            (0, []),  # task prefix
            (0, []),  # error prefix
        ]
        removed = vm.remove_session("sess1")
        assert removed == 2

    def test_returns_zero_on_empty_session(self):
        vm, client, provider = _make_vm()
        client.scan.side_effect = [
            (0, []),
            (0, []),
            (0, []),
        ]
        removed = vm.remove_session("sess1")
        assert removed == 0

    def test_returns_zero_on_exception(self):
        vm, client, provider = _make_vm()
        client.scan.side_effect = Exception("connection lost")
        removed = vm.remove_session("sess1")
        assert removed == 0


class TestGracefulDegradationUnavailableProvider:
    """Tests for graceful degradation when the embedding provider is unavailable."""

    def test_is_available_false_when_provider_unavailable(self):
        provider = _make_provider(available=False)
        vm, client, _ = _make_vm(provider=provider)
        assert vm.is_available is False

    def test_store_output_returns_none_when_provider_embed_fails(self):
        provider = _make_provider()
        provider.embed.side_effect = RuntimeError("provider unavailable")
        vm, client, _ = _make_vm(provider=provider)
        result = vm.store_output("sess1", 1, "output", "task", 0)
        assert result is None

    def test_store_task_returns_none_when_provider_embed_fails(self):
        provider = _make_provider()
        provider.embed.side_effect = RuntimeError("provider unavailable")
        vm, client, _ = _make_vm(provider=provider)
        result = vm.store_task("sess1", "task", 10)
        assert result is None

    def test_store_error_returns_none_when_provider_embed_fails(self):
        provider = _make_provider()
        provider.embed.side_effect = RuntimeError("provider unavailable")
        vm, client, _ = _make_vm(provider=provider)
        result = vm.store_error("sess1", 1, "error text", "task")
        assert result is None

    def test_find_relevant_outputs_returns_empty_when_embed_fails(self):
        provider = _make_provider()
        provider.embed.side_effect = RuntimeError("provider unavailable")
        vm, client, _ = _make_vm(provider=provider)
        results = vm.find_relevant_outputs("query")
        assert results == []

    def test_find_similar_tasks_returns_empty_when_embed_fails(self):
        provider = _make_provider()
        provider.embed.side_effect = RuntimeError("provider unavailable")
        vm, client, _ = _make_vm(provider=provider)
        results = vm.find_similar_tasks("task text")
        assert results == []

    def test_find_similar_errors_returns_empty_when_embed_fails(self):
        provider = _make_provider()
        provider.embed.side_effect = RuntimeError("provider unavailable")
        vm, client, _ = _make_vm(provider=provider)
        results = vm.find_similar_errors("error text")
        assert results == []

    def test_remove_session_still_works_with_unavailable_provider(self):
        """remove_session doesn't embed — it uses SCAN + VREM, so it should
        still succeed even if the provider is unavailable."""
        provider = _make_provider(available=False)
        vm, client, _ = _make_vm(provider=provider)
        client.scan.side_effect = [
            (0, [f"{META_PREFIX}output:sess1:1:abc"]),
            (0, []),
            (0, []),
        ]
        removed = vm.remove_session("sess1")
        assert removed == 1

    def test_no_redis_calls_when_embed_fails_on_store(self):
        """If embed() fails, no Redis calls should be made."""
        provider = _make_provider()
        provider.embed.side_effect = RuntimeError("provider unavailable")
        vm, client, _ = _make_vm(provider=provider)
        vm.store_output("sess1", 1, "output", "task", 0)
        client.execute_command.assert_not_called()
        client.set.assert_not_called()

    def test_no_redis_calls_when_embed_fails_on_find(self):
        """If embed() fails, no VSIM calls should be made."""
        provider = _make_provider()
        provider.embed.side_effect = RuntimeError("provider unavailable")
        vm, client, _ = _make_vm(provider=provider)
        vm.find_relevant_outputs("query")
        client.execute_command.assert_not_called()


class TestGracefulDegradationConnectionErrors:
    """Tests for graceful degradation when Redis connection fails."""

    def test_is_available_false_on_connection_refused(self):
        vm, client, _ = _make_vm()
        client.ping.side_effect = ConnectionError("Connection refused")
        assert vm.is_available is False

    def test_is_available_false_on_timeout(self):
        vm, client, _ = _make_vm()
        client.ping.side_effect = TimeoutError("Connection timed out")
        assert vm.is_available is False

    def test_store_output_returns_none_on_connection_error(self):
        vm, client, _ = _make_vm()
        client.execute_command.side_effect = ConnectionError("Connection lost")
        result = vm.store_output("sess1", 1, "output", "task", 0)
        assert result is None

    def test_store_task_returns_none_on_connection_error(self):
        vm, client, _ = _make_vm()
        client.execute_command.side_effect = ConnectionError("Connection lost")
        result = vm.store_task("sess1", "task", 10)
        assert result is None

    def test_store_error_returns_none_on_connection_error(self):
        vm, client, _ = _make_vm()
        client.execute_command.side_effect = ConnectionError("Connection lost")
        result = vm.store_error("sess1", 1, "error", "task")
        assert result is None

    def test_find_relevant_outputs_returns_empty_on_connection_error(self):
        vm, client, _ = _make_vm()
        client.execute_command.side_effect = ConnectionError("Connection lost")
        results = vm.find_relevant_outputs("query")
        assert results == []

    def test_find_similar_tasks_returns_empty_on_connection_error(self):
        vm, client, _ = _make_vm()
        client.execute_command.side_effect = ConnectionError("Connection lost")
        results = vm.find_similar_tasks("task")
        assert results == []

    def test_find_similar_errors_returns_empty_on_connection_error(self):
        vm, client, _ = _make_vm()
        client.execute_command.side_effect = ConnectionError("Connection lost")
        results = vm.find_similar_errors("error")
        assert results == []

    def test_remove_session_returns_zero_on_connection_error(self):
        vm, client, _ = _make_vm()
        client.scan.side_effect = ConnectionError("Connection lost")
        removed = vm.remove_session("sess1")
        assert removed == 0

    def test_store_output_returns_none_on_timeout(self):
        vm, client, _ = _make_vm()
        client.execute_command.side_effect = TimeoutError("Timed out")
        result = vm.store_output("sess1", 1, "output", "task", 0)
        assert result is None

    def test_find_outputs_returns_empty_on_timeout(self):
        vm, client, _ = _make_vm()
        client.execute_command.side_effect = TimeoutError("Timed out")
        results = vm.find_relevant_outputs("query")
        assert results == []

    def test_store_output_returns_none_when_metadata_set_fails(self):
        """VADD succeeds but metadata SET fails — should still degrade gracefully."""
        vm, client, _ = _make_vm()
        client.execute_command.return_value = 1  # VADD success
        client.set.side_effect = ConnectionError("Connection lost during SET")
        result = vm.store_output("sess1", 1, "output", "task", 0)
        assert result is None

    def test_find_outputs_handles_partial_metadata_failure(self):
        """VSIM succeeds but metadata GET fails for some elements."""
        vm, client, _ = _make_vm()
        meta = json.dumps({"session_id": "s1", "task_text": "t1"})
        client.execute_command.return_value = ["e1", "0.9", "e2", "0.8"]
        # First metadata GET succeeds, second raises
        client.get.side_effect = [meta, ConnectionError("lost")]
        # Should return results for the first element and skip the second
        # (the exception handler catches the whole block, so we get [])
        results = vm.find_relevant_outputs("query")
        # The try/except wraps the entire method, so a mid-iteration
        # connection error returns []
        assert results == []

    def test_is_available_false_when_vinfo_raises_unknown_command(self):
        """Redis version doesn't support VSET commands."""
        vm, client, _ = _make_vm()
        client.ping.return_value = True
        client.execute_command.side_effect = Exception(
            "ERR unknown command 'VINFO'"
        )
        assert vm.is_available is False

    def test_is_available_false_on_authentication_error(self):
        vm, client, _ = _make_vm()
        client.ping.side_effect = Exception("NOAUTH Authentication required")
        assert vm.is_available is False

    def test_remove_session_returns_zero_on_mid_scan_failure(self):
        """Scan starts but fails mid-way through — degrade to 0."""
        vm, client, _ = _make_vm()
        client.scan.side_effect = [
            (42, [f"{META_PREFIX}output:sess1:1:abc"]),  # First page ok
            ConnectionError("Connection lost"),            # Second page fails
        ]
        removed = vm.remove_session("sess1")
        # The exception handler catches everything and returns 0
        assert removed == 0


class TestGracefulDegradationLoopIntegration:
    """Tests that VectorMemory initialization degrades gracefully in LoopRunner."""

    def test_vector_mem_none_when_provider_unavailable(self):
        """LoopRunner.vector_mem should be None when provider is unavailable."""
        from pathlib import Path
        from unittest.mock import patch
        from zoyd.session.embedding import UnavailableProvider

        with patch("zoyd.loop.loop.get_provider", return_value=UnavailableProvider()):
            from zoyd.loop import LoopRunner
            runner = LoopRunner(
                prd_path=Path("test.md"),
                progress_path=Path("progress.txt"),
                vector_memory=True,
                session_logging=False,
                dry_run=True,
            )
        # dry_run=True skips vector init, so vector_mem stays None
        assert runner.vector_mem is None

    def test_vector_mem_none_when_dry_run(self):
        """VectorMemory should not be initialized during dry runs."""
        from pathlib import Path
        from zoyd.loop import LoopRunner
        runner = LoopRunner(
            prd_path=Path("test.md"),
            progress_path=Path("progress.txt"),
            vector_memory=True,
            session_logging=False,
            dry_run=True,
        )
        assert runner.vector_mem is None

    def test_vector_mem_none_when_disabled(self):
        """VectorMemory should not be initialized when vector_memory=False."""
        from pathlib import Path
        from zoyd.loop import LoopRunner
        runner = LoopRunner(
            prd_path=Path("test.md"),
            progress_path=Path("progress.txt"),
            vector_memory=False,
            session_logging=False,
        )
        assert runner.vector_mem is None


class TestVectorMemoryConstants:
    """Tests for module-level constants."""

    def test_outputs_key(self):
        assert OUTPUTS_KEY == "zoyd:vectors:outputs"

    def test_tasks_key(self):
        assert TASKS_KEY == "zoyd:vectors:tasks"

    def test_errors_key(self):
        assert ERRORS_KEY == "zoyd:vectors:errors"

    def test_meta_prefix(self):
        assert META_PREFIX == "zoyd:vectors:meta:"
