"""Task tree visualization using Rich Tree component.

Renders PRD tasks as a styled tree with icons indicating task status:
- Completed tasks
- Pending tasks
- Active (in-progress) tasks
- Blocked tasks
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.tree import Tree

from zoyd.prd import Task
from zoyd.tui.theme import get_task_style

if TYPE_CHECKING:
    from rich.console import Console, RenderableType

# Task status icons
ICONS = {
    "complete": "[zoyd.task.complete]\u2713[/]",  # Checkmark
    "pending": "[zoyd.task.pending]\u25cb[/]",  # Empty circle
    "active": "[zoyd.task.active]\u25c9[/]",  # Circled dot (fisheye)
    "blocked": "[zoyd.task.blocked]\u2717[/]",  # X mark
}


def get_task_icon(complete: bool, active: bool = False, blocked: bool = False) -> str:
    """Get the appropriate icon for a task based on its state.

    Args:
        complete: Whether the task is complete.
        active: Whether the task is currently being worked on.
        blocked: Whether the task is blocked.

    Returns:
        The styled icon string for the task state.
    """
    if blocked:
        return ICONS["blocked"]
    if complete:
        return ICONS["complete"]
    if active:
        return ICONS["active"]
    return ICONS["pending"]


def render_task_tree(
    tasks: list[Task],
    *,
    title: str = "Tasks",
    active_task: Task | None = None,
    blocked_tasks: set[int] | None = None,
    show_line_numbers: bool = False,
) -> Tree:
    """Render tasks as a Rich Tree structure.

    Creates a hierarchical tree visualization of tasks with styled icons
    indicating their completion status.

    Args:
        tasks: List of Task objects to render.
        title: Title for the tree root node.
        active_task: The currently active task (shown with active icon).
        blocked_tasks: Set of line numbers for blocked tasks.
        show_line_numbers: Whether to show line numbers with tasks.

    Returns:
        A Rich Tree object ready for rendering.
    """
    blocked_set = blocked_tasks or set()

    # Create the root tree with the title
    tree = Tree(f"[bold]{title}[/]")

    for task in tasks:
        is_blocked = task.line_number in blocked_set
        is_active = active_task is not None and task.line_number == active_task.line_number

        # Get icon and style for this task
        icon = get_task_icon(task.complete, active=is_active, blocked=is_blocked)
        style = get_task_style(task.complete, active=is_active, blocked=is_blocked)

        # Build the task label
        if show_line_numbers:
            label = f"{icon} [{style}]L{task.line_number}: {task.text}[/]"
        else:
            label = f"{icon} [{style}]{task.text}[/]"

        tree.add(label)

    return tree


def render_task_summary(
    completed: int,
    total: int,
    *,
    show_percentage: bool = True,
) -> str:
    """Render a task completion summary string.

    Args:
        completed: Number of completed tasks.
        total: Total number of tasks.
        show_percentage: Whether to include percentage.

    Returns:
        Formatted summary string like "5/10 tasks (50%)".
    """
    if total == 0:
        return "No tasks"

    if show_percentage:
        percentage = (completed / total) * 100
        return f"{completed}/{total} tasks ({percentage:.0f}%)"

    return f"{completed}/{total} tasks"


def print_task_tree(
    console: Console,
    tasks: list[Task],
    *,
    title: str = "Tasks",
    active_task: Task | None = None,
    blocked_tasks: set[int] | None = None,
    show_line_numbers: bool = False,
    show_summary: bool = True,
) -> None:
    """Print a task tree to the console with optional summary.

    Args:
        console: Rich Console to print to.
        tasks: List of Task objects to render.
        title: Title for the tree root node.
        active_task: The currently active task.
        blocked_tasks: Set of line numbers for blocked tasks.
        show_line_numbers: Whether to show line numbers.
        show_summary: Whether to show completion summary after tree.
    """
    tree = render_task_tree(
        tasks,
        title=title,
        active_task=active_task,
        blocked_tasks=blocked_tasks,
        show_line_numbers=show_line_numbers,
    )

    console.print(tree)

    if show_summary and tasks:
        completed = sum(1 for t in tasks if t.complete)
        summary = render_task_summary(completed, len(tasks))
        console.print(f"\n[dim]{summary}[/]")
