"""Enhanced status rendering for zoyd status command.

Provides rich status display with task tree and progress bar
for the `zoyd status` command.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Group
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from zoyd.prd import Task
from zoyd.tui.task_tree import render_task_tree, render_task_summary
from zoyd.tui.theme import COLORS

if TYPE_CHECKING:
    from rich.console import Console, RenderableType


def create_progress_bar(
    completed: int,
    total: int,
    *,
    description: str = "Progress",
    bar_width: int | None = 40,
) -> Progress:
    """Create a progress bar showing task completion.

    Args:
        completed: Number of completed tasks.
        total: Total number of tasks.
        description: Label for the progress bar.
        bar_width: Width of the bar in characters. None for auto-sizing.

    Returns:
        A Rich Progress object configured for display.
    """
    progress = Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=bar_width, complete_style="bar.complete", finished_style="bar.finished"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn(f"[dim]({completed}/{total})"),
        expand=False,
    )
    task_id = progress.add_task(description, total=total, completed=completed)
    return progress


def create_status_table(
    *,
    prd_path: Path | str | None = None,
    iterations: int = 0,
    status: str = "in_progress",
    next_task: str | None = None,
) -> Table:
    """Create a status information table.

    Args:
        prd_path: Path to the PRD file.
        iterations: Number of iterations completed.
        status: Current status ("complete" or "in_progress").
        next_task: Text of the next incomplete task.

    Returns:
        A Rich Table with status information.
    """
    table = Table(
        show_header=False,
        show_edge=False,
        box=None,
        padding=(0, 2),
        expand=True,
    )
    table.add_column("Label", style="dim")
    table.add_column("Value")

    if prd_path:
        table.add_row("PRD:", str(prd_path))

    if iterations > 0:
        table.add_row("Iterations:", str(iterations))

    # Status with color coding
    if status == "complete":
        status_text = Text("COMPLETE", style="success")
    else:
        status_text = Text("IN PROGRESS", style="warning")
    table.add_row("Status:", status_text)

    if next_task and status != "complete":
        table.add_row("Next task:", Text(next_task, style="zoyd.task.active"))

    return table


def render_status(
    tasks: list[Task],
    *,
    prd_path: Path | str | None = None,
    iterations: int = 0,
    show_tree: bool = True,
    show_progress: bool = True,
    show_line_numbers: bool = False,
    active_task: Task | None = None,
    blocked_tasks: set[int] | None = None,
) -> Panel:
    """Render complete status display with tree and progress bar.

    Creates a comprehensive status view including:
    - Task tree with completion icons
    - Progress bar showing completion percentage
    - Status information (iterations, next task, etc.)

    Args:
        tasks: List of Task objects from the PRD.
        prd_path: Path to the PRD file.
        iterations: Number of iterations completed.
        show_tree: Whether to show the task tree.
        show_progress: Whether to show the progress bar.
        show_line_numbers: Whether to show line numbers in task tree.
        active_task: Currently active task (for highlighting).
        blocked_tasks: Set of line numbers for blocked tasks.

    Returns:
        A Rich Panel containing the complete status display.
    """
    completed = sum(1 for t in tasks if t.complete)
    total = len(tasks)
    is_complete = completed == total and total > 0
    next_task_obj = next((t for t in tasks if not t.complete), None)

    components: list[RenderableType] = []

    # Add task tree
    if show_tree and tasks:
        tree = render_task_tree(
            tasks,
            title="Tasks",
            active_task=active_task,
            blocked_tasks=blocked_tasks,
            show_line_numbers=show_line_numbers,
        )
        components.append(tree)
        components.append(Text())  # Spacer

    # Add progress bar
    if show_progress:
        if total > 0:
            progress = create_progress_bar(completed, total)
            components.append(progress)
        else:
            components.append(Text("No tasks defined", style="dim"))
        components.append(Text())  # Spacer

    # Add status table
    status_table = create_status_table(
        prd_path=prd_path,
        iterations=iterations,
        status="complete" if is_complete else "in_progress",
        next_task=next_task_obj.text if next_task_obj else None,
    )
    components.append(status_table)

    # Combine all components
    content = Group(*components)

    return Panel(
        content,
        title="[panel.title]Zoyd Status[/]",
        border_style=COLORS["twilight"],
        padding=(1, 2),
    )


def print_status(
    console: Console,
    tasks: list[Task],
    *,
    prd_path: Path | str | None = None,
    iterations: int = 0,
    show_tree: bool = True,
    show_progress: bool = True,
    show_line_numbers: bool = False,
    active_task: Task | None = None,
    blocked_tasks: set[int] | None = None,
) -> None:
    """Print the status display to the console.

    Args:
        console: Rich Console to print to.
        tasks: List of Task objects from the PRD.
        prd_path: Path to the PRD file.
        iterations: Number of iterations completed.
        show_tree: Whether to show the task tree.
        show_progress: Whether to show the progress bar.
        show_line_numbers: Whether to show line numbers in task tree.
        active_task: Currently active task.
        blocked_tasks: Set of line numbers for blocked tasks.
    """
    panel = render_status(
        tasks,
        prd_path=prd_path,
        iterations=iterations,
        show_tree=show_tree,
        show_progress=show_progress,
        show_line_numbers=show_line_numbers,
        active_task=active_task,
        blocked_tasks=blocked_tasks,
    )
    console.print(panel)


def get_status_summary(tasks: list[Task]) -> dict:
    """Get a summary of task status for programmatic use.

    Args:
        tasks: List of Task objects.

    Returns:
        Dictionary with completed, total, percentage, and is_complete fields.
    """
    completed = sum(1 for t in tasks if t.complete)
    total = len(tasks)
    percentage = (completed / total * 100) if total > 0 else 0
    is_complete = completed == total and total > 0

    return {
        "completed": completed,
        "total": total,
        "percentage": percentage,
        "is_complete": is_complete,
    }
