"""Tests for TUI status module."""

import pytest

# Skip all tests if rich is not installed
rich = pytest.importorskip("rich")

from io import StringIO
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

from zoyd.prd import Task


class TestCreateProgressBar:
    def test_returns_progress(self):
        from zoyd.tui.status import create_progress_bar

        progress = create_progress_bar(5, 10)
        assert isinstance(progress, Progress)

    def test_zero_total(self):
        from zoyd.tui.status import create_progress_bar

        progress = create_progress_bar(0, 0)
        assert isinstance(progress, Progress)

    def test_all_complete(self):
        from zoyd.tui.status import create_progress_bar

        progress = create_progress_bar(10, 10)
        assert isinstance(progress, Progress)

    def test_custom_description(self):
        from zoyd.tui.status import create_progress_bar

        progress = create_progress_bar(5, 10, description="Tasks")
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(progress)
        rendered = output.getvalue()
        assert "Tasks" in rendered

    def test_displays_count(self):
        from zoyd.tui.status import create_progress_bar

        progress = create_progress_bar(3, 7)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(progress)
        rendered = output.getvalue()
        # Should show count in parentheses
        assert "3/7" in rendered

    def test_displays_percentage(self):
        from zoyd.tui.status import create_progress_bar

        progress = create_progress_bar(5, 10)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(progress)
        rendered = output.getvalue()
        assert "50%" in rendered


class TestCreateStatusTable:
    def test_returns_table(self):
        from zoyd.tui.status import create_status_table

        table = create_status_table()
        assert isinstance(table, Table)

    def test_with_prd_path(self):
        from zoyd.tui.status import create_status_table

        table = create_status_table(prd_path="test.md")
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(table)
        rendered = output.getvalue()
        assert "PRD" in rendered
        assert "test.md" in rendered

    def test_with_path_object(self):
        from zoyd.tui.status import create_status_table

        table = create_status_table(prd_path=Path("test.md"))
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(table)
        rendered = output.getvalue()
        assert "test.md" in rendered

    def test_with_iterations(self):
        from zoyd.tui.status import create_status_table

        table = create_status_table(iterations=5)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(table)
        rendered = output.getvalue()
        assert "Iterations" in rendered
        assert "5" in rendered

    def test_zero_iterations_hidden(self):
        from zoyd.tui.status import create_status_table

        table = create_status_table(iterations=0)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(table)
        rendered = output.getvalue()
        assert "Iterations" not in rendered

    def test_status_complete(self):
        from zoyd.tui.status import create_status_table

        table = create_status_table(status="complete")
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(table)
        rendered = output.getvalue()
        assert "COMPLETE" in rendered

    def test_status_in_progress(self):
        from zoyd.tui.status import create_status_table

        table = create_status_table(status="in_progress")
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(table)
        rendered = output.getvalue()
        assert "IN PROGRESS" in rendered

    def test_with_next_task(self):
        from zoyd.tui.status import create_status_table

        table = create_status_table(status="in_progress", next_task="Fix the bug")
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(table)
        rendered = output.getvalue()
        assert "Next task" in rendered
        assert "Fix the bug" in rendered

    def test_next_task_hidden_when_complete(self):
        from zoyd.tui.status import create_status_table

        table = create_status_table(status="complete", next_task="Should not show")
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(table)
        rendered = output.getvalue()
        assert "Next task" not in rendered


