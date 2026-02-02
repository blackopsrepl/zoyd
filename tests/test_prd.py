"""Tests for PRD parsing."""

import pytest
from pathlib import Path

from zoyd.prd import (
    Task,
    ValidationWarning,
    parse_tasks,
    get_completion_status,
    is_all_complete,
    get_next_incomplete_task,
    validate_prd,
    edit_task,
    add_task,
    delete_task,
    move_task,
    toggle_task,
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


class TestEditTask:
    """Tests for edit_task function."""

    def test_edit_task_text_preserve_incomplete(self, tmp_path):
        """Edit task text and preserve incomplete state."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("# Tasks\n- [ ] Old task\n- [x] Completed task\n")

        result = edit_task(prd_file, 2, "Updated task")

        assert result.text == "Updated task"
        assert result.complete is False
        assert result.line_number == 2

        content = prd_file.read_text()
        assert "- [ ] Updated task" in content
        assert "- [ ] Old task" not in content
        assert "- [x] Completed task" in content

    def test_edit_task_text_preserve_complete(self, tmp_path):
        """Edit task text and preserve complete state."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] First\n- [x] Second\n")

        result = edit_task(prd_file, 2, "Updated second")

        assert result.complete is True
        content = prd_file.read_text()
        assert "- [x] Updated second" in content

    def test_edit_task_file_not_found(self, tmp_path):
        """Raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            edit_task(tmp_path / "nonexistent.md", 1, "Task")

    def test_edit_task_invalid_line(self, tmp_path):
        """Raise ValueError for invalid line number."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] Task\n")

        with pytest.raises(ValueError, match="Invalid line number"):
            edit_task(prd_file, 0, "Task")

        with pytest.raises(ValueError, match="Invalid line number"):
            edit_task(prd_file, 5, "Task")

    def test_edit_non_task_line(self, tmp_path):
        """Raise ValueError for non-task line."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("# Header\n- [ ] Task\n")

        with pytest.raises(ValueError, match="not a task checkbox"):
            edit_task(prd_file, 1, "Task")


class TestAddTask:
    """Tests for add_task function."""

    def test_add_task_incomplete(self, tmp_path):
        """Add incomplete task after line."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] First\n")

        result = add_task(prd_file, 1, "Second task")

        assert result.text == "Second task"
        assert result.complete is False
        assert result.line_number == 2

        content = prd_file.read_text()
        lines = content.strip().split("\n")
        assert lines[0] == "- [ ] First"
        assert lines[1] == "- [ ] Second task"

    def test_add_task_complete(self, tmp_path):
        """Add complete task after line."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] First\n")

        result = add_task(prd_file, 1, "Second", complete=True)

        assert result.complete is True
        content = prd_file.read_text()
        assert "- [x] Second" in content

    def test_add_task_at_beginning(self, tmp_path):
        """Add task at beginning (after line 0)."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] First\n- [ ] Second\n")

        result = add_task(prd_file, 0, "New first")

        assert result.line_number == 1
        content = prd_file.read_text()
        lines = content.strip().split("\n")
        assert lines[0] == "- [ ] New first"
        assert lines[1] == "- [ ] First"

    def test_add_task_file_not_found(self, tmp_path):
        """Raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            add_task(tmp_path / "nonexistent.md", 0, "Task")

    def test_add_task_invalid_line(self, tmp_path):
        """Raise ValueError for invalid line number."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] Task\n")

        with pytest.raises(ValueError):
            add_task(prd_file, 5, "New task")


