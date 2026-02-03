"""Tests for prompt building functionality."""

import pytest
from unittest.mock import patch, MagicMock

from zoyd.loop import (
    build_prompt,
    build_prompt_with_memory,
    PROMPT_TEMPLATE_WITH_MEMORY,
)


class TestBuildPrompt:
    def test_build_prompt_format(self):
        """Test that build_prompt generates correct format."""
        prompt = build_prompt(
            prd_content="# PRD\n- [ ] Task 1",
            progress_content="# Progress",
            iteration=1,
            completed=0,
            total=1,
            current_task="Task 1",
        )
        assert "Iteration 1" in prompt
        assert "0/1 tasks complete" in prompt
        assert "# PRD" in prompt
        assert "- [ ] Task 1" in prompt
        # Check for new current task section
        assert "## Current Task (COMPLETE THIS ONLY)" in prompt
        assert "Task 1" in prompt
        assert "IMPORTANT: Work on ONLY this task" in prompt
        assert "Do NOT run any git commands" in prompt

    def test_build_prompt_empty_progress(self):
        """Test that empty progress shows placeholder."""
        prompt = build_prompt(
            prd_content="# PRD",
            progress_content="",
            iteration=1,
            completed=0,
            total=1,
            current_task="Task 1",
        )
        assert "(No progress yet)" in prompt

    def test_build_prompt_current_task_displayed(self):
        """Test that current task is highlighted in the prompt."""
        prompt = build_prompt(
            prd_content="# PRD\n- [ ] Task A\n- [ ] Task B",
            progress_content="",
            iteration=1,
            completed=0,
            total=2,
            current_task="Task A",
        )
        assert "## Current Task (COMPLETE THIS ONLY)" in prompt
        assert "Task A" in prompt
        assert "Do NOT work on other tasks" in prompt