class TestRenderStatus:
    def test_returns_panel(self):
        from zoyd.tui.status import render_status

        tasks = [Task("Test task", False, 1)]
        panel = render_status(tasks)
        assert isinstance(panel, Panel)

    def test_empty_tasks(self):
        from zoyd.tui.status import render_status

        panel = render_status([])
        assert isinstance(panel, Panel)

    def test_contains_task_tree(self):
        from zoyd.tui.status import render_status

        tasks = [
            Task("Task 1", True, 1),
            Task("Task 2", False, 2),
        ]
        panel = render_status(tasks)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        assert "Task 1" in rendered
        assert "Task 2" in rendered

    def test_contains_progress_bar(self):
        from zoyd.tui.status import render_status

        tasks = [
            Task("Task 1", True, 1),
            Task("Task 2", False, 2),
        ]
        panel = render_status(tasks)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        # Should show percentage
        assert "50%" in rendered

    def test_hide_tree(self):
        from zoyd.tui.status import render_status

        tasks = [Task("Task 1", True, 1)]
        panel = render_status(tasks, show_tree=False)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        # Should still show status info but not tree structure
        assert "Status" in rendered

    def test_hide_progress(self):
        from zoyd.tui.status import render_status

        tasks = [Task("Task 1", True, 1)]
        panel = render_status(tasks, show_progress=False)
        # Should not raise error
        assert isinstance(panel, Panel)

    def test_with_prd_path(self):
        from zoyd.tui.status import render_status

        tasks = [Task("Test", False, 1)]
        panel = render_status(tasks, prd_path="my.md")
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        assert "my.md" in rendered

    def test_with_iterations(self):
        from zoyd.tui.status import render_status

        tasks = [Task("Test", False, 1)]
        panel = render_status(tasks, iterations=5)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        assert "5" in rendered

    def test_shows_next_task(self):
        from zoyd.tui.status import render_status

        tasks = [
            Task("Done", True, 1),
            Task("Next one", False, 2),
        ]
        panel = render_status(tasks)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        assert "Next one" in rendered

    def test_complete_status(self):
        from zoyd.tui.status import render_status

        tasks = [
            Task("Done 1", True, 1),
            Task("Done 2", True, 2),
        ]
        panel = render_status(tasks)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        assert "COMPLETE" in rendered

    def test_with_line_numbers(self):
        from zoyd.tui.status import render_status

        tasks = [Task("Test task", False, 42)]
        panel = render_status(tasks, show_line_numbers=True)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        assert "L42" in rendered

    def test_with_active_task(self):
        from zoyd.tui.status import render_status

        tasks = [Task("Active task", False, 1)]
        panel = render_status(tasks, active_task=tasks[0])
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        # Should show active icon (fisheye)
        assert "\u25c9" in rendered

    def test_with_blocked_tasks(self):
        from zoyd.tui.status import render_status

        tasks = [Task("Blocked task", False, 1)]
        panel = render_status(tasks, blocked_tasks={1})
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        # Should show blocked icon (X mark)
        assert "\u2717" in rendered

    def test_panel_has_title(self):
        from zoyd.tui.status import render_status

        tasks = []
        panel = render_status(tasks)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel)
        rendered = output.getvalue()
        assert "Zoyd Status" in rendered


class TestPrintStatus:
    def test_prints_to_console(self):
        from zoyd.tui.status import print_status

        tasks = [Task("Test task", True, 1)]
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        print_status(console, tasks)

        rendered = output.getvalue()
        assert "Test task" in rendered

    def test_with_all_options(self):
        from zoyd.tui.status import print_status

        tasks = [
            Task("Complete", True, 1),
            Task("Pending", False, 2),
        ]
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        print_status(
            console,
            tasks,
            prd_path="test.md",
            iterations=3,
            show_tree=True,
            show_progress=True,
            show_line_numbers=True,
        )

        rendered = output.getvalue()
        assert "test.md" in rendered
        assert "Complete" in rendered
        assert "Pending" in rendered


class TestGetStatusSummary:
    def test_basic_summary(self):
        from zoyd.tui.status import get_status_summary

        tasks = [
            Task("Done", True, 1),
            Task("Pending", False, 2),
        ]
        summary = get_status_summary(tasks)

        assert summary["completed"] == 1
        assert summary["total"] == 2
        assert summary["percentage"] == 50.0
        assert summary["is_complete"] is False

    def test_all_complete(self):
        from zoyd.tui.status import get_status_summary

        tasks = [
            Task("Done 1", True, 1),
            Task("Done 2", True, 2),
        ]
        summary = get_status_summary(tasks)

        assert summary["completed"] == 2
        assert summary["total"] == 2
        assert summary["percentage"] == 100.0
        assert summary["is_complete"] is True

    def test_none_complete(self):
        from zoyd.tui.status import get_status_summary

        tasks = [
            Task("Pending 1", False, 1),
            Task("Pending 2", False, 2),
        ]
        summary = get_status_summary(tasks)

        assert summary["completed"] == 0
        assert summary["total"] == 2
        assert summary["percentage"] == 0.0
        assert summary["is_complete"] is False

    def test_empty_tasks(self):
        from zoyd.tui.status import get_status_summary

        summary = get_status_summary([])

        assert summary["completed"] == 0
        assert summary["total"] == 0
        assert summary["percentage"] == 0.0
        assert summary["is_complete"] is False


class TestModuleExports:
    def test_render_status_importable(self):
        from zoyd.tui.status import render_status

        assert callable(render_status)

    def test_print_status_importable(self):
        from zoyd.tui.status import print_status

        assert callable(print_status)

    def test_create_progress_bar_importable(self):
        from zoyd.tui.status import create_progress_bar

        assert callable(create_progress_bar)

    def test_create_status_table_importable(self):
        from zoyd.tui.status import create_status_table

        assert callable(create_status_table)

    def test_get_status_summary_importable(self):
        from zoyd.tui.status import get_status_summary

        assert callable(get_status_summary)

    def test_exports_from_tui_init(self):
        from zoyd.tui import (
            render_status,
            print_status,
            get_status_summary,
        )

        assert callable(render_status)
        assert callable(print_status)
        assert callable(get_status_summary)
