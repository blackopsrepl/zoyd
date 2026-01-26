"""Tests for the zoyd.tui.live module."""

from __future__ import annotations

import io

import pytest

rich = pytest.importorskip("rich")

from rich.console import Console

from zoyd.tui.live import LiveDisplay, create_live_display
from zoyd.tui.spinners import MindFlayerSpinner


class TestLiveDisplayInit:
    """Tests for LiveDisplay initialization."""

    def test_create_with_defaults(self) -> None:
        """Should create a LiveDisplay with default settings."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        assert live.console is console
        assert live.prd_path == ""
        assert live.progress_path == ""
        assert live.max_iterations == 10
        assert live.model is None
        assert live.max_cost is None
        assert live.max_log_lines == 20

    def test_create_with_custom_settings(self) -> None:
        """Should create a LiveDisplay with custom settings."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(
            console,
            prd_path="/path/to/prd.md",
            progress_path="/path/to/progress.txt",
            max_iterations=20,
            model="opus",
            max_cost=5.0,
            max_log_lines=50,
        )
        assert live.prd_path == "/path/to/prd.md"
        assert live.progress_path == "/path/to/progress.txt"
        assert live.max_iterations == 20
        assert live.model == "opus"
        assert live.max_cost == 5.0
        assert live.max_log_lines == 50


class TestLiveDisplayState:
    """Tests for LiveDisplay state management."""

    def test_initial_iteration_is_zero(self) -> None:
        """Initial iteration should be 0."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        assert live.iteration == 0

    def test_set_iteration(self) -> None:
        """Should be able to set iteration."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.iteration = 5
        assert live.iteration == 5

    def test_initial_cost_is_zero(self) -> None:
        """Initial cost should be 0."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        assert live.cost == 0.0

    def test_set_cost(self) -> None:
        """Should be able to set cost."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.cost = 1.23
        assert live.cost == 1.23

    def test_set_task(self) -> None:
        """Should be able to set task text."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.set_task("Fix the bug")
        assert live._task_text == "Fix the bug"

    def test_clear_task(self) -> None:
        """Should be able to clear task text."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.set_task("Fix the bug")
        live.set_task(None)
        assert live._task_text is None

    def test_initial_scroll_offset_is_zero(self) -> None:
        """Initial scroll offset should be 0."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        assert live._scroll_offset == 0

    def test_initial_log_lines_is_list(self) -> None:
        """Log lines should be an unbounded list, not a deque."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        assert isinstance(live._log_lines, list)

    def test_initial_completed_is_zero(self) -> None:
        """Initial completed count should be 0."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        assert live._completed == 0

    def test_initial_total_is_zero(self) -> None:
        """Initial total count should be 0."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        assert live._total == 0

    def test_set_completion(self) -> None:
        """set_completion should update _completed and _total."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.set_completion(5, 10)
        assert live._completed == 5
        assert live._total == 10

    def test_set_completion_updates_both_fields(self) -> None:
        """set_completion should update both fields independently."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.set_completion(3, 7)
        assert live._completed == 3
        assert live._total == 7
        live.set_completion(7, 7)
        assert live._completed == 7
        assert live._total == 7


