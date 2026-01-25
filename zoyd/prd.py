"""PRD parsing - extract tasks from markdown checkboxes."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Task:
    """A task extracted from a PRD."""
    text: str
    complete: bool
    line_number: int


# Matches markdown checkboxes: - [ ] or - [x] or - [X]
CHECKBOX_PATTERN = re.compile(r"^(\s*-\s*\[)([ xX])(\]\s*)(.*)$")


def parse_tasks(content: str) -> list[Task]:
    """Parse markdown content and extract checkbox tasks.

    Args:
        content: Markdown content to parse.

    Returns:
        List of Task objects with text, completion status, and line numbers.
    """
    tasks = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        match = CHECKBOX_PATTERN.match(line)
        if match:
            checkbox_char = match.group(2)
            task_text = match.group(4).strip()
            complete = checkbox_char.lower() == "x"
            tasks.append(Task(text=task_text, complete=complete, line_number=line_number))
    return tasks


def read_prd(path: Path) -> str:
    """Read PRD file content.

    Args:
        path: Path to the PRD file.

    Returns:
        Content of the PRD file.

    Raises:
        FileNotFoundError: If the PRD file doesn't exist.
    """
    return path.read_text()


def get_completion_status(tasks: list[Task]) -> tuple[int, int]:
    """Get completion counts from tasks.

    Args:
        tasks: List of Task objects.

    Returns:
        Tuple of (completed_count, total_count).
    """
    completed = sum(1 for t in tasks if t.complete)
    return completed, len(tasks)


def is_all_complete(tasks: list[Task]) -> bool:
    """Check if all tasks are complete.

    Args:
        tasks: List of Task objects.

    Returns:
        True if all tasks are complete (or no tasks exist).
    """
    if not tasks:
        return True
    return all(t.complete for t in tasks)


def get_next_incomplete_task(tasks: list[Task]) -> Task | None:
    """Get the first incomplete task.

    Args:
        tasks: List of Task objects.

    Returns:
        First incomplete Task, or None if all complete.
    """
    for task in tasks:
        if not task.complete:
            return task
    return None
