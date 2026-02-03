"""Data display panel components for the Zoyd TUI.

Provides panels for displaying iteration history and git commit logs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from zoyd.tui.theme import COLORS

if TYPE_CHECKING:
    from rich.console import Console


class IterationHistoryPanel:
    """A panel for displaying recent iteration history.

    Shows a table of recent iterations with their status, cost, and duration.
    Useful for tracking progress and identifying patterns in the loop execution.
    """

    # Status icons
    STATUS_ICONS = {
        "success": "[success]✓[/]",
        "failed": "[error]✗[/]",
        "running": "[active]◉[/]",
        "pending": "[dim]○[/]",
    }

    def __init__(
        self,
        title: str = "History",
        *,
        max_items: int = 10,
    ) -> None:
        """Initialize the iteration history panel.

        Args:
            title: Title for the panel.
            max_items: Maximum number of iterations to display.
        """
        self.title = title
        self.max_items = max_items
        self._items: list[dict] = []

    def add_iteration(
        self,
        iteration: int,
        *,
        status: str = "pending",
        cost: float | None = None,
        duration: float | None = None,
        task: str | None = None,
    ) -> "IterationHistoryPanel":
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
        item = {
            "iteration": iteration,
            "status": status,
            "cost": cost,
            "duration": duration,
            "task": task,
        }
        self._items.append(item)

        # Trim to max items
        if len(self._items) > self.max_items:
            self._items = self._items[-self.max_items :]

        return self

    def update_iteration(
        self,
        iteration: int,
        *,
        status: str | None = None,
        cost: float | None = None,
        duration: float | None = None,
        task: str | None = None,
    ) -> "IterationHistoryPanel":
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
        for item in self._items:
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
        return self

    def clear(self) -> "IterationHistoryPanel":
        """Clear all iteration history.

        Returns:
            Self for method chaining.
        """
        self._items = []
        return self

    def _format_duration(self, seconds: float | None) -> str:
        """Format duration in seconds to a readable string.

        Args:
            seconds: Duration in seconds, or None.

        Returns:
            Formatted duration string.
        """
        if seconds is None:
            return "-"
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"

    def _format_cost(self, cost: float | None) -> str:
        """Format cost in USD to a readable string.

        Args:
            cost: Cost in USD, or None.

        Returns:
            Formatted cost string.
        """
        if cost is None:
            return "-"
        return f"${cost:.4f}"

    def _truncate_task(self, task: str | None, max_len: int = 30) -> str:
        """Truncate task text to fit in the display.

        Args:
            task: Task description, or None.
            max_len: Maximum length before truncation.

        Returns:
            Truncated task string.
        """
        if task is None:
            return "-"
        if len(task) <= max_len:
            return task
        return task[: max_len - 3] + "..."

    def render(self) -> Panel:
        """Render the iteration history panel.

        Returns:
            A Rich Panel containing the iteration history table.
        """
        table = Table(
            show_header=True,
            show_edge=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )

        # Define columns
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Status", width=7, justify="center")
        table.add_column("Cost", width=10, justify="right")
        table.add_column("Duration", width=10, justify="right")
        table.add_column("Task", ratio=1)

        # Add rows
        if not self._items:
            # Show placeholder when empty
            return Panel(
                Text("No iterations yet", style="dim"),
                title=f"[panel.title]{self.title}[/]",
                border_style=COLORS["twilight"],
                padding=(0, 1),
            )

        for item in self._items:
            status_icon = self.STATUS_ICONS.get(item["status"], "[dim]?[/]")
            table.add_row(
                str(item["iteration"]),
                status_icon,
                self._format_cost(item["cost"]),
                self._format_duration(item["duration"]),
                self._truncate_task(item["task"]),
            )

        return Panel(
            table,
            title=f"[panel.title]{self.title}[/]",
            border_style=COLORS["twilight"],
            padding=(0, 1),
        )

    def print(self, console: Console) -> None:
        """Print the iteration history panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


class GitCommitLogPanel:
    """A panel for displaying recent git commits from the session.

    Shows a table of commits made during the zoyd session with their
    iteration number, shortened hash, and commit message.
    """

    def __init__(
        self,
        title: str = "Git Commits",
        *,
        max_items: int = 10,
    ) -> None:
        """Initialize the git commit log panel.

        Args:
            title: Title for the panel.
            max_items: Maximum number of commits to display.
        """
        self.title = title
        self.max_items = max_items
        self._commits: list[dict] = []

    def add_commit(
        self,
        *,
        iteration: int,
        message: str,
        commit_hash: str | None = None,
    ) -> "GitCommitLogPanel":
        """Add a commit to the log.

        Args:
            iteration: Iteration number when commit was made.
            message: Commit message (first line).
            commit_hash: Short commit hash (optional).

        Returns:
            Self for method chaining.
        """
        commit = {
            "iteration": iteration,
            "message": message,
            "hash": commit_hash,
        }
        self._commits.append(commit)

        # Trim to max items
        if len(self._commits) > self.max_items:
            self._commits = self._commits[-self.max_items :]

        return self

    def clear(self) -> "GitCommitLogPanel":
        """Clear all commits from the log.

        Returns:
            Self for method chaining.
        """
        self._commits = []
        return self

    def _truncate_message(self, message: str, max_len: int = 50) -> str:
        """Truncate commit message to fit in the display.

        Args:
            message: Commit message.
            max_len: Maximum length before truncation.

        Returns:
            Truncated message string.
        """
        if len(message) <= max_len:
            return message
        return message[: max_len - 3] + "..."

    def render(self) -> Panel:
        """Render the git commit log panel.

        Returns:
            A Rich Panel containing the commit log table.
        """
        if not self._commits:
            return Panel(
                Text("No commits yet", style="dim"),
                title=f"[panel.title]{self.title}[/]",
                border_style=COLORS["twilight"],
                padding=(0, 1),
            )

        table = Table(
            show_header=True,
            show_edge=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )

        # Define columns
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Hash", style=COLORS["amethyst"], width=8)
        table.add_column("Message", ratio=1)

        # Add rows
        for commit in self._commits:
            hash_display = commit["hash"][:7] if commit["hash"] else "-"
            table.add_row(
                str(commit["iteration"]),
                hash_display,
                self._truncate_message(commit["message"]),
            )

        return Panel(
            table,
            title=f"[panel.title]{self.title}[/]",
            border_style=COLORS["twilight"],
            padding=(0, 1),
        )

    def print(self, console: Console) -> None:
        """Print the git commit log panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


def create_iteration_history_panel(
    *,
    title: str = "History",
    max_items: int = 10,
) -> IterationHistoryPanel:
    """Create an iteration history panel.

    Factory function for creating IterationHistoryPanel.

    Args:
        title: Title for the panel.
        max_items: Maximum number of iterations to display.

    Returns:
        A configured IterationHistoryPanel instance.
    """
    return IterationHistoryPanel(title=title, max_items=max_items)


def create_git_commit_log_panel(
    *,
    title: str = "Git Commits",
    max_items: int = 10,
) -> GitCommitLogPanel:
    """Create a git commit log panel.

    Factory function for creating GitCommitLogPanel.

    Args:
        title: Title for the panel.
        max_items: Maximum number of commits to display.

    Returns:
        A configured GitCommitLogPanel instance.
    """
    return GitCommitLogPanel(title=title, max_items=max_items)