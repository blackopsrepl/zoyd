"""Progress file management - track iteration history."""

from datetime import datetime
from pathlib import Path


def read_progress(path: Path) -> str:
    """Read progress file content.

    Args:
        path: Path to progress file.

    Returns:
        Content of progress file, or empty string if doesn't exist.
    """
    if path.exists():
        return path.read_text()
    return ""


def get_iteration_count(content: str) -> int:
    """Count iterations from progress content.

    Args:
        content: Progress file content.

    Returns:
        Number of iterations recorded.
    """
    count = 0
    for line in content.splitlines():
        if line.startswith("## Iteration "):
            count += 1
    return count


def append_iteration(
    path: Path,
    iteration: int,
    output: str,
    cannot_complete: bool = False,
    cannot_complete_reason: str | None = None,
) -> None:
    """Append a new iteration entry to the progress file.

    Args:
        path: Path to progress file.
        iteration: Iteration number.
        output: Claude's output for this iteration.
        cannot_complete: Whether Claude indicated it cannot complete the task.
        cannot_complete_reason: The matched phrase indicating inability to complete.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if cannot_complete:
        status = " [BLOCKED]"
        reason_line = f"\n**Blocked reason:** {cannot_complete_reason}\n" if cannot_complete_reason else ""
    else:
        status = ""
        reason_line = ""

    entry = f"\n## Iteration {iteration} - {timestamp}{status}\n{reason_line}\n{output}\n"

    with path.open("a") as f:
        f.write(entry)


def init_progress_file(path: Path) -> None:
    """Initialize progress file with header if it doesn't exist.

    Args:
        path: Path to progress file.
    """
    if not path.exists():
        path.write_text("# Zoyd Progress Log\n")
