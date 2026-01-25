"""Tests for progress tracking."""

import pytest
from pathlib import Path

from ralph.progress import (
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
        assert "# Ralph Progress Log" in progress_file.read_text()

    def test_init_does_not_overwrite(self, tmp_path):
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("Existing content")

        init_progress_file(progress_file)

        assert progress_file.read_text() == "Existing content"
