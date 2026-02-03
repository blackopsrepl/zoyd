"""Specialized panel components for the Zoyd TUI.

Provides specialized panels for specific use cases that require
more domain-specific functionality than the general-purpose panels.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.text import Text

from zoyd.tui.theme import COLORS

if TYPE_CHECKING:
    from rich.console import Console


class BlockedTaskPanel:
    """A panel for displaying blocked tasks with warning styling and suggestions.

    Used when a task cannot be completed due to missing dependencies,
    unclear requirements, or other blockers. Provides context about what's
    blocking the task and suggestions for how to proceed.
    """

    def __init__(
        self,
        title: str = "Task Blocked",
        *,
        show_icon: bool = True,
    ) -> None:
        """Initialize the blocked task panel.

        Args:
            title: Title for the panel.
            show_icon: Whether to show a blocked/stop icon in the title.
        """
        self.title = title
        self.show_icon = show_icon
        self._task: str | None = None
        self._reason: str | None = None
        self._blockers: list[str] = []
        self._suggestions: list[str] = []

    def set_task(self, task: str) -> "BlockedTaskPanel":
        """Set the blocked task description.

        Args:
            task: The task that is blocked.

        Returns:
            Self for method chaining.
        """
        self._task = task
        return self

    def set_reason(self, reason: str) -> "BlockedTaskPanel":
        """Set the reason why the task is blocked.

        Args:
            reason: Why the task cannot be completed.

        Returns:
            Self for method chaining.
        """
        self._reason = reason
        return self

    def add_blocker(self, blocker: str) -> "BlockedTaskPanel":
        """Add a specific blocker preventing task completion.

        Args:
            blocker: A specific issue blocking the task.

        Returns:
            Self for method chaining.
        """
        self._blockers.append(blocker)
        return self

    def add_suggestion(self, suggestion: str) -> "BlockedTaskPanel":
        """Add a suggestion for how to resolve the blocker.

        Args:
            suggestion: A suggested action to unblock the task.

        Returns:
            Self for method chaining.
        """
        self._suggestions.append(suggestion)
        return self

    def clear(self) -> "BlockedTaskPanel":
        """Clear all content from the panel.

        Returns:
            Self for method chaining.
        """
        self._task = None
        self._reason = None
        self._blockers = []
        self._suggestions = []
        return self

    def render(self) -> Panel:
        """Render the blocked task panel.

        Returns:
            A Rich Panel with blocked/warning styling.
        """
        parts = []

        # Task description
        if self._task:
            parts.append(
                Text.assemble(
                    ("Task: ", "bold"),
                    (self._task, COLORS["mist"]),
                )
            )

        # Reason for blocking
        if self._reason:
            if parts:
                parts.append(Text())  # Empty line
            parts.append(
                Text.assemble(
                    ("Reason: ", "bold"),
                    (self._reason, COLORS["warning"]),
                )
            )

        # List of blockers
        if self._blockers:
            if parts:
                parts.append(Text())  # Empty line
            parts.append(Text("Blockers:", style="bold"))
            for blocker in self._blockers:
                parts.append(Text(f"  • {blocker}", style="dim"))

        # List of suggestions
        if self._suggestions:
            if parts:
                parts.append(Text())  # Empty line
            parts.append(Text("Suggestions:", style="bold"))
            for suggestion in self._suggestions:
                parts.append(
                    Text.assemble(
                        ("  → ", COLORS["success"]),
                        (suggestion, ""),
                    )
                )

        content = Text("\n").join(parts) if parts else Text("Task is blocked")

        title = self.title
        if self.show_icon:
            title = f"[{COLORS['blocked']}]⊘[/] {title}"

        return Panel(
            content,
            title=f"[{COLORS['blocked']}]{title}[/]",
            border_style=COLORS["blocked"],
            padding=(1, 2),
        )

    def print(self, console: Console) -> None:
        """Print the blocked task panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


def create_blocked_task_panel(
    task: str,
    *,
    reason: str | None = None,
    blockers: list[str] | None = None,
    suggestions: list[str] | None = None,
    title: str = "Task Blocked",
) -> BlockedTaskPanel:
    """Create a blocked task panel with content.

    Factory function for creating BlockedTaskPanel with pre-populated content.

    Args:
        task: The task that is blocked.
        reason: Why the task is blocked (optional).
        blockers: List of specific blockers (optional).
        suggestions: List of suggested actions (optional).
        title: Title for the panel.

    Returns:
        A configured BlockedTaskPanel instance.
    """
    panel = BlockedTaskPanel(title=title).set_task(task)

    if reason:
        panel.set_reason(reason)

    if blockers:
        for blocker in blockers:
            panel.add_blocker(blocker)

    if suggestions:
        for suggestion in suggestions:
            panel.add_suggestion(suggestion)

    return panel