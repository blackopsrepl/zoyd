"""Tests for prompt building with memory functionality."""

import pytest
from unittest.mock import patch, MagicMock

from zoyd.loop import (
    build_prompt_with_memory,
    _format_relevant_context,
)


class TestBuildPromptWithMemory:
    def test_format_with_all_fields(self):
        """Test that build_prompt_with_memory fills all placeholders."""
        prompt = build_prompt_with_memory(
            prd_content="# PRD\n- [ ] Task 1",
            relevant_context="### 1. Similar task\nSome past output",
            recent_progress="## Iteration 5\nDid stuff",
            iteration=6,
            completed=3,
            total=10,
            current_task="Task 1",
        )
        assert "Iteration 6" in prompt
        assert "3/10 tasks complete" in prompt
        assert "## Current Task (COMPLETE THIS ONLY)" in prompt
        assert "Task 1" in prompt
        assert "## Relevant Context from Past Work" in prompt
        assert "### 1. Similar task" in prompt
        assert "Some past output" in prompt
        assert "## Recent Progress" in prompt
        assert "## Iteration 5" in prompt
        assert "Did stuff" in prompt
        assert "## PRD (for context only)" in prompt
        assert "# PRD" in prompt
        assert "- [ ] Task 1" in prompt

    def test_empty_relevant_context_shows_placeholder(self):
        """Test that empty relevant_context shows fallback text."""
        prompt = build_prompt_with_memory(
            prd_content="# PRD",
            relevant_context="",
            recent_progress="## Iteration 1\nProgress",
            iteration=2,
            completed=0,
            total=1,
            current_task="Task A",
        )
        assert "(No relevant context found)" in prompt

    def test_none_relevant_context_shows_placeholder(self):
        """Test that None relevant_context shows fallback text."""
        prompt = build_prompt_with_memory(
            prd_content="# PRD",
            relevant_context=None,
            recent_progress="## Iteration 1\nProgress",
            iteration=2,
            completed=0,
            total=1,
            current_task="Task A",
        )
        assert "(No relevant context found)" in prompt

    def test_empty_recent_progress_shows_placeholder(self):
        """Test that empty recent_progress shows fallback text."""
        prompt = build_prompt_with_memory(
            prd_content="# PRD",
            relevant_context="Some context",
            recent_progress="",
            iteration=1,
            completed=0,
            total=1,
            current_task="Task A",
        )
        assert "(No progress yet)" in prompt

    def test_none_recent_progress_shows_placeholder(self):
        """Test that None recent_progress shows fallback text."""
        prompt = build_prompt_with_memory(
            prd_content="# PRD",
            relevant_context="Some context",
            recent_progress=None,
            iteration=1,
            completed=0,
            total=1,
            current_task="Task A",
        )
        assert "(No progress yet)" in prompt

    def test_both_empty_show_placeholders(self):
        """Test that both empty context and progress show their placeholders."""
        prompt = build_prompt_with_memory(
            prd_content="# PRD",
            relevant_context="",
            recent_progress="",
            iteration=1,
            completed=0,
            total=1,
            current_task="Task A",
        )
        assert "(No relevant context found)" in prompt
        assert "(No progress yet)" in prompt

    def test_uses_memory_template(self):
        """Test that build_prompt_with_memory uses PROMPT_TEMPLATE_WITH_MEMORY."""
        prompt = build_prompt_with_memory(
            prd_content="# PRD",
            relevant_context="context here",
            recent_progress="progress here",
            iteration=1,
            completed=0,
            total=1,
            current_task="My Task",
        )
        # The memory template has "Relevant Context from Past Work" section
        assert "Relevant Context from Past Work" in prompt
        # And "Recent Progress" section instead of full progress log
        assert "Recent Progress" in prompt
        # Should NOT contain the regular template's full progress section header
        assert "## Progress Log" not in prompt

    def test_current_task_in_prompt(self):
        """Test that current task is prominently displayed."""
        prompt = build_prompt_with_memory(
            prd_content="# PRD\n- [ ] Implement feature X\n- [ ] Fix bug Y",
            relevant_context="Past work on feature X",
            recent_progress="## Iteration 3\nWorked on setup",
            iteration=4,
            completed=1,
            total=3,
            current_task="Implement feature X",
        )
        assert "## Current Task (COMPLETE THIS ONLY)" in prompt
        assert "Implement feature X" in prompt
        assert "IMPORTANT: Work on ONLY this task" in prompt
        assert "Do NOT run any git commands" in prompt

    def test_no_git_instruction(self):
        """Test that the no-git instruction is present."""
        prompt = build_prompt_with_memory(
            prd_content="# PRD",
            relevant_context="",
            recent_progress="",
            iteration=1,
            completed=0,
            total=1,
            current_task="Task A",
        )
        assert "Do NOT run any git commands" in prompt
        assert "no git add, git commit, git push" in prompt

    def test_relevant_context_with_multiple_results(self):
        """Test prompt with multi-result relevant context."""
        context = (
            "### 1. Build authentication module\n"
            "Session: abc12345 | Iteration: 3 | Exit: 0 | Similarity: 0.875\n"
            "Implemented JWT auth...\n"
            "---\n"
            "### 2. Add login endpoint\n"
            "Session: def67890 | Iteration: 7 | Exit: 0 | Similarity: 0.812\n"
            "Created /api/login route..."
        )
        prompt = build_prompt_with_memory(
            prd_content="# PRD",
            relevant_context=context,
            recent_progress="## Iteration 10\nRecent work",
            iteration=11,
            completed=5,
            total=10,
            current_task="Add logout endpoint",
        )
        assert "### 1. Build authentication module" in prompt
        assert "### 2. Add login endpoint" in prompt
        assert "Similarity: 0.875" in prompt
        assert "Similarity: 0.812" in prompt