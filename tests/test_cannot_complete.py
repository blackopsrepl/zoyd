"""Tests for cannot complete detection."""

import pytest
from unittest.mock import patch, MagicMock

from zoyd.loop import detect_cannot_complete


class TestDetectCannotComplete:
    """Tests for detecting when Claude cannot complete a task."""

    def test_detect_cannot_complete_direct(self):
        """Test detection of 'I cannot complete this task'."""
        output = "I cannot complete this task because the file doesn't exist."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "cannot complete this task" in reason.lower()

    def test_detect_cant_complete(self):
        """Test detection of 'I can't complete the task'."""
        output = "I can't complete the task without additional permissions."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "can't complete the task" in reason.lower()

    def test_detect_unable_to_complete(self):
        """Test detection of 'unable to complete'."""
        output = "I am unable to complete this task due to missing dependencies."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "unable to" in reason.lower()

    def test_detect_blocked(self):
        """Test detection of 'I'm blocked on'."""
        output = "I'm blocked on getting access to the database configuration."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "blocked" in reason.lower()

    def test_detect_cannot_proceed(self):
        """Test detection of 'cannot proceed with'."""
        output = "I cannot proceed with the implementation until the API is available."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "cannot proceed" in reason.lower()

    def test_detect_task_impossible(self):
        """Test detection of 'task is impossible'."""
        output = "This task is impossible without root access."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "impossible" in reason.lower()

    def test_detect_need_more_info(self):
        """Test detection of 'need more information'."""
        output = "I need more information about the expected output format."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "need more information" in reason.lower()

    def test_detect_blocker_label(self):
        """Test detection of 'Blocker:'."""
        output = "Blocker: The test server is not responding."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "blocker" in reason.lower()

    def test_detect_beyond_capabilities(self):
        """Test detection of 'beyond my capabilities'."""
        output = "This is beyond my capabilities as it requires hardware access."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "beyond" in reason.lower()

    def test_no_detection_normal_output(self):
        """Test that normal output is not detected as blocked."""
        output = "I completed the task successfully. All tests pass."
        detected, reason = detect_cannot_complete(output)
        assert detected is False
        assert reason is None

    def test_no_detection_partial_match(self):
        """Test that partial matches don't trigger false positives."""
        output = "The task can be completed in the next iteration."
        detected, reason = detect_cannot_complete(output)
        assert detected is False
        assert reason is None

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        output = "I CANNOT COMPLETE THIS TASK due to restrictions."
        detected, reason = detect_cannot_complete(output)
        assert detected is True

    def test_detect_require_clarification(self):
        """Test detection of 'require clarification'."""
        output = "I require clarification on which database to use."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "require" in reason.lower()