class TestLiveDisplaySpinner:
    """Tests for LiveDisplay spinner integration."""

    def test_spinner_initially_none(self) -> None:
        """Spinner should be None initially."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        assert live._spinner is None

    def test_start_spinner_creates_mind_flayer_spinner(self) -> None:
        """start_spinner should create a MindFlayerSpinner."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.start_spinner("Loading...")
        assert live._spinner is not None
        assert isinstance(live._spinner, MindFlayerSpinner)

    def test_start_spinner_with_default_text(self) -> None:
        """start_spinner should use default text."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.start_spinner()
        assert live._spinner.text == "Invoking Claude..."

    def test_start_spinner_with_custom_text(self) -> None:
        """start_spinner should accept custom text."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.start_spinner("Processing...")
        assert live._spinner.text == "Processing..."

    def test_stop_spinner_clears_spinner(self) -> None:
        """stop_spinner should clear the spinner."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.start_spinner("Loading...")
        assert live._spinner is not None
        live.stop_spinner()
        assert live._spinner is None

    def test_stop_spinner_when_no_spinner(self) -> None:
        """stop_spinner should not error when no spinner."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.stop_spinner()  # Should not raise
        assert live._spinner is None

    def test_spinner_renders_in_task_line(self) -> None:
        """Spinner should be rendered in task line when active."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.start_spinner("Loading...")
        task_line = live._render_task_line()
        assert task_line is live._spinner


class TestLiveDisplayLogging:
    """Tests for LiveDisplay logging methods."""

    def test_log_adds_message(self) -> None:
        """log should add a message to log lines."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log("Test message")
        assert len(live._log_lines) == 1
        assert str(live._log_lines[0]) == "Test message"

    def test_log_with_style(self) -> None:
        """log should apply style to message."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log("Styled message", style="bold")
        assert len(live._log_lines) == 1

    def test_log_iteration_start(self) -> None:
        """log_iteration_start should log iteration info."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console, max_iterations=10)
        live.log_iteration_start(3, 5, 15)
        assert live.iteration == 3
        assert len(live._log_lines) == 1
        assert "3/10" in str(live._log_lines[0])
        assert "5/15" in str(live._log_lines[0])

    def test_log_success(self) -> None:
        """log_success should log with success prefix."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log_success("Task completed")
        assert len(live._log_lines) == 1
        assert "[success]Task completed" in str(live._log_lines[0])

    def test_log_error(self) -> None:
        """log_error should log with error prefix."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log_error("Something failed")
        assert len(live._log_lines) == 1
        assert "[error]Something failed" in str(live._log_lines[0])

    def test_log_warning(self) -> None:
        """log_warning should log with warning prefix."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log_warning("Be careful")
        assert len(live._log_lines) == 1
        assert "[warning]Be careful" in str(live._log_lines[0])

    def test_log_lines_unbounded(self) -> None:
        """Log lines should be stored in an unbounded list."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console, max_log_lines=3)
        live.log("Line 1")
        live.log("Line 2")
        live.log("Line 3")
        live.log("Line 4")
        # All lines are kept (unbounded list, not deque)
        assert len(live._log_lines) == 4
        assert str(live._log_lines[0]) == "Line 1"
        assert str(live._log_lines[3]) == "Line 4"


class TestLiveDisplayRendering:
    """Tests for LiveDisplay rendering methods."""

    def test_render_banner(self) -> None:
        """_render_banner should return a renderable."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console, prd_path="test.md", model="opus")
        banner = live._render_banner()
        assert banner is not None

    def test_render_logs_empty(self) -> None:
        """_render_logs should return placeholder when empty."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        logs = live._render_logs()
        # Check it returns something renderable
        assert logs is not None

    def test_render_logs_with_content(self) -> None:
        """_render_logs should return panel with content."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log("Test message")
        logs = live._render_logs()
        assert logs is not None

    def test_render_complete(self) -> None:
        """_render should return complete display."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log("Test")
        rendered = live._render()
        assert rendered is not None


