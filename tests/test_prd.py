"""Tests for PRD parsing."""

import pytest

from zoyd.prd import (
    Task,
    ValidationWarning,
    parse_tasks,
    get_completion_status,
    is_all_complete,
    get_next_incomplete_task,
    validate_prd,
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


class TestValidatePrd:
    """Tests for PRD validation."""

    def test_valid_prd_no_warnings(self):
        """Valid PRD should have no warnings."""
        content = """# Project
- [ ] First task
- [x] Second task
- [ ] Third task with details
"""
        warnings = validate_prd(content)
        assert len(warnings) == 0

    def test_empty_task_text(self):
        """Empty task text should generate warning."""
        content = "- [ ]"
        warnings = validate_prd(content)
        assert len(warnings) == 1
        assert warnings[0].line_number == 1
        assert "Empty task text" in warnings[0].message

    def test_empty_task_text_with_whitespace(self):
        """Task with only whitespace after checkbox should warn."""
        content = "- [ ]   "
        warnings = validate_prd(content)
        assert len(warnings) == 1
        assert "Empty task text" in warnings[0].message

    def test_missing_space_inside_brackets(self):
        """Missing space inside brackets should warn."""
        content = "-[]"
        warnings = validate_prd(content)
        assert len(warnings) == 1
        assert "Missing space inside checkbox" in warnings[0].message

    def test_missing_space_after_checkbox(self):
        """Missing space after checkbox should warn."""
        content = "- [ ]text without space"
        warnings = validate_prd(content)
        assert len(warnings) == 1
        assert "Missing space after checkbox" in warnings[0].message

    def test_invalid_bracket_variations(self):
        """Parentheses or angle brackets should warn."""
        content = "-( ) task"
        warnings = validate_prd(content)
        assert len(warnings) == 1
        assert "Invalid checkbox format" in warnings[0].message

    def test_extra_characters_in_brackets(self):
        """Extra characters inside brackets should warn."""
        content = "- [xx] task"
        warnings = validate_prd(content)
        assert len(warnings) == 1
        assert "Invalid checkbox format" in warnings[0].message

    def test_missing_closing_bracket(self):
        """Missing closing bracket should warn."""
        content = "- [ task without closing"
        warnings = validate_prd(content)
        assert len(warnings) == 1
        assert "Missing closing bracket" in warnings[0].message

    def test_multiple_warnings(self):
        """Multiple issues should generate multiple warnings."""
        content = """# Tasks
- [ ]
- []
- [ ]valid task
"""
        warnings = validate_prd(content)
        assert len(warnings) == 3  # Empty text, missing space inside, missing space after

    def test_valid_indented_checkbox(self):
        """Indented valid checkboxes should not warn."""
        content = "  - [ ] Indented task"
        warnings = validate_prd(content)
        assert len(warnings) == 0

    def test_uppercase_x_is_valid(self):
        """Uppercase X in checkbox is valid."""
        content = "- [X] Completed task"
        warnings = validate_prd(content)
        assert len(warnings) == 0

    def test_warning_contains_line_content(self):
        """Warnings should include the original line content."""
        content = "- [] malformed"
        warnings = validate_prd(content)
        assert len(warnings) == 1
        assert warnings[0].line_content == "- [] malformed"

    def test_regular_list_items_no_warning(self):
        """Regular list items (not checkboxes) should not warn."""
        content = """- Regular item
- Another item
* Starred item
"""
        warnings = validate_prd(content)
        assert len(warnings) == 0
