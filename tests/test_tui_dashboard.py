"""Tests for the Zoyd TUI dashboard module."""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

import pytest

rich = pytest.importorskip("rich")

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel

from zoyd.prd import Task
from zoyd.tui.dashboard import (
    LAYOUT_BANNER,
    LAYOUT_BODY,
    LAYOUT_HISTORY,
    LAYOUT_MAIN,
    LAYOUT_OUTPUT,
    LAYOUT_PROGRESS,
    LAYOUT_SIDEBAR,
    LAYOUT_STATUS,
    LAYOUT_TASKS,
    Dashboard,
    DashboardState,
    create_dashboard,
)
from zoyd.tui.events import Event, EventEmitter, EventType


class TestDashboardState:
    """Tests for DashboardState class."""

    def test_default_values(self) -> None:
        """Test that state has sensible defaults."""
        state = DashboardState()

        # Configuration defaults
        assert state.prd_path == ""
        assert state.progress_path == ""
        assert state.model is None
        assert state.max_iterations == 10
        assert state.max_cost is None

        # Progress defaults
        assert state.iteration == 0
        assert state.cost == 0.0
        assert state.tasks_completed == 0
        assert state.tasks_total == 0

        # Task defaults
        assert state.tasks == []
        assert state.active_task is None
        assert state.blocked_tasks == set()

        # Output defaults
        assert len(state.output_lines) == 0
        assert state.current_output == ""

        # Status defaults
        assert state.status_message == "Initializing..."
        assert state.is_running is False

        # Error defaults
        assert state.error_message is None
        assert state.error_details is None

        # History defaults
        assert state.iteration_history == []
        assert state.max_history_items == 10

    def test_reset_error(self) -> None:
        """Test clearing error state."""
        state = DashboardState()
        state.error_message = "Something went wrong"
        state.error_details = "Stack trace here"

        state.reset_error()

        assert state.error_message is None
        assert state.error_details is None

    def test_output_lines_deque_limit(self) -> None:
        """Test that output_lines has a max length."""
        state = DashboardState()

        # Add more than maxlen lines
        for i in range(100):
            state.output_lines.append(f"Line {i}")

        # Should be limited to maxlen (50)
        assert len(state.output_lines) == 50
        # Oldest lines should be dropped
        assert "Line 0" not in state.output_lines
        assert "Line 99" in state.output_lines

    def test_add_iteration_to_history(self) -> None:
        """Test adding an iteration to history."""
        state = DashboardState()
        state.add_iteration_to_history(
            1, status="success", cost=0.05, duration=10.5, task="Test task"
        )

        assert len(state.iteration_history) == 1
        assert state.iteration_history[0]["iteration"] == 1
        assert state.iteration_history[0]["status"] == "success"
        assert state.iteration_history[0]["cost"] == 0.05
        assert state.iteration_history[0]["duration"] == 10.5
        assert state.iteration_history[0]["task"] == "Test task"

    def test_add_iteration_to_history_max_items(self) -> None:
        """Test that history respects max items limit."""
        state = DashboardState()
        state.max_history_items = 5

        for i in range(10):
            state.add_iteration_to_history(i + 1, status="success")

        assert len(state.iteration_history) == 5
        # Should keep the most recent items
        assert state.iteration_history[0]["iteration"] == 6
        assert state.iteration_history[4]["iteration"] == 10

    def test_update_iteration_in_history(self) -> None:
        """Test updating an iteration in history."""
        state = DashboardState()
        state.add_iteration_to_history(1, status="running")
        state.update_iteration_in_history(1, status="success", duration=15.0)

        assert state.iteration_history[0]["status"] == "success"
        assert state.iteration_history[0]["duration"] == 15.0

    def test_update_iteration_in_history_partial(self) -> None:
        """Test partial update preserves other fields."""
        state = DashboardState()
        state.add_iteration_to_history(1, status="running", cost=0.01)
        state.update_iteration_in_history(1, status="success")

        assert state.iteration_history[0]["status"] == "success"
        assert state.iteration_history[0]["cost"] == 0.01  # Unchanged

    def test_update_nonexistent_iteration(self) -> None:
        """Test updating nonexistent iteration does nothing."""
        state = DashboardState()
        state.add_iteration_to_history(1, status="running")
        state.update_iteration_in_history(999, status="success")

        assert state.iteration_history[0]["status"] == "running"

    # Commit log state tests
    def test_commit_log_defaults(self) -> None:
        """Test commit log defaults."""
        state = DashboardState()
        assert state.commit_log == []
        assert state.max_commit_items == 10

    def test_add_commit_to_log(self) -> None:
        """Test adding a commit to the log."""
        state = DashboardState()
        state.add_commit_to_log(
            iteration=1, message="feat: add new feature", commit_hash="abc123def"
        )

        assert len(state.commit_log) == 1
        assert state.commit_log[0]["iteration"] == 1
        assert state.commit_log[0]["message"] == "feat: add new feature"
        assert state.commit_log[0]["hash"] == "abc123def"

    def test_add_commit_to_log_without_hash(self) -> None:
        """Test adding a commit without hash."""
        state = DashboardState()
        state.add_commit_to_log(iteration=1, message="Test commit")

        assert state.commit_log[0]["hash"] is None

    def test_add_commit_to_log_max_items(self) -> None:
        """Test that commit log respects max items limit."""
        state = DashboardState()
        state.max_commit_items = 3

        for i in range(5):
            state.add_commit_to_log(iteration=i + 1, message=f"Commit {i + 1}")

        assert len(state.commit_log) == 3
        # Should keep the most recent items
        assert state.commit_log[0]["iteration"] == 3
        assert state.commit_log[2]["iteration"] == 5


