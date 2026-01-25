"""Multi-progress bar panel for the Zoyd TUI.

Provides progress visualization for:
- Task completion (completed/total tasks)
- Iteration progress (current/max iterations)
- Cost budget (current/max cost in USD)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Group
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table
from rich.text import Text

from zoyd.tui.theme import COLORS, get_cost_style

if TYPE_CHECKING:
    from rich.console import Console


class ProgressPanel:
    """A panel displaying multiple progress bars.

    Shows progress for tasks, iterations, and cost in a unified panel.
    Each progress indicator uses theme-appropriate styling.
    """

    def __init__(self, title: str = "Progress") -> None:
        """Initialize the progress panel.

        Args:
            title: Title for the progress panel.
        """
        self.title = title
        self._task_completed: int = 0
        self._task_total: int = 0
        self._iteration_current: int = 0
        self._iteration_max: int | None = None
        self._cost_current: float | None = None
        self._cost_max: float | None = None

    def set_tasks(self, completed: int, total: int) -> ProgressPanel:
        """Set task completion progress.

        Args:
            completed: Number of completed tasks.
            total: Total number of tasks.

        Returns:
            Self for method chaining.
        """
        self._task_completed = completed
        self._task_total = total
        return self

    def set_iteration(
        self, current: int, max_iterations: int | None = None
    ) -> ProgressPanel:
        """Set iteration progress.

        Args:
            current: Current iteration number.
            max_iterations: Maximum iterations allowed (None for unlimited).

        Returns:
            Self for method chaining.
        """
        self._iteration_current = current
        self._iteration_max = max_iterations
        return self

    def set_cost(
        self, current: float | None, max_cost: float | None = None
    ) -> ProgressPanel:
        """Set cost progress.

        Args:
            current: Current cost in USD (None if not tracking).
            max_cost: Maximum cost limit in USD (None for unlimited).

        Returns:
            Self for method chaining.
        """
        self._cost_current = current
        self._cost_max = max_cost
        return self

    def _create_task_progress(self) -> Progress | Text:
        """Create the task completion progress bar.

        Returns:
            A Rich Progress object or Text placeholder.
        """
        if self._task_total == 0:
            return Text("No tasks defined", style="dim")

        progress = Progress(
            TextColumn("[bold]Tasks"),
            BarColumn(
                bar_width=30,
                complete_style="bar.complete",
                finished_style="bar.finished",
            ),
            TaskProgressColumn(),
            TextColumn(f"[dim]({self._task_completed}/{self._task_total})"),
            expand=False,
        )
        progress.add_task(
            "Tasks",
            total=self._task_total,
            completed=self._task_completed,
        )
        return progress

    def _create_iteration_progress(self) -> Progress | Text:
        """Create the iteration progress bar.

        Returns:
            A Rich Progress object or Text placeholder.
        """
        if self._iteration_max is None:
            # No max iterations - just show count
            return Text(f"Iteration: {self._iteration_current}", style="zoyd.iteration")

        progress = Progress(
            TextColumn("[bold]Iteration"),
            BarColumn(
                bar_width=30,
                complete_style="bar.complete",
                finished_style="bar.finished",
            ),
            TaskProgressColumn(),
            TextColumn(
                f"[dim]({self._iteration_current}/{self._iteration_max})"
            ),
            expand=False,
        )
        progress.add_task(
            "Iteration",
            total=self._iteration_max,
            completed=self._iteration_current,
        )
        return progress

    def _create_cost_gauge(self) -> Text | Progress:
        """Create the cost budget gauge.

        Returns:
            A Text or Progress object showing cost status.
        """
        if self._cost_current is None and self._cost_max is None:
            return Text("Cost tracking: disabled", style="dim")

        if self._cost_max is None:
            # Tracking cost but no limit
            cost_str = f"${self._cost_current:.4f}" if self._cost_current else "$0.0000"
            return Text(f"Cost: {cost_str}", style="zoyd.cost.low")

        # Have both current and max - show gauge
        current = self._cost_current or 0.0
        style = get_cost_style(current, self._cost_max)

        progress = Progress(
            TextColumn("[bold]Cost"),
            BarColumn(
                bar_width=30,
                complete_style=style,
                finished_style="zoyd.cost.high",
            ),
            TaskProgressColumn(),
            TextColumn(f"[dim](${current:.4f}/${self._cost_max:.2f})"),
            expand=False,
        )
        # Use max_cost as total, current as completed
        progress.add_task(
            "Cost",
            total=self._cost_max,
            completed=min(current, self._cost_max),
        )
        return progress

    def render(self) -> Panel:
        """Render the progress panel with all progress indicators.

        Returns:
            A Rich Panel containing all progress bars.
        """
        components = []

        # Task progress
        components.append(self._create_task_progress())

        # Iteration progress
        components.append(Text())  # Spacer
        components.append(self._create_iteration_progress())

        # Cost gauge (only if cost tracking is enabled)
        if self._cost_current is not None or self._cost_max is not None:
            components.append(Text())  # Spacer
            components.append(self._create_cost_gauge())

        content = Group(*components)

        return Panel(
            content,
            title=f"[panel.title]{self.title}[/]",
            border_style=COLORS["twilight"],
            padding=(1, 2),
        )

    def print(self, console: Console) -> None:
        """Print the progress panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


