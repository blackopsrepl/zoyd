"""Live dashboard for the Zoyd TUI.

Provides a full-screen dashboard layout with:
- Banner: Mind flayer ASCII art header
- Status: Configuration and state information
- Tasks: Task tree with completion status
- Output: Claude output with markdown rendering
- Progress: Multi-progress bars for tasks, iterations, and cost

The dashboard uses Rich's Layout and Live components for real-time updates.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from zoyd.prd import Task
from zoyd.tui.banner import MIND_FLAYER_COMPACT, MIND_FLAYER_FULL
from zoyd.tui.events import Event, EventEmitter, EventType
from zoyd.tui.panels import (
    create_claude_output_panel,
    create_error_panel,
    create_iteration_history_panel,
    create_status_bar,
)
from zoyd.tui.progress import create_progress_panel
from zoyd.tui.task_tree import render_task_tree
from zoyd.tui.theme import COLORS

if TYPE_CHECKING:
    from rich.console import Console, RenderableType


# Layout names for dashboard sections
LAYOUT_BANNER = "banner"
LAYOUT_STATUS = "status"
LAYOUT_TASKS = "tasks"
LAYOUT_OUTPUT = "output"
LAYOUT_PROGRESS = "progress"
LAYOUT_HISTORY = "history"
LAYOUT_MAIN = "main"
LAYOUT_SIDEBAR = "sidebar"
LAYOUT_BODY = "body"


class DashboardState:
    """State container for the dashboard.

    Holds all dynamic state that can be updated during the loop:
    - Configuration: PRD path, progress path, model, limits
    - Progress: Current iteration, cost, task counts
    - Tasks: List of tasks with completion status
    - Output: Claude's output and log messages
    - Errors: Any error state to display
    """

    def __init__(self) -> None:
        """Initialize the dashboard state."""
        # Configuration
        self.prd_path: str = ""
        self.progress_path: str = ""
        self.model: str | None = None
        self.max_iterations: int = 10
        self.max_cost: float | None = None

        # Progress
        self.iteration: int = 0
        self.cost: float = 0.0
        self.tasks_completed: int = 0
        self.tasks_total: int = 0

        # Tasks
        self.tasks: list[Task] = []
        self.active_task: Task | None = None
        self.blocked_tasks: set[int] = set()

        # Output
        self.output_lines: deque[str] = deque(maxlen=50)
        self.current_output: str = ""

        # Status
        self.status_message: str = "Initializing..."
        self.is_running: bool = False

        # Error state
        self.error_message: str | None = None
        self.error_details: str | None = None

        # Iteration history
        self.iteration_history: list[dict] = []
        self.max_history_items: int = 10

    def reset_error(self) -> None:
        """Clear any error state."""
        self.error_message = None
        self.error_details = None

    def add_iteration_to_history(
        self,
        iteration: int,
        *,
        status: str = "pending",
        cost: float | None = None,
        duration: float | None = None,
        task: str | None = None,
    ) -> None:
        """Add an iteration to the history.

        Args:
            iteration: Iteration number.
            status: Status string - "success", "failed", "running", or "pending".
            cost: Cost in USD for this iteration.
            duration: Duration in seconds.
            task: Task description that was worked on.
        """
        item = {
            "iteration": iteration,
            "status": status,
            "cost": cost,
            "duration": duration,
            "task": task,
        }
        self.iteration_history.append(item)

        # Trim to max items
        if len(self.iteration_history) > self.max_history_items:
            self.iteration_history = self.iteration_history[-self.max_history_items :]

    def update_iteration_in_history(
        self,
        iteration: int,
        *,
        status: str | None = None,
        cost: float | None = None,
        duration: float | None = None,
        task: str | None = None,
    ) -> None:
        """Update an existing iteration in the history.

        Args:
            iteration: Iteration number to update.
            status: New status string (if provided).
            cost: New cost value (if provided).
            duration: New duration value (if provided).
            task: New task description (if provided).
        """
        for item in self.iteration_history:
            if item["iteration"] == iteration:
                if status is not None:
                    item["status"] = status
                if cost is not None:
                    item["cost"] = cost
                if duration is not None:
                    item["duration"] = duration
                if task is not None:
                    item["task"] = task
                break


class Dashboard:
    """Full-screen live dashboard for the Zoyd TUI.

    Provides a Layout-based dashboard with sections for:
    - Banner: Fixed header with mind flayer ASCII art
    - Status: Configuration and current state
    - Tasks: Task tree with completion icons
    - Output: Claude output and logs
    - Progress: Multi-progress bars

    The dashboard integrates with the EventEmitter to receive
    updates from the LoopRunner.
    """

    def __init__(
        self,
        console: Console,
        *,
        compact: bool = False,
        refresh_per_second: int = 4,
    ) -> None:
        """Initialize the dashboard.

        Args:
            console: Rich Console to use for output.
            compact: Use compact layout for narrow terminals.
            refresh_per_second: How often to refresh the display.
        """
        self.console = console
        self.compact = compact
        self.refresh_per_second = refresh_per_second

        # State
        self.state = DashboardState()

        # Live display
        self._live: Live | None = None

        # Create the layout structure
        self._layout = self._create_layout()

    def _create_layout(self) -> Layout:
        """Create the dashboard layout structure.

        Returns:
            A Rich Layout configured with all sections.
        """
        layout = Layout(name="root")

        # Main split: banner at top, body below
        layout.split_column(
            Layout(name=LAYOUT_BANNER, size=3 if self.compact else 5),
            Layout(name=LAYOUT_BODY),
        )

        # Body split: main area with sidebar
        layout[LAYOUT_BODY].split_row(
            Layout(name=LAYOUT_MAIN, ratio=2),
            Layout(name=LAYOUT_SIDEBAR, ratio=1),
        )

        # Main area: status at top, output below, history at bottom
        layout[LAYOUT_MAIN].split_column(
            Layout(name=LAYOUT_STATUS, size=5),
            Layout(name=LAYOUT_OUTPUT, ratio=2),
            Layout(name=LAYOUT_HISTORY, size=12),
        )

        # Sidebar: tasks at top, progress below
        layout[LAYOUT_SIDEBAR].split_column(
            Layout(name=LAYOUT_TASKS, ratio=2),
            Layout(name=LAYOUT_PROGRESS, ratio=1),
        )

        return layout

    def _render_banner(self) -> RenderableType:
        """Render the banner section.

        Returns:
            Rich renderable for the banner.
        """
        # Select compact or full banner based on mode
        art = MIND_FLAYER_COMPACT if self.compact else MIND_FLAYER_FULL

        # Just the title portion for the fixed header
        text = Text()
        text.append("ZOYD", style=f"bold {COLORS['psionic']}")
        if self.state.is_running:
            text.append(" - ", style="dim")
            text.append("RUNNING", style=f"bold {COLORS['success']}")
        elif self.state.error_message:
            text.append(" - ", style="dim")
            text.append("ERROR", style=f"bold {COLORS['error']}")
        else:
            text.append(" - ", style="dim")
            text.append("AUTONOMOUS LOOP", style=COLORS["orchid"])

        return Panel(
            text,
            border_style=COLORS["twilight"],
            padding=(0, 1),
        )

    def _render_status(self) -> RenderableType:
        """Render the status section.

        Returns:
            Rich renderable for status information.
        """
        bar = create_status_bar(
            prd=self.state.prd_path,
            progress=self.state.progress_path,
            iteration=self.state.iteration,
            max_iterations=self.state.max_iterations,
            model=self.state.model,
            cost=self.state.cost if self.state.cost > 0 or self.state.max_cost else None,
            max_cost=self.state.max_cost,
        )
        bar.title = "Status"
        return bar.render()

    def _render_tasks(self) -> RenderableType:
        """Render the tasks section.

        Returns:
            Rich renderable for the task tree.
        """
        if not self.state.tasks:
            return Panel(
                Text("No tasks loaded", style="dim"),
                title="[panel.title]Tasks[/]",
                border_style=COLORS["twilight"],
                padding=(1, 2),
            )

        tree = render_task_tree(
            self.state.tasks,
            title=f"Tasks ({self.state.tasks_completed}/{self.state.tasks_total})",
            active_task=self.state.active_task,
            blocked_tasks=self.state.blocked_tasks,
        )

        return Panel(
            tree,
            title="[panel.title]Tasks[/]",
            border_style=COLORS["twilight"],
            padding=(0, 1),
        )

    def _render_output(self) -> RenderableType:
        """Render the output section.

        Returns:
            Rich renderable for Claude output and logs.
        """
        # Show error panel if there's an error
        if self.state.error_message:
            return create_error_panel(
                self.state.error_message,
                details=self.state.error_details,
            ).render()

        # Show Claude output with Markdown rendering
        if self.state.current_output:
            # Use ClaudeOutputPanel for proper Markdown rendering
            subtitle = f"Iteration {self.state.iteration}" if self.state.iteration > 0 else None
            return create_claude_output_panel(
                self.state.current_output,
                title="Claude Output",
                subtitle=subtitle,
            ).render()

        # Show recent log lines when no Claude output
        if self.state.output_lines:
            content = Text()
            for i, line in enumerate(self.state.output_lines):
                if i > 0:
                    content.append("\n")
                content.append(line)
            return Panel(
                content,
                title="[panel.title]Output[/]",
                border_style=COLORS["twilight"],
                padding=(1, 2),
            )

        # Show placeholder with status message
        return Panel(
            Text(self.state.status_message, style="dim"),
            title="[panel.title]Output[/]",
            border_style=COLORS["twilight"],
            padding=(1, 2),
        )

    def _render_progress(self) -> RenderableType:
        """Render the progress section.

        Returns:
            Rich renderable for progress bars.
        """
        panel = create_progress_panel(
            task_completed=self.state.tasks_completed,
            task_total=self.state.tasks_total,
            iteration=self.state.iteration,
            max_iterations=self.state.max_iterations,
            cost=self.state.cost if self.state.max_cost else None,
            max_cost=self.state.max_cost,
        )
        return panel.render()

    def _render_history(self) -> RenderableType:
        """Render the iteration history section.

        Returns:
            Rich renderable for iteration history.
        """
        history_panel = create_iteration_history_panel(
            title="Iteration History",
            max_items=self.state.max_history_items,
        )

        # Populate with history items
        for item in self.state.iteration_history:
            history_panel.add_iteration(
                item["iteration"],
                status=item.get("status", "pending"),
                cost=item.get("cost"),
                duration=item.get("duration"),
                task=item.get("task"),
            )

        return history_panel.render()

    def _render(self) -> Layout:
        """Render the complete dashboard.

        Returns:
            The Layout with all sections populated.
        """
        self._layout[LAYOUT_BANNER].update(self._render_banner())
        self._layout[LAYOUT_STATUS].update(self._render_status())
        self._layout[LAYOUT_TASKS].update(self._render_tasks())
        self._layout[LAYOUT_OUTPUT].update(self._render_output())
        self._layout[LAYOUT_PROGRESS].update(self._render_progress())
        self._layout[LAYOUT_HISTORY].update(self._render_history())

        return self._layout

    def refresh(self) -> None:
        """Refresh the live display."""
        if self._live is not None:
            self._live.update(self._render())

    # --- State update methods ---

    def set_config(
        self,
        *,
        prd_path: str = "",
        progress_path: str = "",
        model: str | None = None,
        max_iterations: int = 10,
        max_cost: float | None = None,
    ) -> Dashboard:
        """Set configuration values.

        Args:
            prd_path: Path to the PRD file.
            progress_path: Path to the progress file.
            model: Claude model being used.
            max_iterations: Maximum iterations allowed.
            max_cost: Maximum cost limit in USD.

        Returns:
            Self for method chaining.
        """
        self.state.prd_path = prd_path
        self.state.progress_path = progress_path
        self.state.model = model
        self.state.max_iterations = max_iterations
        self.state.max_cost = max_cost
        self.refresh()
        return self

    def set_tasks(self, tasks: list[Task]) -> Dashboard:
        """Set the task list.

        Args:
            tasks: List of Task objects.

        Returns:
            Self for method chaining.
        """
        self.state.tasks = tasks
        self.state.tasks_total = len(tasks)
        self.state.tasks_completed = sum(1 for t in tasks if t.complete)
        self.refresh()
        return self

    def set_iteration(self, iteration: int) -> Dashboard:
        """Set the current iteration number.

        Args:
            iteration: Current iteration number.

        Returns:
            Self for method chaining.
        """
        self.state.iteration = iteration
        self.refresh()
        return self

    def set_cost(self, cost: float) -> Dashboard:
        """Set the current cost.

        Args:
            cost: Current cost in USD.

        Returns:
            Self for method chaining.
        """
        self.state.cost = cost
        self.refresh()
        return self

    def set_active_task(self, task: Task | None) -> Dashboard:
        """Set the currently active task.

        Args:
            task: The task being worked on, or None.

        Returns:
            Self for method chaining.
        """
        self.state.active_task = task
        self.refresh()
        return self

    def add_blocked_task(self, line_number: int) -> Dashboard:
        """Mark a task as blocked.

        Args:
            line_number: Line number of the blocked task.

        Returns:
            Self for method chaining.
        """
        self.state.blocked_tasks.add(line_number)
        self.refresh()
        return self

    def set_running(self, running: bool) -> Dashboard:
        """Set the running state.

        Args:
            running: Whether the loop is running.

        Returns:
            Self for method chaining.
        """
        self.state.is_running = running
        self.refresh()
        return self

    def set_status(self, message: str) -> Dashboard:
        """Set the status message.

        Args:
            message: Status message to display.

        Returns:
            Self for method chaining.
        """
        self.state.status_message = message
        self.refresh()
        return self

    def set_output(self, output: str) -> Dashboard:
        """Set the current Claude output.

        Args:
            output: Output text to display.

        Returns:
            Self for method chaining.
        """
        self.state.current_output = output
        self.refresh()
        return self

    def log(self, message: str) -> Dashboard:
        """Add a log message.

        Args:
            message: Message to add to the log.

        Returns:
            Self for method chaining.
        """
        self.state.output_lines.append(message)
        self.refresh()
        return self

    def set_error(self, message: str, details: str | None = None) -> Dashboard:
        """Set an error state.

        Args:
            message: Error message.
            details: Optional error details.

        Returns:
            Self for method chaining.
        """
        self.state.error_message = message
        self.state.error_details = details
        self.refresh()
        return self

    def clear_error(self) -> Dashboard:
        """Clear any error state.

        Returns:
            Self for method chaining.
        """
        self.state.reset_error()
        self.refresh()
        return self

    def add_iteration_history(
        self,
        iteration: int,
        *,
        status: str = "pending",
        cost: float | None = None,
        duration: float | None = None,
        task: str | None = None,
    ) -> Dashboard:
        """Add an iteration to the history.

        Args:
            iteration: Iteration number.
            status: Status string - "success", "failed", "running", or "pending".
            cost: Cost in USD for this iteration.
            duration: Duration in seconds.
            task: Task description that was worked on.

        Returns:
            Self for method chaining.
        """
        self.state.add_iteration_to_history(
            iteration, status=status, cost=cost, duration=duration, task=task
        )
        self.refresh()
        return self

    def update_iteration_history(
        self,
        iteration: int,
        *,
        status: str | None = None,
        cost: float | None = None,
        duration: float | None = None,
        task: str | None = None,
    ) -> Dashboard:
        """Update an existing iteration in the history.

        Args:
            iteration: Iteration number to update.
            status: New status string (if provided).
            cost: New cost value (if provided).
            duration: New duration value (if provided).
            task: New task description (if provided).

        Returns:
            Self for method chaining.
        """
        self.state.update_iteration_in_history(
            iteration, status=status, cost=cost, duration=duration, task=task
        )
        self.refresh()
        return self

    # --- Event handler integration ---

    def connect_events(self, emitter: EventEmitter) -> Dashboard:
        """Connect dashboard updates to an event emitter.

        Registers handlers for all relevant event types to update
        the dashboard state automatically.

        Args:
            emitter: The EventEmitter to connect to.

        Returns:
            Self for method chaining.
        """
        emitter.on(EventType.LOOP_START, self._on_loop_start)
        emitter.on(EventType.LOOP_END, self._on_loop_end)
        emitter.on(EventType.ITERATION_START, self._on_iteration_start)
        emitter.on(EventType.ITERATION_END, self._on_iteration_end)
        emitter.on(EventType.CLAUDE_INVOKE, self._on_claude_invoke)
        emitter.on(EventType.CLAUDE_RESPONSE, self._on_claude_response)
        emitter.on(EventType.CLAUDE_ERROR, self._on_claude_error)
        emitter.on(EventType.TASK_COMPLETE, self._on_task_complete)
        emitter.on(EventType.TASK_BLOCKED, self._on_task_blocked)
        emitter.on(EventType.COST_UPDATE, self._on_cost_update)
        emitter.on(EventType.COST_LIMIT_EXCEEDED, self._on_cost_limit_exceeded)
        emitter.on(EventType.LOG_MESSAGE, self._on_log_message)
        return self

    def _on_loop_start(self, event: Event) -> None:
        """Handle LOOP_START event."""
        self.state.is_running = True
        self.state.max_iterations = event.get("max_iterations", 10)
        self.state.max_cost = event.get("max_cost")
        self.state.status_message = "Loop started"
        self.refresh()

    def _on_loop_end(self, event: Event) -> None:
        """Handle LOOP_END event."""
        self.state.is_running = False
        status = event.get("status", "unknown")
        self.state.status_message = f"Loop ended: {status}"
        self.refresh()

    def _on_iteration_start(self, event: Event) -> None:
        """Handle ITERATION_START event."""
        self.state.iteration = event.get("iteration", 0)
        self.state.tasks_completed = event.get("completed", 0)
        self.state.tasks_total = event.get("total", 0)
        self.state.status_message = f"Starting iteration {self.state.iteration}"
        self.state.current_output = ""
        self.clear_error()

        # Add iteration to history with running status
        task = event.get("task", None)
        self.state.add_iteration_to_history(
            self.state.iteration,
            status="running",
            task=task,
        )
        self.refresh()

    def _on_iteration_end(self, event: Event) -> None:
        """Handle ITERATION_END event."""
        success = event.get("success", False)
        duration = event.get("duration", 0)
        cost = event.get("cost", None)
        self.state.status_message = (
            f"Iteration {self.state.iteration} completed "
            f"({'success' if success else 'failed'}, {duration:.1f}s)"
        )

        # Update iteration history with final status and duration
        self.state.update_iteration_in_history(
            self.state.iteration,
            status="success" if success else "failed",
            duration=duration,
            cost=cost,
        )
        self.refresh()

    def _on_claude_invoke(self, event: Event) -> None:
        """Handle CLAUDE_INVOKE event."""
        task = event.get("task", "")
        self.state.status_message = f"Invoking Claude: {task[:50]}..."
        self.refresh()

    def _on_claude_response(self, event: Event) -> None:
        """Handle CLAUDE_RESPONSE event."""
        cost = event.get("cost_usd", 0)
        self.state.cost += cost
        self.state.status_message = "Claude responded"
        self.refresh()

    def _on_claude_error(self, event: Event) -> None:
        """Handle CLAUDE_ERROR event."""
        return_code = event.get("return_code", 1)
        output = event.get("output", "")[:500]
        self.set_error(
            f"Claude invocation failed (code {return_code})",
            details=output if output else None,
        )

    def _on_task_complete(self, event: Event) -> None:
        """Handle TASK_COMPLETE event."""
        self.state.tasks_completed += 1
        task = event.get("task", "")
        self.state.status_message = f"Task completed: {task[:40]}..."
        # Clear active task
        self.state.active_task = None
        self.refresh()

    def _on_task_blocked(self, event: Event) -> None:
        """Handle TASK_BLOCKED event."""
        line_number = event.get("line_number")
        if line_number is not None:
            self.state.blocked_tasks.add(line_number)
        self.state.status_message = "Task blocked"
        self.refresh()

    def _on_cost_update(self, event: Event) -> None:
        """Handle COST_UPDATE event."""
        self.state.cost = event.get("total_cost", 0)
        iteration_cost = event.get("iteration_cost", None)

        # Update iteration history with the cost
        if iteration_cost is not None:
            self.state.update_iteration_in_history(
                self.state.iteration,
                cost=iteration_cost,
            )
        self.refresh()

    def _on_cost_limit_exceeded(self, event: Event) -> None:
        """Handle COST_LIMIT_EXCEEDED event."""
        total_cost = event.get("total_cost", 0)
        max_cost = event.get("max_cost", 0)
        self.set_error(
            f"Cost limit exceeded: ${total_cost:.4f} / ${max_cost:.2f}",
        )

    def _on_log_message(self, event: Event) -> None:
        """Handle LOG_MESSAGE event."""
        message = event.get("message", "")
        if message:
            self.log(message)

    # --- Context manager ---

    def __enter__(self) -> Dashboard:
        """Enter the live dashboard context.

        Returns:
            Self for use in with statement.
        """
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=self.refresh_per_second,
            screen=True,  # Use alternate screen buffer for fullscreen
            transient=False,
        )
        self._live.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the live dashboard context."""
        if self._live is not None:
            self._live.__exit__(exc_type, exc_val, exc_tb)
            self._live = None


def create_dashboard(
    console: Console,
    *,
    compact: bool = False,
    refresh_per_second: int = 4,
) -> Dashboard:
    """Create a dashboard instance.

    Factory function for creating Dashboard.

    Args:
        console: Rich Console to use for output.
        compact: Use compact layout for narrow terminals.
        refresh_per_second: How often to refresh the display.

    Returns:
        A configured Dashboard instance.
    """
    return Dashboard(
        console,
        compact=compact,
        refresh_per_second=refresh_per_second,
    )