class TestDashboard:
    """Tests for Dashboard class."""

    @pytest.fixture
    def console(self) -> Console:
        """Create a test console."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def dashboard(self, console: Console) -> Dashboard:
        """Create a test dashboard."""
        return Dashboard(console)

    def test_init_defaults(self, dashboard: Dashboard) -> None:
        """Test dashboard initialization with defaults."""
        assert dashboard.compact is False
        assert dashboard.refresh_per_second == 4
        assert isinstance(dashboard.state, DashboardState)
        assert dashboard._live is None

    def test_init_compact(self, console: Console) -> None:
        """Test dashboard initialization with compact mode."""
        dashboard = Dashboard(console, compact=True)
        assert dashboard.compact is True

    def test_init_custom_refresh(self, console: Console) -> None:
        """Test dashboard initialization with custom refresh rate."""
        dashboard = Dashboard(console, refresh_per_second=10)
        assert dashboard.refresh_per_second == 10

    def test_layout_structure(self, dashboard: Dashboard) -> None:
        """Test that the layout has the correct structure."""
        layout = dashboard._layout

        # Check root layout exists
        assert layout.name == "root"

        # Check main sections exist
        assert LAYOUT_BANNER in [c.name for c in layout.children]
        assert LAYOUT_BODY in [c.name for c in layout.children]

    def test_layout_sections(self, dashboard: Dashboard) -> None:
        """Test that all layout sections are accessible."""
        layout = dashboard._layout

        # All named sections should be accessible
        sections = [
            LAYOUT_BANNER,
            LAYOUT_BODY,
            LAYOUT_MAIN,
            LAYOUT_SIDEBAR,
            LAYOUT_STATUS,
            LAYOUT_OUTPUT,
            LAYOUT_HISTORY,
            LAYOUT_TASKS,
            LAYOUT_PROGRESS,
        ]

        for section in sections:
            # Should not raise KeyError
            assert layout[section] is not None


class TestDashboardRendering:
    """Tests for Dashboard rendering methods."""

    @pytest.fixture
    def console(self) -> Console:
        """Create a test console."""
        return Console(file=StringIO(), force_terminal=True, width=120, height=40)

    @pytest.fixture
    def dashboard(self, console: Console) -> Dashboard:
        """Create a test dashboard."""
        return Dashboard(console)

    def test_render_banner(self, dashboard: Dashboard) -> None:
        """Test banner rendering."""
        result = dashboard._render_banner()
        assert isinstance(result, Panel)

    def test_render_banner_running(self, dashboard: Dashboard) -> None:
        """Test banner rendering when running."""
        dashboard.state.is_running = True
        result = dashboard._render_banner()
        assert isinstance(result, Panel)

    def test_render_banner_error(self, dashboard: Dashboard) -> None:
        """Test banner rendering with error."""
        dashboard.state.error_message = "Test error"
        result = dashboard._render_banner()
        assert isinstance(result, Panel)

    def test_render_status(self, dashboard: Dashboard) -> None:
        """Test status rendering."""
        dashboard.state.prd_path = "test.md"
        dashboard.state.iteration = 5
        result = dashboard._render_status()
        assert isinstance(result, Panel)

    def test_render_tasks_empty(self, dashboard: Dashboard) -> None:
        """Test tasks rendering with no tasks."""
        result = dashboard._render_tasks()
        assert isinstance(result, Panel)

    def test_render_tasks_with_tasks(self, dashboard: Dashboard) -> None:
        """Test tasks rendering with tasks."""
        dashboard.state.tasks = [
            Task(text="Task 1", complete=True, line_number=1),
            Task(text="Task 2", complete=False, line_number=2),
        ]
        dashboard.state.tasks_total = 2
        dashboard.state.tasks_completed = 1
        result = dashboard._render_tasks()
        assert isinstance(result, Panel)

    def test_render_output_empty(self, dashboard: Dashboard) -> None:
        """Test output rendering with no output."""
        result = dashboard._render_output()
        assert isinstance(result, Panel)

    def test_render_output_with_content(self, dashboard: Dashboard) -> None:
        """Test output rendering with content."""
        dashboard.state.current_output = "Hello, World!"
        result = dashboard._render_output()
        assert isinstance(result, Panel)

    def test_render_output_with_logs(self, dashboard: Dashboard) -> None:
        """Test output rendering with log lines."""
        dashboard.state.output_lines.append("Log line 1")
        dashboard.state.output_lines.append("Log line 2")
        result = dashboard._render_output()
        assert isinstance(result, Panel)

    def test_render_output_with_error(self, dashboard: Dashboard) -> None:
        """Test output rendering with error state."""
        dashboard.state.error_message = "Something went wrong"
        dashboard.state.error_details = "Details here"
        result = dashboard._render_output()
        assert isinstance(result, Panel)

    def test_render_progress(self, dashboard: Dashboard) -> None:
        """Test progress rendering."""
        dashboard.state.tasks_completed = 5
        dashboard.state.tasks_total = 10
        dashboard.state.iteration = 3
        dashboard.state.max_iterations = 10
        result = dashboard._render_progress()
        assert isinstance(result, Panel)

    def test_render_history_empty(self, dashboard: Dashboard) -> None:
        """Test history rendering with no history."""
        result = dashboard._render_history()
        assert isinstance(result, Panel)

    def test_render_history_with_items(self, dashboard: Dashboard) -> None:
        """Test history rendering with items."""
        dashboard.state.add_iteration_to_history(
            1, status="success", cost=0.05, duration=10.5
        )
        dashboard.state.add_iteration_to_history(
            2, status="failed", cost=0.03, duration=5.0
        )
        result = dashboard._render_history()
        assert isinstance(result, Panel)

    def test_render_commits_empty(self, dashboard: Dashboard) -> None:
        """Test commits rendering with no commits."""
        result = dashboard._render_commits()
        assert isinstance(result, Panel)

    def test_render_commits_with_items(self, dashboard: Dashboard) -> None:
        """Test commits rendering with items."""
        dashboard.state.add_commit_to_log(
            iteration=1, message="feat: add feature", commit_hash="abc123d"
        )
        dashboard.state.add_commit_to_log(
            iteration=2, message="fix: bug fix", commit_hash="def456e"
        )
        result = dashboard._render_commits()
        assert isinstance(result, Panel)

    def test_full_render(self, dashboard: Dashboard) -> None:
        """Test rendering the complete dashboard."""
        result = dashboard._render()
        assert isinstance(result, Layout)


class TestDashboardStateUpdates:
    """Tests for Dashboard state update methods."""

    @pytest.fixture
    def console(self) -> Console:
        """Create a test console."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def dashboard(self, console: Console) -> Dashboard:
        """Create a test dashboard."""
        return Dashboard(console)

    def test_set_config(self, dashboard: Dashboard) -> None:
        """Test setting configuration."""
        result = dashboard.set_config(
            prd_path="test.md",
            progress_path="progress.txt",
            model="opus",
            max_iterations=20,
            max_cost=5.0,
        )

        assert result is dashboard  # Method chaining
        assert dashboard.state.prd_path == "test.md"
        assert dashboard.state.progress_path == "progress.txt"
        assert dashboard.state.model == "opus"
        assert dashboard.state.max_iterations == 20
        assert dashboard.state.max_cost == 5.0

    def test_set_tasks(self, dashboard: Dashboard) -> None:
        """Test setting tasks."""
        tasks = [
            Task(text="Task 1", complete=True, line_number=1),
            Task(text="Task 2", complete=False, line_number=2),
            Task(text="Task 3", complete=False, line_number=3),
        ]

        result = dashboard.set_tasks(tasks)

        assert result is dashboard
        assert dashboard.state.tasks == tasks
        assert dashboard.state.tasks_total == 3
        assert dashboard.state.tasks_completed == 1

    def test_set_iteration(self, dashboard: Dashboard) -> None:
        """Test setting iteration."""
        result = dashboard.set_iteration(5)

        assert result is dashboard
        assert dashboard.state.iteration == 5

    def test_set_cost(self, dashboard: Dashboard) -> None:
        """Test setting cost."""
        result = dashboard.set_cost(1.234)

        assert result is dashboard
        assert dashboard.state.cost == 1.234

    def test_set_active_task(self, dashboard: Dashboard) -> None:
        """Test setting active task."""
        task = Task(text="Active task", complete=False, line_number=5)
        result = dashboard.set_active_task(task)

        assert result is dashboard
        assert dashboard.state.active_task is task

    def test_set_active_task_none(self, dashboard: Dashboard) -> None:
        """Test clearing active task."""
        dashboard.state.active_task = Task(text="Old task", complete=False, line_number=1)
        result = dashboard.set_active_task(None)

        assert result is dashboard
        assert dashboard.state.active_task is None

    def test_add_blocked_task(self, dashboard: Dashboard) -> None:
        """Test adding blocked task."""
        result = dashboard.add_blocked_task(10)

        assert result is dashboard
        assert 10 in dashboard.state.blocked_tasks

    def test_set_running(self, dashboard: Dashboard) -> None:
        """Test setting running state."""
        result = dashboard.set_running(True)

        assert result is dashboard
        assert dashboard.state.is_running is True

    def test_set_status(self, dashboard: Dashboard) -> None:
        """Test setting status message."""
        result = dashboard.set_status("Processing...")

        assert result is dashboard
        assert dashboard.state.status_message == "Processing..."

    def test_set_output(self, dashboard: Dashboard) -> None:
        """Test setting output."""
        result = dashboard.set_output("Claude output here")

        assert result is dashboard
        assert dashboard.state.current_output == "Claude output here"

    def test_log(self, dashboard: Dashboard) -> None:
        """Test logging messages."""
        result = dashboard.log("Log message 1")
        dashboard.log("Log message 2")

        assert result is dashboard
        assert "Log message 1" in dashboard.state.output_lines
        assert "Log message 2" in dashboard.state.output_lines

    def test_set_error(self, dashboard: Dashboard) -> None:
        """Test setting error."""
        result = dashboard.set_error("Error message", details="Error details")

        assert result is dashboard
        assert dashboard.state.error_message == "Error message"
        assert dashboard.state.error_details == "Error details"

    def test_clear_error(self, dashboard: Dashboard) -> None:
        """Test clearing error."""
        dashboard.state.error_message = "Error"
        dashboard.state.error_details = "Details"

        result = dashboard.clear_error()

        assert result is dashboard
        assert dashboard.state.error_message is None
        assert dashboard.state.error_details is None

    def test_add_iteration_history(self, dashboard: Dashboard) -> None:
        """Test adding iteration to history."""
        result = dashboard.add_iteration_history(
            1, status="success", cost=0.05, duration=10.0, task="Test task"
        )

        assert result is dashboard
        assert len(dashboard.state.iteration_history) == 1
        assert dashboard.state.iteration_history[0]["iteration"] == 1
        assert dashboard.state.iteration_history[0]["status"] == "success"

    def test_update_iteration_history(self, dashboard: Dashboard) -> None:
        """Test updating iteration in history."""
        dashboard.add_iteration_history(1, status="running")
        result = dashboard.update_iteration_history(1, status="success", duration=15.0)

        assert result is dashboard
        assert dashboard.state.iteration_history[0]["status"] == "success"
        assert dashboard.state.iteration_history[0]["duration"] == 15.0

    def test_add_commit(self, dashboard: Dashboard) -> None:
        """Test adding a commit to the dashboard."""
        result = dashboard.add_commit(1, "feat: add feature", commit_hash="abc123d")

        assert result is dashboard
        assert len(dashboard.state.commit_log) == 1
        assert dashboard.state.commit_log[0]["iteration"] == 1
        assert dashboard.state.commit_log[0]["message"] == "feat: add feature"
        assert dashboard.state.commit_log[0]["hash"] == "abc123d"

    def test_add_commit_without_hash(self, dashboard: Dashboard) -> None:
        """Test adding a commit without hash."""
        dashboard.add_commit(1, "Test commit")

        assert dashboard.state.commit_log[0]["hash"] is None


