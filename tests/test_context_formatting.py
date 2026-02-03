"""Tests for relevant context formatting."""

import pytest
from unittest.mock import patch, MagicMock

from zoyd.loop import _format_relevant_context


class TestFormatRelevantContext:
    """Tests for _format_relevant_context result formatting."""

    def test_empty_results_returns_placeholder(self):
        """Empty list returns the placeholder string."""
        assert _format_relevant_context([]) == "(No relevant context found)"

    def test_single_result_formatted(self):
        """A single result is formatted with header, metadata, and preview."""
        results = [
            {
                "element_id": "output:abc:1:deadbeef",
                "score": 0.875,
                "session_id": "abcdef1234567890",
                "iteration": 3,
                "task_text": "Implement login",
                "output_preview": "Added login form with validation.",
                "timestamp": "2026-01-25T14:00:00",
                "return_code": 0,
            }
        ]
        result = _format_relevant_context(results)
        assert "### 1. Implement login" in result
        assert "Session: abcdef12" in result
        assert "Iteration: 3" in result
        assert "Exit: 0" in result
        assert "Similarity: 0.875" in result
        assert "Added login form with validation." in result

    def test_multiple_results_numbered(self):
        """Multiple results are numbered sequentially."""
        results = [
            {
                "element_id": "output:a:1:aa",
                "score": 0.9,
                "session_id": "aaaa1111bbbb2222",
                "iteration": 1,
                "task_text": "First task",
                "output_preview": "First output.",
                "timestamp": "2026-01-25T14:00:00",
                "return_code": 0,
            },
            {
                "element_id": "output:b:2:bb",
                "score": 0.8,
                "session_id": "cccc3333dddd4444",
                "iteration": 2,
                "task_text": "Second task",
                "output_preview": "Second output.",
                "timestamp": "2026-01-25T15:00:00",
                "return_code": 0,
            },
        ]
        result = _format_relevant_context(results)
        assert "### 1. First task" in result
        assert "### 2. Second task" in result
        assert "First output." in result
        assert "Second output." in result

    def test_results_separated_by_horizontal_rule(self):
        """Multiple results are separated by --- horizontal rules."""
        results = [
            {
                "element_id": "output:a:1:aa",
                "score": 0.9,
                "session_id": "aaaa1111",
                "iteration": 1,
                "task_text": "Task A",
                "output_preview": "Output A.",
                "timestamp": "2026-01-25T14:00:00",
                "return_code": 0,
            },
            {
                "element_id": "output:b:2:bb",
                "score": 0.8,
                "session_id": "bbbb2222",
                "iteration": 2,
                "task_text": "Task B",
                "output_preview": "Output B.",
                "timestamp": "2026-01-25T15:00:00",
                "return_code": 0,
            },
        ]
        result = _format_relevant_context(results)
        assert "\n\n---\n\n" in result

    def test_session_id_truncated_to_8_chars(self):
        """Session ID is truncated to first 8 characters."""
        results = [
            {
                "element_id": "output:x:1:xx",
                "score": 0.5,
                "session_id": "abcdefghijklmnop",
                "iteration": 1,
                "task_text": "Some task",
                "output_preview": "Preview.",
                "timestamp": "2026-01-25T14:00:00",
                "return_code": 0,
            }
        ]
        result = _format_relevant_context(results)
        assert "Session: abcdefgh" in result
        assert "abcdefghijklmnop" not in result

    def test_return_code_none_omits_exit(self):
        """When return_code is None, Exit field is omitted."""
        results = [
            {
                "element_id": "output:x:1:xx",
                "score": 0.7,
                "session_id": "abcd1234",
                "iteration": 1,
                "task_text": "A task",
                "output_preview": "Preview.",
                "timestamp": "2026-01-25T14:00:00",
                "return_code": None,
            }
        ]
        result = _format_relevant_context(results)
        assert "Exit:" not in result
        assert "Session: abcd1234" in result
        assert "Similarity: 0.700" in result

    def test_missing_return_code_omits_exit(self):
        """When return_code key is missing, Exit field is omitted."""
        results = [
            {
                "element_id": "output:x:1:xx",
                "score": 0.6,
                "session_id": "abcd1234",
                "iteration": 1,
                "task_text": "A task",
                "output_preview": "Preview.",
                "timestamp": "2026-01-25T14:00:00",
            }
        ]
        result = _format_relevant_context(results)
        assert "Exit:" not in result

    def test_missing_fields_use_defaults(self):
        """Missing dict keys fall back to default values."""
        results = [{}]
        result = _format_relevant_context(results)
        assert "### 1. Unknown task" in result
        assert "Session: unknown" in result
        assert "Iteration: ?" in result
        assert "Similarity: 0.000" in result

    def test_score_formatted_to_three_decimals(self):
        """Score is formatted with exactly 3 decimal places."""
        results = [
            {
                "element_id": "output:x:1:xx",
                "score": 0.12345,
                "session_id": "abcd1234",
                "iteration": 1,
                "task_text": "Task",
                "output_preview": "",
                "timestamp": "2026-01-25T14:00:00",
                "return_code": 0,
            }
        ]
        result = _format_relevant_context(results)
        assert "Similarity: 0.123" in result

    def test_metadata_line_pipe_separated(self):
        """Metadata fields are separated by ' | '."""
        results = [
            {
                "element_id": "output:x:1:xx",
                "score": 0.5,
                "session_id": "abcd1234",
                "iteration": 7,
                "task_text": "Task",
                "output_preview": "",
                "timestamp": "2026-01-25T14:00:00",
                "return_code": 1,
            }
        ]
        result = _format_relevant_context(results)
        lines = result.split("\n")
        meta_line = lines[1]
        assert "Session: abcd1234 | Iteration: 7 | Exit: 1 | Similarity: 0.500" == meta_line

    def test_output_preview_on_separate_line(self):
        """Output preview is separated from metadata by a blank line."""
        results = [
            {
                "element_id": "output:x:1:xx",
                "score": 0.5,
                "session_id": "abcd1234",
                "iteration": 1,
                "task_text": "Task",
                "output_preview": "The actual output preview text.",
                "timestamp": "2026-01-25T14:00:00",
                "return_code": 0,
            }
        ]
        result = _format_relevant_context(results)
        # header, meta, blank, preview
        lines = result.split("\n")
        assert lines[0] == "### 1. Task"
        assert lines[2] == ""
        assert lines[3] == "The actual output preview text."