"""Factory functions for creating panel components.

Provides convenient factory functions for creating pre-configured panel instances
with common patterns and default settings.

This module consolidates all factory functions from the original panels.py file.
Some factory functions already exist in other modules and are re-exported here
for convenience.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import RenderableType

# Import panel classes and existing factory functions
from zoyd.tui.panels.core import (
    StatusBar,
    OutputPanel,
    ClaudeOutputPanel,
)
from zoyd.tui.panels.alerts import (
    ErrorPanel,
    WarningPanel,
)
from zoyd.tui.panels.data_display import (
    IterationHistoryPanel,
    GitCommitLogPanel,
    create_iteration_history_panel,
    create_git_commit_log_panel,
)
from zoyd.tui.panels.specialized import (
    BlockedTaskPanel,
    create_blocked_task_panel,
)


def create_status_bar(
    *,
    task: str | None = None,
    completed: int = 0,
    total: int = 0,
    iteration: int | None = None,
    max_iterations: int | None = None,
    model: str | None = None,
    cost: float | None = None,
    max_cost: float | None = None,
) -> StatusBar:
    """Create a status bar with common loop runner information.

    Args:
        task: Current task description.
        completed: Number of completed tasks.
        total: Total number of tasks.
        iteration: Current iteration number.
        max_iterations: Maximum iterations allowed.
        model: Claude model being used.
        cost: Current cost in USD.
        max_cost: Maximum cost limit in USD.

    Returns:
        A configured StatusBar instance.
    """
    bar = StatusBar(title="Status")

    if task:
        bar.add_item("Task", task)

    if total > 0:
        bar.add_item("Completed", f"{completed}/{total}")

    if iteration is not None:
        if max_iterations is not None:
            bar.add_item("Iteration", f"{iteration}/{max_iterations}")
        else:
            bar.add_item("Iteration", str(iteration))

    if model:
        bar.add_item("Model", model)

    if cost is not None:
        cost_str = f"${cost:.4f}"
        if max_cost is not None:
            cost_str = f"${cost:.4f}/${max_cost:.2f}"
            # Color based on budget usage
            ratio = cost / max_cost if max_cost > 0 else 0
            if ratio < 0.5:
                style = "success"
            elif ratio < 0.8:
                style = "warning"
            else:
                style = "error"
            bar.add_item("Cost", cost_str, style)
        else:
            bar.add_item("Cost", cost_str)
    elif max_cost is not None:
        # Show cost limit even when current cost is unknown
        bar.add_item("Cost Limit", f"${max_cost:.2f}")

    return bar


def create_output_panel(
    content: "RenderableType",
    *,
    title: str = "Output",
    subtitle: str | None = None,
) -> OutputPanel:
    """Create an output panel with content.

    Args:
        content: The content to display.
        title: Title for the panel.
        subtitle: Optional subtitle.

    Returns:
        A configured OutputPanel instance.
    """
    return OutputPanel(title=title, subtitle=subtitle).set_content(content)


def create_error_panel(
    message: str,
    *,
    title: str = "Error",
    details: str | None = None,
    suggestion: str | None = None,
) -> ErrorPanel:
    """Create an error panel with a message.

    Args:
        message: The main error message.
        title: Title for the panel.
        details: Optional additional details.
        suggestion: Optional suggestion for resolution.

    Returns:
        A configured ErrorPanel instance.
    """
    panel = ErrorPanel(title=title).set_message(message)
    if details:
        panel.set_details(details)
    if suggestion:
        panel.set_suggestion(suggestion)
    return panel


def create_warning_panel(
    items: list[tuple[str, str | None]],
    *,
    title: str = "Warning",
) -> WarningPanel:
    """Create a warning panel with items.

    Args:
        items: List of (message, detail) tuples. Detail can be None.
        title: Title for the panel.

    Returns:
        A configured WarningPanel instance.
    """
    panel = WarningPanel(title=title)
    for message, detail in items:
        panel.add_item(message, detail)
    return panel


def create_claude_output_panel(
    content: str = "",
    *,
    title: str = "Claude Output",
    subtitle: str | None = None,
    use_markdown: bool = True,
    code_theme: str = "dracula",
) -> ClaudeOutputPanel:
    """Create a Claude output panel with markdown content.

    Args:
        content: Markdown text from Claude's output.
        title: Title for the panel.
        subtitle: Optional subtitle (e.g., iteration number).
        use_markdown: Whether to render content as markdown.
        code_theme: Pygments theme for syntax highlighting (default: dracula).

    Returns:
        A configured ClaudeOutputPanel instance.
    """
    panel = ClaudeOutputPanel(title=title, subtitle=subtitle, code_theme=code_theme)
    panel.set_content(content)
    panel.set_markdown(use_markdown)
    return panel


# Re-export factory functions from other modules for convenience
__all__ = [
    "create_status_bar",
    "create_output_panel", 
    "create_error_panel",
    "create_warning_panel",
    "create_claude_output_panel",
    "create_iteration_history_panel",
    "create_git_commit_log_panel", 
    "create_blocked_task_panel",
]