class TestDeleteTask:
    """Tests for delete_task function."""

    def test_delete_task(self, tmp_path):
        """Delete task at line."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] First\n- [x] Second\n- [ ] Third\n")

        result = delete_task(prd_file, 2)

        assert result.text == "Second"
        assert result.complete is True
        assert result.line_number == 2  # Original line number

        content = prd_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 2
        assert "- [ ] First" in content
        assert "- [ ] Third" in content
        assert "- [x] Second" not in content

    def test_delete_only_task(self, tmp_path):
        """Delete the only task in file."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] Only task\n")

        result = delete_task(prd_file, 1)

        assert result.text == "Only task"
        content = prd_file.read_text().strip()
        assert content == ""

    def test_delete_task_file_not_found(self, tmp_path):
        """Raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            delete_task(tmp_path / "nonexistent.md", 1)

    def test_delete_task_invalid_line(self, tmp_path):
        """Raise ValueError for invalid line number."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] Task\n")

        with pytest.raises(ValueError, match="Invalid line number"):
            delete_task(prd_file, 0)

        with pytest.raises(ValueError, match="Invalid line number"):
            delete_task(prd_file, 5)

    def test_delete_non_task_line(self, tmp_path):
        """Raise ValueError for non-task line."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("# Header\n- [ ] Task\n")

        with pytest.raises(ValueError, match="not a task checkbox"):
            delete_task(prd_file, 1)


class TestMoveTask:
    """Tests for move_task function."""

    def test_move_task_up(self, tmp_path):
        """Move task to earlier position."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] First\n- [ ] Second\n- [ ] Third\n")

        result = move_task(prd_file, 3, 1)

        assert result.text == "Third"
        assert result.line_number == 1

        content = prd_file.read_text()
        lines = content.strip().split("\n")
        assert lines[0] == "- [ ] Third"
        assert lines[1] == "- [ ] First"
        assert lines[2] == "- [ ] Second"

    def test_move_task_down(self, tmp_path):
        """Move task to later position."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] First\n- [ ] Second\n- [ ] Third\n")

        result = move_task(prd_file, 1, 3)

        assert result.text == "First"
        assert result.line_number == 3

        content = prd_file.read_text()
        lines = content.strip().split("\n")
        assert lines[0] == "- [ ] Second"
        assert lines[1] == "- [ ] Third"
        assert lines[2] == "- [ ] First"

    def test_move_same_line_error(self, tmp_path):
        """Raise ValueError when from and to are the same."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] Task\n")

        with pytest.raises(ValueError, match="cannot be the same"):
            move_task(prd_file, 1, 1)

    def test_move_task_file_not_found(self, tmp_path):
        """Raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            move_task(tmp_path / "nonexistent.md", 1, 2)

    def test_move_task_invalid_line(self, tmp_path):
        """Raise ValueError for invalid line number."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] First\n- [ ] Second\n")

        with pytest.raises(ValueError, match="Invalid from_line"):
            move_task(prd_file, 0, 1)

        with pytest.raises(ValueError, match="Invalid from_line"):
            move_task(prd_file, 5, 1)

        with pytest.raises(ValueError, match="Invalid to_line"):
            move_task(prd_file, 1, 0)

        with pytest.raises(ValueError, match="Invalid to_line"):
            move_task(prd_file, 1, 5)

    def test_move_non_task_line(self, tmp_path):
        """Raise ValueError for non-task line."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("# Header\n- [ ] Task\n- [ ] Another\n")

        with pytest.raises(ValueError, match="not a task checkbox"):
            move_task(prd_file, 1, 2)


class TestToggleTask:
    """Tests for toggle_task function."""

    def test_toggle_incomplete_to_complete(self, tmp_path):
        """Toggle incomplete task to complete."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] Incomplete task\n")

        result = toggle_task(prd_file, 1)

        assert result.text == "Incomplete task"
        assert result.complete is True

        content = prd_file.read_text()
        assert "- [x] Incomplete task" in content
        assert "- [ ] Incomplete task" not in content

    def test_toggle_complete_to_incomplete(self, tmp_path):
        """Toggle complete task to incomplete."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [x] Complete task\n")

        result = toggle_task(prd_file, 1)

        assert result.text == "Complete task"
        assert result.complete is False

        content = prd_file.read_text()
        assert "- [ ] Complete task" in content
        assert "- [x] Complete task" not in content

    def test_toggle_task_file_not_found(self, tmp_path):
        """Raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            toggle_task(tmp_path / "nonexistent.md", 1)

    def test_toggle_task_invalid_line(self, tmp_path):
        """Raise ValueError for invalid line number."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [ ] Task\n")

        with pytest.raises(ValueError, match="Invalid line number"):
            toggle_task(prd_file, 0)

        with pytest.raises(ValueError, match="Invalid line number"):
            toggle_task(prd_file, 5)

    def test_toggle_non_task_line(self, tmp_path):
        """Raise ValueError for non-task line."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("# Header\n- [ ] Task\n")

        with pytest.raises(ValueError, match="not a task checkbox"):
            toggle_task(prd_file, 1)

    def test_toggle_uppercase_x(self, tmp_path):
        """Toggle task with uppercase X."""
        prd_file = tmp_path / "test.md"
        prd_file.write_text("- [X] Completed task\n")

        result = toggle_task(prd_file, 1)

        assert result.complete is False
        content = prd_file.read_text()
        assert "- [ ] Completed task" in content
