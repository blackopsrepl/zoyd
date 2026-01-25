"""Tests for PRD parsing."""

import pytest

from ralph.prd import (
    Task,
    parse_tasks,
    get_completion_status,
    is_all_complete,
    get_next_incomplete_task,
)


class TestParseTasks:
    def test_parse_incomplete_task(self):
        content = "- [ ] Do something"
        tasks = parse_tasks(content)
        assert len(tasks) == 1
        assert tasks[0].text == "Do something"
        assert tasks[0].complete is False
        assert tasks[0].line_number == 1

    def test_parse_complete_task(self):
        content = "- [x] Done task"
        tasks = parse_tasks(content)
        assert len(tasks) == 1
        assert tasks[0].text == "Done task"
        assert tasks[0].complete is True

    def test_parse_uppercase_x(self):
        content = "- [X] Done with uppercase"
        tasks = parse_tasks(content)
        assert len(tasks) == 1
        assert tasks[0].complete is True

    def test_parse_multiple_tasks(self):
        content = """# Tasks
- [ ] First task
- [x] Second task
- [ ] Third task
"""
        tasks = parse_tasks(content)
        assert len(tasks) == 3
        assert tasks[0].text == "First task"
        assert tasks[0].complete is False
        assert tasks[0].line_number == 2
        assert tasks[1].text == "Second task"
        assert tasks[1].complete is True
        assert tasks[1].line_number == 3
        assert tasks[2].text == "Third task"
        assert tasks[2].complete is False
        assert tasks[2].line_number == 4

    def test_parse_with_indentation(self):
        content = "  - [ ] Indented task"
        tasks = parse_tasks(content)
        assert len(tasks) == 1
        assert tasks[0].text == "Indented task"

    def test_parse_empty_content(self):
        tasks = parse_tasks("")
        assert tasks == []

    def test_parse_no_tasks(self):
        content = """# Project
Some text without checkboxes.
- Regular list item
"""
        tasks = parse_tasks(content)
        assert tasks == []


class TestCompletionStatus:
    def test_all_incomplete(self):
        tasks = [
            Task("One", False, 1),
            Task("Two", False, 2),
        ]
        completed, total = get_completion_status(tasks)
        assert completed == 0
        assert total == 2

    def test_all_complete(self):
        tasks = [
            Task("One", True, 1),
            Task("Two", True, 2),
        ]
        completed, total = get_completion_status(tasks)
        assert completed == 2
        assert total == 2

    def test_mixed(self):
        tasks = [
            Task("One", True, 1),
            Task("Two", False, 2),
            Task("Three", True, 3),
        ]
        completed, total = get_completion_status(tasks)
        assert completed == 2
        assert total == 3

    def test_empty(self):
        completed, total = get_completion_status([])
        assert completed == 0
        assert total == 0


class TestIsAllComplete:
    def test_all_complete(self):
        tasks = [Task("One", True, 1), Task("Two", True, 2)]
        assert is_all_complete(tasks) is True

    def test_some_incomplete(self):
        tasks = [Task("One", True, 1), Task("Two", False, 2)]
        assert is_all_complete(tasks) is False

    def test_empty_is_complete(self):
        assert is_all_complete([]) is True


class TestGetNextIncompleteTask:
    def test_gets_first_incomplete(self):
        tasks = [
            Task("One", True, 1),
            Task("Two", False, 2),
            Task("Three", False, 3),
        ]
        next_task = get_next_incomplete_task(tasks)
        assert next_task is not None
        assert next_task.text == "Two"

    def test_none_when_all_complete(self):
        tasks = [Task("One", True, 1), Task("Two", True, 2)]
        assert get_next_incomplete_task(tasks) is None

    def test_none_when_empty(self):
        assert get_next_incomplete_task([]) is None
