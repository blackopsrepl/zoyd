"""Live display for fixed banner with scrolling logs.

Provides a Rich Live display that keeps the banner/status fixed at the top
while allowing iteration logs to scroll underneath.

The display handles terminal resize events (SIGWINCH) gracefully by refreshing
the display when the terminal size changes.
"""

from __future__ import annotations

import signal
from typing import TYPE_CHECKING, Any, Callable

from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from zoyd import __version__
from zoyd.tui.banner import get_versioned_banner
from zoyd.tui.panels import create_status_bar
from zoyd.tui.spinners import MindFlayerSpinner
from zoyd.tui.theme import COLORS

from rich.console import RenderableType

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console

# Default code theme for syntax highlighting in Markdown blocks
DEFAULT_CODE_THEME = "dracula"


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
        refresh_per_second: int = 4,
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
            refresh_per_second: How often to refresh the display.
        """
        self.console = console
        self.prd_path = prd_path
        self.progress_path = progress_path
        self.max_iterations = max_iterations
        self.model = model
        self.max_cost = max_cost
        self.max_log_lines = max_log_lines
        self.refresh_per_second = refresh_per_second

        # State
        self._iteration = 0
        self._cost = 0.0
        self._task_text: str | None = None
        self._spinner: MindFlayerSpinner | None = None
        self._log_lines: list[RenderableType] = []
        self._scroll_offset: int = 0
        self._completed = 0
        self._total = 0

        # Live display
        self._live: Live | None = None

        # Signal handler for terminal resize
        self._old_sigwinch_handler: Callable[[int, Any], Any] | int | None = None

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

    def set_completion(self, completed: int, total: int) -> None:
        """Set the task completion counts.

        Args:
            completed: Number of completed tasks.
            total: Total number of tasks.
        """
        self._completed = completed
        self._total = total
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

        If the user has scrolled up (offset > 0), the scroll offset is
        incremented so the viewport stays on the same content.  If already
        in auto-scroll mode (offset == 0), the view stays at the bottom.

        Args:
            message: The message to log.
            style: Optional Rich style for the message.
        """
        text = Text(message, style=style or "")
        self._log_lines.append(text)
        if self._scroll_offset > 0:
            self._scroll_offset += 1
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

    def log_lines(self, content: str) -> None:
        """Log content by splitting into individual lines.

        Each line is appended as a separate Text renderable to the log area.
        If the user has scrolled up (offset > 0), the scroll offset is
        incremented by the number of new lines so the viewport stays on
        the same content.

        Args:
            content: Content string to split and log line by line.
        """
        lines = content.split("\n")
        for line in lines:
            self._log_lines.append(Text(line))
        if self._scroll_offset > 0:
            self._scroll_offset += len(lines)
        self._refresh()

    def log_markdown(self, content: str, *, code_theme: str | None = None) -> None:
        """Log markdown content with syntax highlighting for code blocks.

        If the user has scrolled up (offset > 0), the scroll offset is
        incremented so the viewport stays on the same content.

        Args:
            content: Markdown content to render.
            code_theme: Optional code theme override. Defaults to DEFAULT_CODE_THEME.
        """
        theme = code_theme or DEFAULT_CODE_THEME
        md = Markdown(content, code_theme=theme)
        self._log_lines.append(md)
        if self._scroll_offset > 0:
            self._scroll_offset += 1
        self._refresh()

    def _render_banner(self) -> RenderableType:
        """Render the ZOYD ASCII art banner with mind flayer art and version.

        Uses ``get_versioned_banner(__version__)`` to include the version
        string below the second box in the banner.

        Returns:
            Rich renderable for the banner panel.
        """
        versioned = get_versioned_banner(__version__)
        banner_text = Text()
        for line in versioned.strip().split("\n"):
            banner_text.append(line + "\n", style=f"bold {COLORS['psionic']}")

        return Panel(
            banner_text,
            border_style=COLORS["twilight"],
            padding=(0, 2),
            subtitle=f"PRD: {self.prd_path}  |  Progress: {self.progress_path}",
        )

    def _render_status(self) -> RenderableType:
        """Render the status bar area.

        Returns:
            Rich renderable for the status bar.
        """
        bar = create_status_bar(
            task=self._task_text,
            completed=self._completed,
            total=self._total,
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

    def _get_log_height(self) -> int:
        """Calculate the available height for the log panel.

        Uses the terminal height minus the banner height (approximately 24 lines
        for the banner + status + task line + padding).

        Returns:
            Number of lines available for the log panel.
        """
        # Get terminal height, default to 40 if unavailable
        terminal_height = self.console.height or 40

        # Banner is approximately 22 lines, plus status bar (2), task line (2),
        # panel borders and padding (4). Reserve ~30 lines for non-log content.
        banner_overhead = 30

        # Calculate available height for logs (minimum 5 lines)
        available = max(5, terminal_height - banner_overhead)
        return available

    def _render_logs(self) -> RenderableType:
        """Render the scrolling log area with dynamic height.

        The log panel fills the remaining terminal height after the banner
        and status areas. Uses Group to support mixed content types
        (Text, Markdown, etc.).

        When ``_scroll_offset == 0`` (auto-scroll mode), the most recent
        ``log_height`` entries are shown.  Otherwise the view is shifted
        upward by ``_scroll_offset`` lines from the bottom.

        A scroll indicator is shown in the panel subtitle when the user
        has scrolled away from the bottom.

        Returns:
            Rich renderable for the logs.
        """
        log_height = self._get_log_height()
        total = len(self._log_lines)
        subtitle: str | None = None

        if not self._log_lines:
            content: RenderableType = Text("Waiting for activity...", style="dim")
        else:
            if self._scroll_offset == 0:
                # Auto-scroll: show the last log_height entries
                visible_lines = list(self._log_lines)[-log_height:]
            else:
                # Manual scroll: compute window from the offset
                end = max(0, total - self._scroll_offset)
                start = max(0, end - log_height)
                visible_lines = list(self._log_lines)[start:end]

                # Show scroll indicator
                subtitle = f"[lines {start + 1}-{end} of {total}]"

            # Use Group for mixed content types (Text, Markdown, etc.)
            content = Group(*visible_lines)

        return Panel(
            content,
            title="[panel.title]Log[/]",
            subtitle=subtitle,
            border_style=COLORS["twilight"],
            padding=(0, 1),
            height=log_height + 2,  # Add 2 for panel borders
        )

    def _render(self) -> RenderableType:
        """Render the complete display.

        Layout (top to bottom):
        1. ASCII art banner (ZOYD logo + mind flayer)
        2. Status bar (PRD, iteration, model, cost)
        3. Current task line (optional, with spinner)
        4. Scrolling log panel (fills remaining terminal height)

        Returns:
            Rich renderable for the entire display.
        """
        components = [self._render_banner()]
        components.append(self._render_status())

        task_line = self._render_task_line()
        if task_line:
            components.append(task_line)

        components.append(self._render_logs())

        return Group(*components)

    def _refresh(self) -> None:
        """Refresh the live display if active."""
        if self._live is not None:
            self._live.update(self._render())

    # --- Terminal resize handling ---

    def _handle_resize(self, signum: int, frame: Any) -> None:
        """Handle terminal resize signal (SIGWINCH).

        This method is called when the terminal is resized. It forces a refresh
        of the live display to adapt to the new terminal size.

        Args:
            signum: The signal number (SIGWINCH).
            frame: The current stack frame (unused).
        """
        # Force console to re-detect terminal size
        if hasattr(self.console, '_width'):
            self.console._width = None
        if hasattr(self.console, '_height'):
            self.console._height = None

        # Refresh the display
        self._refresh()

    def _install_resize_handler(self) -> None:
        """Install the SIGWINCH signal handler for terminal resize.

        Saves the old handler so it can be restored on exit.
        Only installs on Unix systems where SIGWINCH is available.
        """
        if hasattr(signal, "SIGWINCH"):
            self._old_sigwinch_handler = signal.signal(
                signal.SIGWINCH, self._handle_resize
            )

    def _restore_resize_handler(self) -> None:
        """Restore the previous SIGWINCH signal handler.

        Called when exiting the display context to restore the
        previous signal handler (if any).
        """
        if hasattr(signal, "SIGWINCH") and self._old_sigwinch_handler is not None:
            signal.signal(signal.SIGWINCH, self._old_sigwinch_handler)
            self._old_sigwinch_handler = None

    def handle_resize(self) -> "LiveDisplay":
        """Manually trigger a resize handling.

        This can be called programmatically to force the display to
        refresh based on the current terminal dimensions.

        Returns:
            Self for method chaining.
        """
        self._handle_resize(0, None)
        return self

    def __enter__(self) -> LiveDisplay:
        """Enter the live display context.

        Installs a SIGWINCH handler to gracefully handle terminal resizes.

        Returns:
            Self for use in with statement.
        """
        # Install resize handler before starting Live
        self._install_resize_handler()

        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=self.refresh_per_second,
            transient=False,
            screen=False,
        )
        self._live.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the live display context.

        Restores the previous SIGWINCH handler.
        """
        if self._live is not None:
            self._live.__exit__(exc_type, exc_val, exc_tb)
            self._live = None

        # Restore the old resize handler
        self._restore_resize_handler()


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
        self._completed = 0
        self._total = 0

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

    def set_completion(self, completed: int, total: int) -> None:
        """Set the task completion counts.

        Stores state for API compatibility but does not produce output.

        Args:
            completed: Number of completed tasks.
            total: Total number of tasks.
        """
        self._completed = completed
        self._total = total

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

    def log_markdown(self, content: str, *, code_theme: str | None = None) -> None:
        """Log markdown content as plain text.

        In plain mode, this strips markdown formatting and outputs plain text.
        Code blocks are preserved but without syntax highlighting.

        Args:
            content: Markdown content to render.
            code_theme: Ignored in plain mode.
        """
        # In plain mode, just print the markdown content as-is
        # The content is already human-readable markdown
        print(content)

    def log_lines(self, content: str) -> None:
        """Log content by printing each line individually.

        Args:
            content: Content string to split and print line by line.
        """
        for line in content.split("\n"):
            print(line)

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
    refresh_per_second: int = 4,
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
        refresh_per_second: How often to refresh the display.

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
        refresh_per_second=refresh_per_second,
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