class CostGauge:
    """A standalone cost budget gauge visualization.

    Displays cost as a horizontal bar with color-coded thresholds:
    - Green (low): Under 50% of budget
    - Yellow (medium): 50-80% of budget
    - Red (high): Over 80% of budget
    """

    def __init__(
        self,
        current: float = 0.0,
        max_cost: float | None = None,
        *,
        show_percentage: bool = True,
        show_values: bool = True,
        bar_width: int = 30,
    ) -> None:
        """Initialize the cost gauge.

        Args:
            current: Current cost in USD.
            max_cost: Maximum cost limit in USD (None for unlimited).
            show_percentage: Whether to show percentage.
            show_values: Whether to show dollar values.
            bar_width: Width of the bar in characters.
        """
        self.current = current
        self.max_cost = max_cost
        self.show_percentage = show_percentage
        self.show_values = show_values
        self.bar_width = bar_width

    def update(self, current: float, max_cost: float | None = None) -> CostGauge:
        """Update the gauge values.

        Args:
            current: New current cost.
            max_cost: New max cost (or None to keep existing).

        Returns:
            Self for method chaining.
        """
        self.current = current
        if max_cost is not None:
            self.max_cost = max_cost
        return self

    def get_style(self) -> str:
        """Get the appropriate style based on budget usage.

        Returns:
            Style name for the current cost level.
        """
        if self.max_cost is None or self.max_cost <= 0:
            return "zoyd.cost.low"
        return get_cost_style(self.current, self.max_cost)

    def render(self) -> Text | Progress:
        """Render the cost gauge.

        Returns:
            A Rich Text or Progress object.
        """
        if self.max_cost is None:
            # No limit - just show current cost
            cost_str = f"${self.current:.4f}"
            return Text(f"Cost: {cost_str}", style=self.get_style())

        style = self.get_style()

        columns = [TextColumn("[bold]Cost")]

        columns.append(
            BarColumn(
                bar_width=self.bar_width,
                complete_style=style,
                finished_style="zoyd.cost.high",
            )
        )

        if self.show_percentage:
            columns.append(TaskProgressColumn())

        if self.show_values:
            columns.append(
                TextColumn(f"[dim](${self.current:.4f}/${self.max_cost:.2f})")
            )

        progress = Progress(*columns, expand=False)
        progress.add_task(
            "Cost",
            total=self.max_cost,
            completed=min(self.current, self.max_cost),
        )
        return progress

    def render_compact(self) -> Text:
        """Render a compact text-only version.

        Returns:
            A Rich Text object with styled cost display.
        """
        style = self.get_style()
        if self.max_cost is None:
            return Text(f"${self.current:.4f}", style=style)

        ratio = self.current / self.max_cost if self.max_cost > 0 else 0
        percentage = min(ratio * 100, 100)
        return Text(
            f"${self.current:.4f}/${self.max_cost:.2f} ({percentage:.0f}%)",
            style=style,
        )

    def print(self, console: Console) -> None:
        """Print the gauge to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


def create_progress_panel(
    *,
    task_completed: int = 0,
    task_total: int = 0,
    iteration: int = 0,
    max_iterations: int | None = None,
    cost: float | None = None,
    max_cost: float | None = None,
    title: str = "Progress",
) -> ProgressPanel:
    """Create a configured progress panel.

    Factory function for creating a ProgressPanel with common settings.

    Args:
        task_completed: Number of completed tasks.
        task_total: Total number of tasks.
        iteration: Current iteration number.
        max_iterations: Maximum iterations allowed.
        cost: Current cost in USD.
        max_cost: Maximum cost limit in USD.
        title: Title for the panel.

    Returns:
        A configured ProgressPanel instance.
    """
    panel = ProgressPanel(title=title)
    panel.set_tasks(task_completed, task_total)
    panel.set_iteration(iteration, max_iterations)
    panel.set_cost(cost, max_cost)
    return panel


def create_cost_gauge(
    current: float = 0.0,
    max_cost: float | None = None,
    *,
    show_percentage: bool = True,
    show_values: bool = True,
    bar_width: int = 30,
) -> CostGauge:
    """Create a cost gauge.

    Factory function for creating a CostGauge.

    Args:
        current: Current cost in USD.
        max_cost: Maximum cost limit in USD.
        show_percentage: Whether to show percentage.
        show_values: Whether to show dollar values.
        bar_width: Width of the bar in characters.

    Returns:
        A configured CostGauge instance.
    """
    return CostGauge(
        current=current,
        max_cost=max_cost,
        show_percentage=show_percentage,
        show_values=show_values,
        bar_width=bar_width,
    )
