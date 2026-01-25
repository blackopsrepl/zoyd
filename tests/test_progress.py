"""Tests for progress tracking."""

import pytest
from pathlib import Path

from zoyd.progress import (
    read_progress,
    get_iteration_count,
    append_iteration,
    init_progress_file,
)


class TestReadProgress:
    def test_read_existing_file(self, tmp_path):
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Progress\nSome content")
        content = read_progress(progress_file)
        assert content == "# Progress\nSome content"

    def test_read_nonexistent_file(self, tmp_path):
        progress_file = tmp_path / "nonexistent.txt"
        content = read_progress(progress_file)
        assert content == ""


class TestGetIterationCount:
    def test_no_iterations(self):
        content = "# Progress Log\nNo iterations yet"
        assert get_iteration_count(content) == 0

    def test_one_iteration(self):
        content = """# Progress Log

## Iteration 1 - 2024-01-01 12:00:00

Some output here.
"""
        assert get_iteration_count(content) == 1

    def test_multiple_iterations(self):
        content = """# Progress Log

## Iteration 1 - 2024-01-01 12:00:00

First output.

## Iteration 2 - 2024-01-01 12:05:00

Second output.

## Iteration 3 - 2024-01-01 12:10:00

Third output.
"""
        assert get_iteration_count(content) == 3

    def test_empty_content(self):
        assert get_iteration_count("") == 0


class TestAppendIteration:
    def test_append_to_new_file(self, tmp_path):
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Progress\n")

        append_iteration(progress_file, 1, "Claude output here")

        content = progress_file.read_text()
        assert "## Iteration 1" in content
        assert "Claude output here" in content

    def test_append_multiple(self, tmp_path):
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Progress\n")

        append_iteration(progress_file, 1, "First")
        append_iteration(progress_file, 2, "Second")

        content = progress_file.read_text()
        assert "## Iteration 1" in content
        assert "## Iteration 2" in content
        assert "First" in content
        assert "Second" in content


class TestInitProgressFile:
    def test_init_creates_file(self, tmp_path):
        progress_file = tmp_path / "progress.txt"
        assert not progress_file.exists()

        init_progress_file(progress_file)

        assert progress_file.exists()
        assert "# Zoyd Progress Log" in progress_file.read_text()

    def test_init_does_not_overwrite(self, tmp_path):
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("Existing content")

        init_progress_file(progress_file)

        assert progress_file.read_text() == "Existing content"


class TestAppendIterationBlocked:
    """Tests for append_iteration with blocked task detection."""

    def test_append_blocked_iteration(self, tmp_path):
        """Test appending an iteration marked as blocked."""
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Progress\n")

        append_iteration(
            progress_file,
            1,
            "I cannot complete this task.",
            cannot_complete=True,
            cannot_complete_reason="cannot complete this task",
        )

        content = progress_file.read_text()
        assert "[BLOCKED]" in content
        assert "**Blocked reason:**" in content
        assert "cannot complete this task" in content

    def test_append_normal_iteration_no_blocked_marker(self, tmp_path):
        """Test that normal iterations don't have blocked marker."""
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Progress\n")

        append_iteration(progress_file, 1, "Task completed successfully.")

        content = progress_file.read_text()
        assert "[BLOCKED]" not in content
        assert "**Blocked reason:**" not in content

    def test_append_blocked_without_reason(self, tmp_path):
        """Test appending a blocked iteration without a specific reason."""
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Progress\n")

        append_iteration(
            progress_file,
            1,
            "Cannot proceed.",
            cannot_complete=True,
            cannot_complete_reason=None,
        )

        content = progress_file.read_text()
        assert "[BLOCKED]" in content
        assert "**Blocked reason:**" not in content

    def test_mixed_blocked_and_normal(self, tmp_path):
        """Test mixing blocked and normal iterations."""
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Progress\n")

        append_iteration(progress_file, 1, "First task done.")
        append_iteration(
            progress_file,
            2,
            "I am blocked on this.",
            cannot_complete=True,
            cannot_complete_reason="blocked on",
        )
        append_iteration(progress_file, 3, "Third task done.")

        content = progress_file.read_text()
        assert "## Iteration 1" in content
        assert "## Iteration 2" in content and "[BLOCKED]" in content
        assert "## Iteration 3" in content
        # Only iteration 2 should be blocked
        lines = content.split("\n")
        blocked_count = sum(1 for line in lines if "[BLOCKED]" in line)
        assert blocked_count == 1
