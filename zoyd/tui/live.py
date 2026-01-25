"""Live display for fixed banner with scrolling logs.

Provides a Rich Live display that keeps the banner/status fixed at the top
while allowing iteration logs to scroll underneath.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from zoyd.tui.panels import create_status_bar
from zoyd.tui.spinners import MindFlayerSpinner
from zoyd.tui.theme import COLORS

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console, RenderableType


class LiveDisplay:
    """A live display with fixed banner and scrolling logs.

    The display is split into two areas:
    - Banner: Fixed at top, shows status bar with iteration, model, cost
    - Logs: Scrolling area below showing recent log messages
    """

    def __init__(
        self,
        console: Console,
        *,
        prd_path: str = "",
        progress_path: str = "",
        max_iterations: int = 10,
        model: str | None = None,
        max_cost: float | None = None,
        max_log_lines: int = 20,
    ) -> None:
        """Initialize the live display.

        Args:
            console: Rich Console to use for output.
            prd_path: Path to the PRD file.
            progress_path: Path to the progress file.
            max_iterations: Maximum iterations allowed.
            model: Claude model being used.
            max_cost: Maximum cost limit in USD.
            max_log_lines: Maximum number of log lines to show.
        """
        self.console = console
        self.prd_path = prd_path
        self.progress_path = progress_path
        self.max_iterations = max_iterations
        self.model = model
        self.max_cost = max_cost
        self.max_log_lines = max_log_lines

        # State
        self._iteration = 0
        self._cost = 0.0
        self._task_text: str | None = None
        self._spinner: MindFlayerSpinner | None = None
        self._log_lines: deque[Text] = deque(maxlen=max_log_lines)

        # Live display
        self._live: Live | None = None

    @property
    def iteration(self) -> int:
        """Get the current iteration number."""
        return self._iteration

    @iteration.setter
    def iteration(self, value: int) -> None:
        """Set the current iteration number and refresh display."""
        self._iteration = value
        self._refresh()

    @property
    def cost(self) -> float:
        """Get the current cost."""
        return self._cost

    @cost.setter
    def cost(self, value: float) -> None:
        """Set the current cost and refresh display."""
        self._cost = value
        self._refresh()

    def set_task(self, text: str | None) -> None:
        """Set the current task being worked on.

        Args:
            text: Task text, or None to clear.
        """
        self._task_text = text
        self._refresh()

    def start_spinner(self, text: str = "Invoking Claude...") -> None:
        """Start the loading spinner.

        Args:
            text: Text to show next to the spinner.
        """
        self._spinner = MindFlayerSpinner(text=text)
        self._refresh()

    def stop_spinner(self) -> None:
        """Stop the loading spinner."""
        self._spinner = None
        self._refresh()

    def log(self, message: str, style: str | None = None) -> None:
        """Add a log message to the scrolling area.

        Args:
            message: The message to log.
            style: Optional Rich style for the message.
        """
        text = Text(message, style=style or "")
        self._log_lines.append(text)
        self._refresh()

    def log_iteration_start(self, iteration: int, completed: int, total: int) -> None:
        """Log the start of an iteration.

        Args:
            iteration: Iteration number.
            completed: Number of completed tasks.
            total: Total number of tasks.
        """
        self._iteration = iteration
        self.log(
            f"=== Iteration {iteration}/{self.max_iterations} ({completed}/{total} tasks) ===",
            style="bold",
        )

    def log_success(self, message: str) -> None:
        """Log a success message.

        Args:
            message: The success message.
        """
        self.log(f"[success]{message}", style="success")

    def log_error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: The error message.
        """
        self.log(f"[error]{message}", style="error")

    def log_warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message: The warning message.
        """
        self.log(f"[warning]{message}", style="warning")

    def _render_banner(self) -> RenderableType:
        """Render the banner/status bar area.

        Returns:
            Rich renderable for the banner.
        """
        bar = create_status_bar(
            prd=self.prd_path,
            progress=self.progress_path,
            iteration=self._iteration,
            max_iterations=self.max_iterations,
            model=self.model,
            cost=self._cost if self._cost > 0 or self.max_cost else None,
            max_cost=self.max_cost,
        )
        bar.title = "Status"
        return bar.render()

    def _render_task_line(self) -> RenderableType | None:
        """Render the current task line with optional spinner.

        Returns:
            Rich renderable for the task line, or None.
        """
        if self._spinner is not None:
            return self._spinner
        if self._task_text:
            return Text(f"Task: {self._task_text}", style="zoyd.task.active")
        return None

    def _render_logs(self) -> RenderableType:
        """Render the scrolling log area.

        Returns:
            Rich renderable for the logs.
        """
        if not self._log_lines:
            return Text("Waiting for activity...", style="dim")

        # Join log lines with newlines
        content = Text()
        for i, line in enumerate(self._log_lines):
            if i > 0:
                content.append("\n")
            content.append(line)

        return Panel(
            content,
            title="[panel.title]Log[/]",
            border_style=COLORS["twilight"],
            padding=(0, 1),
        )

    def _render(self) -> RenderableType:
        """Render the complete display.

        Returns:
            Rich renderable for the entire display.
        """
        components = [self._render_banner()]

        task_line = self._render_task_line()
        if task_line:
            components.append(Text())  # Spacer
            components.append(task_line)

        components.append(Text())  # Spacer
        components.append(self._render_logs())

        return Group(*components)

    def _refresh(self) -> None:
        """Refresh the live display if active."""
        if self._live is not None:
            self._live.update(self._render())

    def __enter__(self) -> LiveDisplay:
        """Enter the live display context.

        Returns:
            Self for use in with statement.
        """
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
        )
        self._live.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the live display context."""
        if self._live is not None:
            self._live.__exit__(exc_type, exc_val, exc_tb)
            self._live = None


