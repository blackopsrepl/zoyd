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


def append_iteration(path: Path, iteration: int, output: str) -> None:
    """Append a new iteration entry to the progress file.

    Args:
        path: Path to progress file.
        iteration: Iteration number.
        output: Claude's output for this iteration.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry = f"\n## Iteration {iteration} - {timestamp}\n\n{output}\n"

    with path.open("a") as f:
        f.write(entry)


def init_progress_file(path: Path) -> None:
    """Initialize progress file with header if it doesn't exist.

    Args:
        path: Path to progress file.
    """
    if not path.exists():
        path.write_text("# Ralph Progress Log\n")