class TestLiveDisplayContextManager:
    """Tests for LiveDisplay context manager."""

    def test_context_manager_enter(self) -> None:
        """Entering context should start live display."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        live = LiveDisplay(console)
        with live:
            assert live._live is not None

    def test_context_manager_exit(self) -> None:
        """Exiting context should stop live display."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        live = LiveDisplay(console)
        with live:
            pass
        assert live._live is None

    def test_context_manager_returns_self(self) -> None:
        """Context manager should return self on enter."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        live = LiveDisplay(console)
        with live as ctx:
            assert ctx is live


class TestLiveDisplayResizeHandler:
    """Tests for LiveDisplay terminal resize handling."""

    def test_old_sigwinch_handler_initially_none(self) -> None:
        """Old SIGWINCH handler should be None initially."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        assert live._old_sigwinch_handler is None

    def test_install_resize_handler_saves_old_handler(self) -> None:
        """_install_resize_handler should save the previous handler."""
        import signal
        if not hasattr(signal, "SIGWINCH"):
            pytest.skip("SIGWINCH not available on this platform")

        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)

        # Save current handler for comparison
        old_handler = signal.getsignal(signal.SIGWINCH)

        live._install_resize_handler()
        assert live._old_sigwinch_handler == old_handler

        # Clean up
        live._restore_resize_handler()

    def test_restore_resize_handler_restores_old_handler(self) -> None:
        """_restore_resize_handler should restore the previous handler."""
        import signal
        if not hasattr(signal, "SIGWINCH"):
            pytest.skip("SIGWINCH not available on this platform")

        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)

        # Save current handler for comparison
        original_handler = signal.getsignal(signal.SIGWINCH)

        live._install_resize_handler()
        live._restore_resize_handler()

        # Handler should be restored
        assert signal.getsignal(signal.SIGWINCH) == original_handler
        assert live._old_sigwinch_handler is None

    def test_context_manager_installs_handler(self) -> None:
        """Entering context should install resize handler."""
        import signal
        if not hasattr(signal, "SIGWINCH"):
            pytest.skip("SIGWINCH not available on this platform")

        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        live = LiveDisplay(console)

        with live:
            # Handler should be installed
            current_handler = signal.getsignal(signal.SIGWINCH)
            assert current_handler == live._handle_resize

    def test_context_manager_restores_handler_on_exit(self) -> None:
        """Exiting context should restore previous handler."""
        import signal
        if not hasattr(signal, "SIGWINCH"):
            pytest.skip("SIGWINCH not available on this platform")

        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        live = LiveDisplay(console)

        # Save current handler for comparison
        original_handler = signal.getsignal(signal.SIGWINCH)

        with live:
            pass

        # Handler should be restored
        assert signal.getsignal(signal.SIGWINCH) == original_handler

    def test_handle_resize_method_refreshes_display(self) -> None:
        """_handle_resize should refresh the display."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        live = LiveDisplay(console)

        with live:
            # Call handle_resize - should not raise
            live._handle_resize(0, None)

    def test_handle_resize_public_method(self) -> None:
        """handle_resize should be callable and return self."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)

        result = live.handle_resize()
        assert result is live

    def test_handle_resize_without_live_context(self) -> None:
        """handle_resize should not raise when called outside context."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)

        # Should not raise even when _live is None
        result = live.handle_resize()
        assert result is live


class TestCreateLiveDisplay:
    """Tests for create_live_display factory function."""

    def test_create_with_defaults(self) -> None:
        """Should create LiveDisplay with defaults."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = create_live_display(console)
        assert isinstance(live, LiveDisplay)
        assert live.console is console

    def test_create_with_all_options(self) -> None:
        """Should create LiveDisplay with all options."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = create_live_display(
            console,
            prd_path="prd.md",
            progress_path="progress.txt",
            max_iterations=15,
            model="sonnet",
            max_cost=10.0,
            max_log_lines=30,
        )
        assert live.prd_path == "prd.md"
        assert live.progress_path == "progress.txt"
        assert live.max_iterations == 15
        assert live.model == "sonnet"
        assert live.max_cost == 10.0
        assert live.max_log_lines == 30


class TestModuleExports:
    """Tests for module exports."""

    def test_import_live_display(self) -> None:
        """LiveDisplay should be importable."""
        from zoyd.tui.live import LiveDisplay
        assert LiveDisplay is not None

    def test_import_create_live_display(self) -> None:
        """create_live_display should be importable."""
        from zoyd.tui.live import create_live_display
        assert create_live_display is not None
