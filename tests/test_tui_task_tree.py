"""Tests for TUI task tree module."""

import pytest

# Skip all tests if rich is not installed
rich = pytest.importorskip("rich")

from zoyd.prd import Task


class TestIcons:
    def test_icons_dict_exists(self):
        from zoyd.tui.task_tree import ICONS

        assert isinstance(ICONS, dict)

    def test_icons_has_all_states(self):
        from zoyd.tui.task_tree import ICONS

        states = ["complete", "pending", "active", "blocked"]
        for state in states:
            assert state in ICONS, f"Missing icon for state: {state}"

    def test_icons_are_styled(self):
        from zoyd.tui.task_tree import ICONS

        # Each icon should have markup tags
        for state, icon in ICONS.items():
            assert "[" in icon and "]" in icon, f"Icon {state} should have style markup"


class TestGetTaskIcon:
    def test_complete_icon(self):
        from zoyd.tui.task_tree import get_task_icon, ICONS

        assert get_task_icon(complete=True) == ICONS["complete"]

    def test_pending_icon(self):
        from zoyd.tui.task_tree import get_task_icon, ICONS

        assert get_task_icon(complete=False) == ICONS["pending"]

    def test_active_icon(self):
        from zoyd.tui.task_tree import get_task_icon, ICONS

        assert get_task_icon(complete=False, active=True) == ICONS["active"]

    def test_blocked_icon(self):
        from zoyd.tui.task_tree import get_task_icon, ICONS

        assert get_task_icon(complete=False, blocked=True) == ICONS["blocked"]

    def test_blocked_takes_precedence(self):
        from zoyd.tui.task_tree import get_task_icon, ICONS

        assert get_task_icon(complete=True, blocked=True) == ICONS["blocked"]
        assert get_task_icon(complete=False, active=True, blocked=True) == ICONS["blocked"]

    def test_complete_takes_precedence_over_active(self):
        from zoyd.tui.task_tree import get_task_icon, ICONS

        assert get_task_icon(complete=True, active=True) == ICONS["complete"]


class TestRenderTaskTree:
    def test_returns_tree(self):
        from rich.tree import Tree

        from zoyd.tui.task_tree import render_task_tree

        tasks = [Task("Test task", False, 1)]
        tree = render_task_tree(tasks)
        assert isinstance(tree, Tree)

    def test_empty_tasks_list(self):
        from zoyd.tui.task_tree import render_task_tree

        tree = render_task_tree([])
        # Should still create tree with just title
        assert tree.label is not None

    def test_custom_title(self):
        from zoyd.tui.task_tree import render_task_tree

        tree = render_task_tree([], title="My Tasks")
        assert "My Tasks" in str(tree.label)

    def test_tasks_added_to_tree(self):
        from rich.console import Console
        from io import StringIO

        from zoyd.tui.task_tree import render_task_tree

        tasks = [
            Task("Task 1", False, 1),
            Task("Task 2", True, 2),
            Task("Task 3", False, 3),
        ]
        tree = render_task_tree(tasks)
        # Render the tree and check all tasks are present
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(tree)
        rendered = output.getvalue()
        assert "Task 1" in rendered
        assert "Task 2" in rendered
        assert "Task 3" in rendered

    def test_active_task_highlighted(self):
        from rich.console import Console
        from io import StringIO

        from zoyd.tui.task_tree import render_task_tree

        tasks = [Task("Task 1", False, 1), Task("Task 2", False, 2)]
        active = tasks[0]
        tree = render_task_tree(tasks, active_task=active)

        # Render to string and check active icon is present
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(tree)
        rendered = output.getvalue()
        # Active task should have the fisheye symbol
        assert "\u25c9" in rendered

    def test_blocked_tasks_marked(self):
        from rich.console import Console
        from io import StringIO

        from zoyd.tui.task_tree import render_task_tree

        tasks = [Task("Task 1", False, 1), Task("Task 2", False, 2)]
        tree = render_task_tree(tasks, blocked_tasks={1})

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(tree)
        rendered = output.getvalue()
        # Blocked task should have the X symbol
        assert "\u2717" in rendered

    def test_show_line_numbers(self):
        from rich.console import Console
        from io import StringIO

        from zoyd.tui.task_tree import render_task_tree

        tasks = [Task("Test task", False, 42)]
        tree = render_task_tree(tasks, show_line_numbers=True)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(tree)
        rendered = output.getvalue()
        assert "L42" in rendered

    def test_hide_line_numbers_by_default(self):
        from rich.console import Console
        from io import StringIO

        from zoyd.tui.task_tree import render_task_tree

        tasks = [Task("Test task", False, 42)]
        tree = render_task_tree(tasks)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(tree)
        rendered = output.getvalue()
        assert "L42" not in rendered


