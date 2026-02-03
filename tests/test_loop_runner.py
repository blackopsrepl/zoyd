"""Tests for LoopRunner class functionality."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from zoyd.loop import LoopRunner


class TestLoopRunner:
    def test_default_delay(self, tmp_path):
        """Test that default delay is 1.0 second."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
        )
        assert runner.delay == 1.0

    def test_backoff_delay_no_failures(self, tmp_path):
        """Test that backoff delay is 0 with no failures."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        runner.consecutive_failures = 0
        assert runner.get_backoff_delay() == 0.0

    def test_backoff_delay_one_failure(self, tmp_path):
        """Test exponential backoff after 1 failure (2^1 = 2s)."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        runner.consecutive_failures = 1
        assert runner.get_backoff_delay() == 2.0

    def test_backoff_delay_two_failures(self, tmp_path):
        """Test exponential backoff after 2 failures (2^2 = 4s)."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        runner.consecutive_failures = 2
        assert runner.get_backoff_delay() == 4.0

    def test_backoff_delay_three_failures(self, tmp_path):
        """Test exponential backoff after 3 failures (2^3 = 8s)."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        runner.consecutive_failures = 3
        assert runner.get_backoff_delay() == 8.0

    def test_custom_delay(self, tmp_path):
        """Test that custom delay can be set."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            delay=5.0,
        )
        assert runner.delay == 5.0

    def test_zero_delay(self, tmp_path):
        """Test that zero delay is allowed."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            delay=0.0,
        )
        assert runner.delay == 0.0

    def test_rate_limit_status_default(self, tmp_path):
        """Test rate limit status with default delay."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert runner.get_rate_limit_status() == "delay=1.0s"

    def test_rate_limit_status_zero_delay(self, tmp_path):
        """Test rate limit status with zero delay."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file, delay=0.0)
        assert runner.get_rate_limit_status() == "delay=0s"

    def test_rate_limit_status_custom_delay(self, tmp_path):
        """Test rate limit status with custom delay."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file, delay=2.5)
        assert runner.get_rate_limit_status() == "delay=2.5s"

    def test_rate_limit_status_with_backoff(self, tmp_path):
        """Test rate limit status includes backoff after failure."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        runner.consecutive_failures = 2
        assert runner.get_rate_limit_status() == "delay=1.0s, backoff=4.0s"

    def test_rate_limit_status_zero_delay_with_backoff(self, tmp_path):
        """Test rate limit status with zero delay but active backoff."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file, delay=0.0)
        runner.consecutive_failures = 1
        assert runner.get_rate_limit_status() == "delay=0s, backoff=2.0s"