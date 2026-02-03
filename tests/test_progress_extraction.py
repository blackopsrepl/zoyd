"""Tests for progress extraction and formatting."""

import pytest
from unittest.mock import patch, MagicMock

from zoyd.loop import (
    _extract_recent_iterations,
    _format_relevant_context,
    detect_cannot_complete,
)


class TestExtractRecentIterations:
    """Tests for _extract_recent_iterations progress splitting logic."""

    def test_empty_content_returns_empty(self):
        """Empty string returns empty string."""
        assert _extract_recent_iterations("", 3) == ""

    def test_none_content_returns_empty(self):
        """Falsy content returns empty string."""
        assert _extract_recent_iterations(None, 3) == ""

    def test_no_iterations_returns_empty(self):
        """Content without any ## Iteration headers returns empty string."""
        content = "# Zoyd Progress Log\nSome preamble text\nNothing here."
        assert _extract_recent_iterations(content, 3) == ""

    def test_single_iteration(self):
        """Single iteration is returned correctly."""
        content = (
            "# Zoyd Progress Log\n\n"
            "## Iteration 1 - 2026-01-25 14:00:00\n\n"
            "Did some work."
        )
        result = _extract_recent_iterations(content, 3)
        assert "## Iteration 1" in result
        assert "Did some work." in result

    def test_returns_last_n_iterations(self):
        """With more iterations than n, returns only the last n."""
        content = (
            "# Zoyd Progress Log\n\n"
            "## Iteration 1 - 2026-01-25 14:00:00\n\nFirst work.\n\n"
            "## Iteration 2 - 2026-01-25 15:00:00\n\nSecond work.\n\n"
            "## Iteration 3 - 2026-01-25 16:00:00\n\nThird work.\n\n"
            "## Iteration 4 - 2026-01-25 17:00:00\n\nFourth work.\n\n"
            "## Iteration 5 - 2026-01-25 18:00:00\n\nFifth work."
        )
        result = _extract_recent_iterations(content, 2)
        assert "## Iteration 4" in result
        assert "Fourth work." in result
        assert "## Iteration 5" in result
        assert "Fifth work." in result
        assert "## Iteration 1" not in result
        assert "## Iteration 2" not in result
        assert "## Iteration 3" not in result

    def test_n_greater_than_available_returns_all(self):
        """When n exceeds iteration count, returns all iterations."""
        content = (
            "# Zoyd Progress Log\n\n"
            "## Iteration 1 - 2026-01-25 14:00:00\n\nFirst.\n\n"
            "## Iteration 2 - 2026-01-25 15:00:00\n\nSecond."
        )
        result = _extract_recent_iterations(content, 10)
        assert "## Iteration 1" in result
        assert "First." in result
        assert "## Iteration 2" in result
        assert "Second." in result

    def test_preamble_excluded(self):
        """Text before the first ## Iteration header is excluded."""
        content = (
            "# Zoyd Progress Log\n"
            "This is preamble text that should not appear.\n\n"
            "## Iteration 1 - 2026-01-25 14:00:00\n\n"
            "Actual work."
        )
        result = _extract_recent_iterations(content, 5)
        assert "preamble text" not in result
        assert "## Iteration 1" in result
        assert "Actual work." in result

    def test_n_equals_one_returns_last(self):
        """n=1 returns only the most recent iteration."""
        content = (
            "# Zoyd Progress Log\n\n"
            "## Iteration 1 - 2026-01-25 14:00:00\n\nOld work.\n\n"
            "## Iteration 2 - 2026-01-25 15:00:00\n\nRecent work."
        )
        result = _extract_recent_iterations(content, 1)
        assert "## Iteration 2" in result
        assert "Recent work." in result
        assert "## Iteration 1" not in result
        assert "Old work." not in result

    def test_iteration_header_preserved(self):
        """The ## Iteration prefix is restored on each section."""
        content = (
            "# Zoyd Progress Log\n\n"
            "## Iteration 42 - 2026-01-25 14:00:00\n\n"
            "Work on iteration 42."
        )
        result = _extract_recent_iterations(content, 1)
        assert result.startswith("## Iteration 42")

    def test_multiline_iteration_content(self):
        """Iterations with multi-line content are preserved intact."""
        content = (
            "# Log\n\n"
            "## Iteration 1 - 2026-01-25 14:00:00\n\n"
            "Line 1\nLine 2\nLine 3\n\n"
            "## Iteration 2 - 2026-01-25 15:00:00\n\n"
            "Line A\nLine B"
        )
        result = _extract_recent_iterations(content, 1)
        assert "Line A" in result
        assert "Line B" in result
        assert "Line 1" not in result

    def test_n_zero_returns_all(self):
        """n=0 returns all iterations (Python list[-0:] is list[0:])."""
        content = (
            "# Log\n\n"
            "## Iteration 1 - 2026-01-25 14:00:00\n\nWork."
        )
        result = _extract_recent_iterations(content, 0)
        assert "## Iteration 1" in result

    def test_exact_n_returns_all(self):
        """When n equals the number of iterations, all are returned."""
        content = (
            "# Log\n\n"
            "## Iteration 1 - 2026-01-25 14:00:00\n\nFirst.\n\n"
            "## Iteration 2 - 2026-01-25 15:00:00\n\nSecond.\n\n"
            "## Iteration 3 - 2026-01-25 16:00:00\n\nThird."
        )
        result = _extract_recent_iterations(content, 3)
        assert "## Iteration 1" in result
        assert "## Iteration 2" in result
        assert "## Iteration 3" in result