class TestRenderTaskSummary:
    def test_basic_summary(self):
        from zoyd.tui.task_tree import render_task_summary

        summary = render_task_summary(3, 10)
        assert "3/10" in summary
        assert "tasks" in summary

    def test_summary_with_percentage(self):
        from zoyd.tui.task_tree import render_task_summary

        summary = render_task_summary(5, 10, show_percentage=True)
        assert "50%" in summary

    def test_summary_without_percentage(self):
        from zoyd.tui.task_tree import render_task_summary

        summary = render_task_summary(5, 10, show_percentage=False)
        assert "%" not in summary
        assert "5/10" in summary

    def test_zero_total_tasks(self):
        from zoyd.tui.task_tree import render_task_summary

        summary = render_task_summary(0, 0)
        assert summary == "No tasks"

    def test_all_complete(self):
        from zoyd.tui.task_tree import render_task_summary

        summary = render_task_summary(10, 10)
        assert "10/10" in summary
        assert "100%" in summary

    def test_none_complete(self):
        from zoyd.tui.task_tree import render_task_summary

        summary = render_task_summary(0, 5)
        assert "0/5" in summary
        assert "0%" in summary


class TestPrintTaskTree:
    def test_prints_tree(self):
        from rich.console import Console
        from io import StringIO

        from zoyd.tui.task_tree import print_task_tree

        tasks = [Task("Test task", True, 1)]
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        print_task_tree(console, tasks)

        rendered = output.getvalue()
        assert "Test task" in rendered

    def test_prints_summary_by_default(self):
        from rich.console import Console
        from io import StringIO
        import re

        from zoyd.tui.task_tree import print_task_tree

        tasks = [Task("Task 1", True, 1), Task("Task 2", False, 2)]
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        print_task_tree(console, tasks)

        rendered = output.getvalue()
        # Strip ANSI codes for reliable assertion
        plain = re.sub(r'\x1b\[[0-9;]*m', '', rendered)
        assert "1/2" in plain

    def test_hide_summary(self):
        from rich.console import Console
        from io import StringIO

        from zoyd.tui.task_tree import print_task_tree

        tasks = [Task("Task 1", True, 1), Task("Task 2", False, 2)]
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        print_task_tree(console, tasks, show_summary=False)

        rendered = output.getvalue()
        # Should still have task content
        assert "Task 1" in rendered
        # But no summary
        assert "1/2" not in rendered

    def test_empty_tasks_no_summary(self):
        from rich.console import Console
        from io import StringIO

        from zoyd.tui.task_tree import print_task_tree

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        print_task_tree(console, [])

        rendered = output.getvalue()
        # Should just have the title, no crash
        assert "Tasks" in rendered


class TestModuleExports:
    def test_render_task_tree_importable(self):
        from zoyd.tui.task_tree import render_task_tree

        assert callable(render_task_tree)

    def test_get_task_icon_importable(self):
        from zoyd.tui.task_tree import get_task_icon

        assert callable(get_task_icon)

    def test_print_task_tree_importable(self):
        from zoyd.tui.task_tree import print_task_tree

        assert callable(print_task_tree)

    def test_render_task_summary_importable(self):
        from zoyd.tui.task_tree import render_task_summary

        assert callable(render_task_summary)

    def test_icons_importable(self):
        from zoyd.tui.task_tree import ICONS

        assert isinstance(ICONS, dict)