class PlainDisplay:
    """A plain text display for non-TUI output.

    Provides the same interface as LiveDisplay but outputs plain text
    to stdout without any Rich formatting or live updates.
    """

    def __init__(
        self,
        *,
        prd_path: str = "",
        progress_path: str = "",
        max_iterations: int = 10,
        model: str | None = None,
        max_cost: float | None = None,
        **kwargs,  # Ignore extra args like max_log_lines
    ) -> None:
        """Initialize the plain display.

        Args:
            prd_path: Path to the PRD file.
            progress_path: Path to the progress file.
            max_iterations: Maximum iterations allowed.
            model: Claude model being used.
            max_cost: Maximum cost limit in USD.
        """
        self.prd_path = prd_path
        self.progress_path = progress_path
        self.max_iterations = max_iterations
        self.model = model
        self.max_cost = max_cost

        # State (same as LiveDisplay for API compatibility)
        self._iteration = 0
        self._cost = 0.0
        self._task_text: str | None = None

    @property
    def iteration(self) -> int:
        """Get the current iteration number."""
        return self._iteration

    @iteration.setter
    def iteration(self, value: int) -> None:
        """Set the current iteration number."""
        self._iteration = value

    @property
    def cost(self) -> float:
        """Get the current cost."""
        return self._cost

    @cost.setter
    def cost(self, value: float) -> None:
        """Set the current cost."""
        self._cost = value

    def set_task(self, text: str | None) -> None:
        """Set the current task being worked on.

        Args:
            text: Task text, or None to clear.
        """
        self._task_text = text

    def start_spinner(self, text: str = "Invoking Claude...") -> None:
        """Start the loading spinner (no-op in plain mode).

        Args:
            text: Text to show (ignored in plain mode).
        """
        # Plain mode doesn't show spinners
        pass

    def stop_spinner(self) -> None:
        """Stop the loading spinner (no-op in plain mode)."""
        pass

    def log(self, message: str, style: str | None = None) -> None:
        """Print a log message to stdout.

        Args:
            message: The message to log.
            style: Optional style (ignored in plain mode).
        """
        # Strip Rich markup tags for plain output
        import re
        plain_message = re.sub(r'\[/?[^\]]+\]', '', message)
        print(plain_message)

    def log_iteration_start(self, iteration: int, completed: int, total: int) -> None:
        """Log the start of an iteration.

        Args:
            iteration: Iteration number.
            completed: Number of completed tasks.
            total: Total number of tasks.
        """
        self._iteration = iteration
        print(f"=== Iteration {iteration}/{self.max_iterations} ({completed}/{total} tasks) ===")

    def log_success(self, message: str) -> None:
        """Log a success message.

        Args:
            message: The success message.
        """
        print(f"[SUCCESS] {message}")

    def log_error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: The error message.
        """
        print(f"[ERROR] {message}")

    def log_warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message: The warning message.
        """
        print(f"[WARNING] {message}")

    def __enter__(self) -> "PlainDisplay":
        """Enter the display context.

        Returns:
            Self for use in with statement.
        """
        # Print startup banner in plain mode
        print(f"Zoyd - Autonomous Loop")
        print(f"PRD: {self.prd_path}")
        print(f"Progress: {self.progress_path}")
        print(f"Max iterations: {self.max_iterations}")
        if self.model:
            print(f"Model: {self.model}")
        if self.max_cost:
            print(f"Cost limit: ${self.max_cost:.2f}")
        print()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the display context."""
        pass


def create_live_display(
    console: Console,
    *,
    prd_path: str = "",
    progress_path: str = "",
    max_iterations: int = 10,
    model: str | None = None,
    max_cost: float | None = None,
    max_log_lines: int = 20,
) -> LiveDisplay:
    """Create a live display instance.

    Factory function for creating LiveDisplay.

    Args:
        console: Rich Console to use for output.
        prd_path: Path to the PRD file.
        progress_path: Path to the progress file.
        max_iterations: Maximum iterations allowed.
        model: Claude model being used.
        max_cost: Maximum cost limit in USD.
        max_log_lines: Maximum number of log lines to show.

    Returns:
        A configured LiveDisplay instance.
    """
    return LiveDisplay(
        console,
        prd_path=prd_path,
        progress_path=progress_path,
        max_iterations=max_iterations,
        model=model,
        max_cost=max_cost,
        max_log_lines=max_log_lines,
    )


def create_plain_display(
    *,
    prd_path: str = "",
    progress_path: str = "",
    max_iterations: int = 10,
    model: str | None = None,
    max_cost: float | None = None,
) -> PlainDisplay:
    """Create a plain display instance.

    Factory function for creating PlainDisplay for non-TUI mode.

    Args:
        prd_path: Path to the PRD file.
        progress_path: Path to the progress file.
        max_iterations: Maximum iterations allowed.
        model: Claude model being used.
        max_cost: Maximum cost limit in USD.

    Returns:
        A configured PlainDisplay instance.
    """
    return PlainDisplay(
        prd_path=prd_path,
        progress_path=progress_path,
        max_iterations=max_iterations,
        model=model,
        max_cost=max_cost,
    )


class DashboardDisplay:
    """A fullscreen dashboard display using Rich Layout.

    Provides the same interface as LiveDisplay but uses the Dashboard class
    for a full-screen TUI experience with rich layout sections for:
    - Banner with ZOYD branding
    - Task tree with completion status
    - Claude output with Markdown rendering
    - Progress bars for iterations and cost
    - Git commit history
    """

    def __init__(
        self,
        console: Console,
        *,
        prd_path: str = "",
        progress_path: str = "",
        max_iterations: int = 10,
        model: str | None = None,
        max_cost: float | None = None,
        compact: bool = False,
        refresh_per_second: int = 4,
    ) -> None:
        """Initialize the dashboard display.

        Args:
            console: Rich Console to use for output.
            prd_path: Path to the PRD file.
            progress_path: Path to the progress file.
            max_iterations: Maximum iterations allowed.
            model: Claude model being used.
            max_cost: Maximum cost limit in USD.
            compact: Use compact layout for narrow terminals.
            refresh_per_second: How often to refresh the display.
        """
        from zoyd.tui.dashboard import Dashboard

        self.console = console
        self.prd_path = prd_path
        self.progress_path = progress_path
        self.max_iterations = max_iterations
        self.model = model
        self.max_cost = max_cost

        # Create the dashboard
        self._dashboard = Dashboard(
            console,
            compact=compact,
            refresh_per_second=refresh_per_second,
        )

        # Configure dashboard with initial state
        self._dashboard.set_config(
            prd_path=prd_path,
            progress_path=progress_path,
            model=model,
            max_iterations=max_iterations,
            max_cost=max_cost,
        )

        # Internal state (for property access)
        self._iteration = 0
        self._cost = 0.0
        self._task_text: str | None = None

    @property
    def iteration(self) -> int:
        """Get the current iteration number."""
        return self._iteration

    @iteration.setter
    def iteration(self, value: int) -> None:
        """Set the current iteration number and update dashboard."""
        self._iteration = value
        self._dashboard.set_iteration(value)

    @property
    def cost(self) -> float:
        """Get the current cost."""
        return self._cost

    @cost.setter
    def cost(self, value: float) -> None:
        """Set the current cost and update dashboard."""
        self._cost = value
        self._dashboard.set_cost(value)

    @property
    def events(self):
        """Get the dashboard for event connection.

        This allows LoopRunner to connect events to the dashboard.
        """
        return self._dashboard

    def set_task(self, text: str | None) -> None:
        """Set the current task being worked on.

        Args:
            text: Task text, or None to clear.
        """
        self._task_text = text
        # Find the matching task in the dashboard and set it as active
        if text:
            for task in self._dashboard.state.tasks:
                if task.text == text:
                    self._dashboard.set_active_task(task)
                    break
        else:
            self._dashboard.set_active_task(None)

    def set_tasks(self, tasks) -> None:
        """Set the task list for the dashboard.

        Args:
            tasks: List of Task objects.
        """
        self._dashboard.set_tasks(tasks)

    def start_spinner(self, text: str = "Invoking Claude...") -> None:
        """Start the loading spinner.

        Args:
            text: Text to show next to the spinner.
        """
        self._dashboard.set_status(text)

    def stop_spinner(self) -> None:
        """Stop the loading spinner."""
        self._dashboard.set_status("Ready")

    def log(self, message: str, style: str | None = None) -> None:
        """Add a log message to the dashboard.

        Args:
            message: The message to log.
            style: Optional Rich style for the message.
        """
        # Strip Rich tags if present
        import re
        plain_message = re.sub(r'\[/?[^\]]+\]', '', message)
        self._dashboard.log(plain_message)

    def log_iteration_start(self, iteration: int, completed: int, total: int) -> None:
        """Log the start of an iteration.

        Args:
            iteration: Iteration number.
            completed: Number of completed tasks.
            total: Total number of tasks.
        """
        self._iteration = iteration
        self._dashboard.set_iteration(iteration)
        self._dashboard.state.tasks_completed = completed
        self._dashboard.state.tasks_total = total
        self._dashboard.log(f"Starting iteration {iteration}/{self.max_iterations}")

    def log_success(self, message: str) -> None:
        """Log a success message.

        Args:
            message: The success message.
        """
        self._dashboard.log(f"✓ {message}")
        self._dashboard.clear_error()

    def log_error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: The error message.
        """
        self._dashboard.set_error(message)

    def log_warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message: The warning message.
        """
        self._dashboard.set_warning(message)

    def set_output(self, output: str) -> None:
        """Set the Claude output for display.

        Args:
            output: Claude's output text.
        """
        self._dashboard.set_output(output)

    def __enter__(self) -> "DashboardDisplay":
        """Enter the fullscreen dashboard context.

        Returns:
            Self for use in with statement.
        """
        self._dashboard.set_running(True)
        self._dashboard.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the fullscreen dashboard context."""
        self._dashboard.set_running(False)
        self._dashboard.__exit__(exc_type, exc_val, exc_tb)


def create_dashboard_display(
    console: Console,
    *,
    prd_path: str = "",
    progress_path: str = "",
    max_iterations: int = 10,
    model: str | None = None,
    max_cost: float | None = None,
    compact: bool = False,
    refresh_per_second: int = 4,
) -> DashboardDisplay:
    """Create a fullscreen dashboard display instance.

    Factory function for creating DashboardDisplay for fullscreen mode.

    Args:
        console: Rich Console to use for output.
        prd_path: Path to the PRD file.
        progress_path: Path to the progress file.
        max_iterations: Maximum iterations allowed.
        model: Claude model being used.
        max_cost: Maximum cost limit in USD.
        compact: Use compact layout for narrow terminals.
        refresh_per_second: How often to refresh the display.

    Returns:
        A configured DashboardDisplay instance.
    """
    return DashboardDisplay(
        console,
        prd_path=prd_path,
        progress_path=progress_path,
        max_iterations=max_iterations,
        model=model,
        max_cost=max_cost,
        compact=compact,
        refresh_per_second=refresh_per_second,
    )