class TestDashboardEventHandlers:
    """Tests for Dashboard event handler integration."""

    @pytest.fixture
    def console(self) -> Console:
        """Create a test console."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def dashboard(self, console: Console) -> Dashboard:
        """Create a test dashboard."""
        return Dashboard(console)

    @pytest.fixture
    def emitter(self) -> EventEmitter:
        """Create a test event emitter."""
        return EventEmitter()

    def test_connect_events(self, dashboard: Dashboard, emitter: EventEmitter) -> None:
        """Test connecting event handlers."""
        result = dashboard.connect_events(emitter)

        assert result is dashboard
        # Check handlers were registered
        assert emitter.has_handlers(EventType.LOOP_START)
        assert emitter.has_handlers(EventType.LOOP_END)
        assert emitter.has_handlers(EventType.ITERATION_START)
        assert emitter.has_handlers(EventType.ITERATION_END)
        assert emitter.has_handlers(EventType.CLAUDE_INVOKE)
        assert emitter.has_handlers(EventType.CLAUDE_RESPONSE)
        assert emitter.has_handlers(EventType.CLAUDE_ERROR)
        assert emitter.has_handlers(EventType.TASK_COMPLETE)
        assert emitter.has_handlers(EventType.TASK_BLOCKED)
        assert emitter.has_handlers(EventType.COST_UPDATE)
        assert emitter.has_handlers(EventType.COST_LIMIT_EXCEEDED)
        assert emitter.has_handlers(EventType.COMMIT_SUCCESS)
        assert emitter.has_handlers(EventType.LOG_MESSAGE)

    def test_on_loop_start(self, dashboard: Dashboard) -> None:
        """Test LOOP_START event handler."""
        event = Event(
            EventType.LOOP_START,
            {"max_iterations": 20, "max_cost": 5.0},
        )
        dashboard._on_loop_start(event)

        assert dashboard.state.is_running is True
        assert dashboard.state.max_iterations == 20
        assert dashboard.state.max_cost == 5.0

    def test_on_loop_end(self, dashboard: Dashboard) -> None:
        """Test LOOP_END event handler."""
        dashboard.state.is_running = True
        event = Event(EventType.LOOP_END, {"status": "complete"})
        dashboard._on_loop_end(event)

        assert dashboard.state.is_running is False
        assert "complete" in dashboard.state.status_message

    def test_on_iteration_start(self, dashboard: Dashboard) -> None:
        """Test ITERATION_START event handler."""
        event = Event(
            EventType.ITERATION_START,
            {"iteration": 5, "completed": 3, "total": 10},
        )
        dashboard._on_iteration_start(event)

        assert dashboard.state.iteration == 5
        assert dashboard.state.tasks_completed == 3
        assert dashboard.state.tasks_total == 10
        assert dashboard.state.current_output == ""

    def test_on_iteration_start_adds_to_history(self, dashboard: Dashboard) -> None:
        """Test ITERATION_START event adds to history."""
        event = Event(
            EventType.ITERATION_START,
            {"iteration": 5, "task": "Test task"},
        )
        dashboard._on_iteration_start(event)

        assert len(dashboard.state.iteration_history) == 1
        assert dashboard.state.iteration_history[0]["iteration"] == 5
        assert dashboard.state.iteration_history[0]["status"] == "running"
        assert dashboard.state.iteration_history[0]["task"] == "Test task"

    def test_on_iteration_end(self, dashboard: Dashboard) -> None:
        """Test ITERATION_END event handler."""
        dashboard.state.iteration = 5
        event = Event(
            EventType.ITERATION_END,
            {"success": True, "duration": 15.5},
        )
        dashboard._on_iteration_end(event)

        assert "success" in dashboard.state.status_message
        assert "15.5" in dashboard.state.status_message

    def test_on_iteration_end_updates_history(self, dashboard: Dashboard) -> None:
        """Test ITERATION_END event updates history."""
        dashboard.state.iteration = 5
        dashboard.state.add_iteration_to_history(5, status="running")

        event = Event(
            EventType.ITERATION_END,
            {"success": True, "duration": 15.5, "cost": 0.1234},
        )
        dashboard._on_iteration_end(event)

        assert dashboard.state.iteration_history[0]["status"] == "success"
        assert dashboard.state.iteration_history[0]["duration"] == 15.5
        assert dashboard.state.iteration_history[0]["cost"] == 0.1234

    def test_on_claude_invoke(self, dashboard: Dashboard) -> None:
        """Test CLAUDE_INVOKE event handler."""
        event = Event(
            EventType.CLAUDE_INVOKE,
            {"task": "Implement the feature"},
        )
        dashboard._on_claude_invoke(event)

        assert "Invoking Claude" in dashboard.state.status_message

    def test_on_claude_response(self, dashboard: Dashboard) -> None:
        """Test CLAUDE_RESPONSE event handler."""
        dashboard.state.cost = 1.0
        event = Event(
            EventType.CLAUDE_RESPONSE,
            {"cost_usd": 0.5},
        )
        dashboard._on_claude_response(event)

        assert dashboard.state.cost == 1.5

    def test_on_claude_error(self, dashboard: Dashboard) -> None:
        """Test CLAUDE_ERROR event handler."""
        event = Event(
            EventType.CLAUDE_ERROR,
            {"return_code": 1, "output": "Error output"},
        )
        dashboard._on_claude_error(event)

        assert dashboard.state.error_message is not None
        assert "code 1" in dashboard.state.error_message

    def test_on_task_complete(self, dashboard: Dashboard) -> None:
        """Test TASK_COMPLETE event handler."""
        dashboard.state.tasks_completed = 5
        dashboard.state.active_task = Task(text="Old task", complete=False, line_number=1)
        event = Event(
            EventType.TASK_COMPLETE,
            {"task": "Completed task"},
        )
        dashboard._on_task_complete(event)

        assert dashboard.state.tasks_completed == 6
        assert dashboard.state.active_task is None

    def test_on_task_blocked(self, dashboard: Dashboard) -> None:
        """Test TASK_BLOCKED event handler."""
        event = Event(
            EventType.TASK_BLOCKED,
            {"line_number": 42},
        )
        dashboard._on_task_blocked(event)

        assert 42 in dashboard.state.blocked_tasks

    def test_on_cost_update(self, dashboard: Dashboard) -> None:
        """Test COST_UPDATE event handler."""
        event = Event(
            EventType.COST_UPDATE,
            {"total_cost": 2.5},
        )
        dashboard._on_cost_update(event)

        assert dashboard.state.cost == 2.5

    def test_on_cost_update_updates_history(self, dashboard: Dashboard) -> None:
        """Test COST_UPDATE event updates iteration history."""
        dashboard.state.iteration = 5
        dashboard.state.add_iteration_to_history(5, status="running")

        event = Event(
            EventType.COST_UPDATE,
            {"total_cost": 2.5, "iteration_cost": 0.5},
        )
        dashboard._on_cost_update(event)

        assert dashboard.state.iteration_history[0]["cost"] == 0.5

    def test_on_cost_limit_exceeded(self, dashboard: Dashboard) -> None:
        """Test COST_LIMIT_EXCEEDED event handler."""
        event = Event(
            EventType.COST_LIMIT_EXCEEDED,
            {"total_cost": 5.5, "max_cost": 5.0},
        )
        dashboard._on_cost_limit_exceeded(event)

        assert dashboard.state.error_message is not None
        assert "exceeded" in dashboard.state.error_message.lower()

    def test_on_commit_success(self, dashboard: Dashboard) -> None:
        """Test COMMIT_SUCCESS event handler."""
        event = Event(
            EventType.COMMIT_SUCCESS,
            {"iteration": 5, "message": "feat: add new feature", "hash": "abc123d"},
        )
        dashboard._on_commit_success(event)

        assert len(dashboard.state.commit_log) == 1
        assert dashboard.state.commit_log[0]["iteration"] == 5
        assert dashboard.state.commit_log[0]["message"] == "feat: add new feature"
        assert dashboard.state.commit_log[0]["hash"] == "abc123d"

    def test_on_commit_success_without_hash(self, dashboard: Dashboard) -> None:
        """Test COMMIT_SUCCESS event handler without hash."""
        event = Event(
            EventType.COMMIT_SUCCESS,
            {"iteration": 3, "message": "fix: bug fix"},
        )
        dashboard._on_commit_success(event)

        assert dashboard.state.commit_log[0]["hash"] is None

    def test_on_log_message(self, dashboard: Dashboard) -> None:
        """Test LOG_MESSAGE event handler."""
        event = Event(
            EventType.LOG_MESSAGE,
            {"message": "Log entry"},
        )
        dashboard._on_log_message(event)

        assert "Log entry" in dashboard.state.output_lines


class TestDashboardContextManager:
    """Tests for Dashboard context manager."""

    @pytest.fixture
    def console(self) -> Console:
        """Create a test console."""
        return Console(file=StringIO(), force_terminal=True, width=120, height=40)

    def test_context_manager_enter(self, console: Console) -> None:
        """Test entering context manager."""
        dashboard = Dashboard(console)

        with dashboard as d:
            assert d is dashboard
            assert dashboard._live is not None

    def test_context_manager_exit(self, console: Console) -> None:
        """Test exiting context manager."""
        dashboard = Dashboard(console)

        with dashboard:
            pass

        assert dashboard._live is None


class TestCreateDashboard:
    """Tests for create_dashboard factory function."""

    def test_create_dashboard_defaults(self) -> None:
        """Test factory with defaults."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        dashboard = create_dashboard(console)

        assert isinstance(dashboard, Dashboard)
        assert dashboard.compact is False
        assert dashboard.refresh_per_second == 4

    def test_create_dashboard_compact(self) -> None:
        """Test factory with compact mode."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        dashboard = create_dashboard(console, compact=True)

        assert dashboard.compact is True

    def test_create_dashboard_custom_refresh(self) -> None:
        """Test factory with custom refresh rate."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        dashboard = create_dashboard(console, refresh_per_second=10)

        assert dashboard.refresh_per_second == 10


class TestModuleExports:
    """Tests for module exports."""

    def test_import_dashboard(self) -> None:
        """Test importing Dashboard class."""
        from zoyd.tui import Dashboard

        assert Dashboard is not None

    def test_import_dashboard_state(self) -> None:
        """Test importing DashboardState class."""
        from zoyd.tui import DashboardState

        assert DashboardState is not None

    def test_import_create_dashboard(self) -> None:
        """Test importing create_dashboard function."""
        from zoyd.tui import create_dashboard

        assert callable(create_dashboard)

    def test_in_all(self) -> None:
        """Test that exports are in __all__."""
        import zoyd.tui as tui

        assert "Dashboard" in tui.__all__
        assert "DashboardState" in tui.__all__
        assert "create_dashboard" in tui.__all__
