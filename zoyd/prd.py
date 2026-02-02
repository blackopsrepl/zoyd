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


@dataclass
class ValidationWarning:
    """A validation warning for a PRD."""
    line_number: int
    line_content: str
    message: str


# Matches markdown checkboxes: - [ ] or - [x] or - [X]
CHECKBOX_PATTERN = re.compile(r"^(\s*-\s*\[)([ xX])(\]\s*)(.*)$")

# Patterns for detecting malformed checkboxes
MALFORMED_CHECKBOX_PATTERNS = [
    # Missing space inside brackets: -[] or -[x] without proper spacing
    (re.compile(r"^\s*-\s*\[\]"), "Missing space inside checkbox brackets (should be '- [ ]')"),
    # Extra characters inside brackets: -[xx], -[ x], -[x ], etc.
    (re.compile(r"^\s*-\s*\[[^\]]{2,}\]"), "Invalid checkbox format (should have single space or 'x' inside)"),
    # No space before checkbox content: - [ ]text or - [x]text
    (re.compile(r"^\s*-\s*\[[ xX]\][^\s]"), "Missing space after checkbox (should be '- [ ] text')"),
    # Bracket variations: -( ), -< >, etc.
    (re.compile(r"^\s*-\s*[\(<][^\)\>]*[\)>]"), "Invalid checkbox format (use square brackets: '- [ ]')"),
    # Missing closing bracket: - [ text or - [x text
    (re.compile(r"^\s*-\s*\[[ xX][^\]]*$"), "Missing closing bracket in checkbox"),
]


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


def validate_prd(content: str) -> list[ValidationWarning]:
    """Validate PRD content for common issues.

    Checks for:
    - Malformed checkboxes (missing spaces, wrong brackets, etc.)
    - Empty task text (checkbox with no description)

    Args:
        content: Markdown content to validate.

    Returns:
        List of ValidationWarning objects for each issue found.
    """
    warnings = []
    lines = content.splitlines()

    for line_number, line in enumerate(lines, start=1):
        # Skip empty lines
        if not line.strip():
            continue

        # Check for valid checkbox with empty text or missing space after checkbox
        match = CHECKBOX_PATTERN.match(line)
        if match:
            bracket_group = match.group(3)  # Contains "]" and any trailing space
            task_text = match.group(4).strip()

            # Check if there's no space after the bracket (] immediately followed by text)
            if bracket_group == "]" and match.group(4) and not match.group(4)[0].isspace():
                warnings.append(ValidationWarning(
                    line_number=line_number,
                    line_content=line,
                    message="Missing space after checkbox (should be '- [ ] text')",
                ))
            elif not task_text:
                warnings.append(ValidationWarning(
                    line_number=line_number,
                    line_content=line,
                    message="Empty task text (checkbox has no description)",
                ))
            continue

        # Check for malformed checkbox patterns
        for pattern, message in MALFORMED_CHECKBOX_PATTERNS:
            if pattern.match(line):
                warnings.append(ValidationWarning(
                    line_number=line_number,
                    line_content=line,
                    message=message,
                ))
                break  # Only report first matching issue per line

    return warnings


def _is_task_line(line: str) -> bool:
    """Check if a line is a task checkbox line.

    Args:
        line: Line content to check.

    Returns:
        True if the line is a checkbox task line.
    """
    return CHECKBOX_PATTERN.match(line) is not None


def _get_checkbox_state(line: str) -> tuple[str, str]:
    """Extract checkbox state and prefix from a task line.

    Args:
        line: Task line to parse.

    Returns:
        Tuple of (prefix including checkbox, checkbox char).
    """
    match = CHECKBOX_PATTERN.match(line)
    if match:
        prefix = match.group(1) + match.group(2) + match.group(3)
        checkbox_char = match.group(2)
        return prefix, checkbox_char
    return "- [ ] ", " "


def edit_task(path: Path, line_number: int, new_text: str) -> Task:
    """Edit task text in-place, preserving checkbox state.

    Args:
        path: Path to the PRD file.
        line_number: 1-based line number of the task to edit.
        new_text: New task text.

    Returns:
        Updated Task object.

    Raises:
        FileNotFoundError: If the PRD file doesn't exist.
        ValueError: If line_number is invalid or not a task line.
    """
    if not path.exists():
        raise FileNotFoundError(f"PRD file not found: {path}")

    content = path.read_text()
    lines = content.splitlines()

    if line_number < 1 or line_number > len(lines):
        raise ValueError(f"Invalid line number: {line_number}")

    line_idx = line_number - 1
    original_line = lines[line_idx]

    if not _is_task_line(original_line):
        raise ValueError(f"Line {line_number} is not a task checkbox")

    # Extract current checkbox state
    match = CHECKBOX_PATTERN.match(original_line)
    prefix = match.group(1) + match.group(2) + match.group(3)
    checkbox_char = match.group(2)
    complete = checkbox_char.lower() == "x"

    # Build new line preserving checkbox state
    new_line = prefix + new_text
    lines[line_idx] = new_line

    # Write back
    path.write_text("\n".join(lines) + ("\n" if content.endswith("\n") else ""))

    return Task(text=new_text, complete=complete, line_number=line_number)


def add_task(path: Path, after_line: int, text: str, complete: bool = False) -> Task:
    """Add new task after given line number.

    Args:
        path: Path to the PRD file.
        after_line: 1-based line number after which to insert the task.
        text: Task text.
        complete: Whether task should be completed.

    Returns:
        Created Task object with its line number.

    Raises:
        FileNotFoundError: If the PRD file doesn't exist.
        ValueError: If after_line is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"PRD file not found: {path}")

    content = path.read_text()
    lines = content.splitlines()

    if after_line < 0 or after_line > len(lines):
        raise ValueError(f"Invalid line number: {after_line}")

    checkbox_char = "x" if complete else " "
    new_line = f"- [{checkbox_char}] {text}"

    # Insert after the specified line
    lines.insert(after_line, new_line)

    # Write back
    path.write_text("\n".join(lines) + ("\n" if content.endswith("\n") else ""))

    return Task(text=text, complete=complete, line_number=after_line + 1)


def delete_task(path: Path, line_number: int) -> Task:
    """Remove task at line.

    Args:
        path: Path to the PRD file.
        line_number: 1-based line number of the task to delete.

    Returns:
        Deleted Task object.

    Raises:
        FileNotFoundError: If the PRD file doesn't exist.
        ValueError: If line_number is invalid or not a task line.
    """
    if not path.exists():
        raise FileNotFoundError(f"PRD file not found: {path}")

    content = path.read_text()
    lines = content.splitlines()

    if line_number < 1 or line_number > len(lines):
        raise ValueError(f"Invalid line number: {line_number}")

    line_idx = line_number - 1
    line = lines[line_idx]

    if not _is_task_line(line):
        raise ValueError(f"Line {line_number} is not a task checkbox")

    # Extract task info before deletion
    match = CHECKBOX_PATTERN.match(line)
    task_text = match.group(4).strip()
    checkbox_char = match.group(2)
    complete = checkbox_char.lower() == "x"

    # Remove the line
    lines.pop(line_idx)

    # Write back
    path.write_text("\n".join(lines) + ("\n" if content.endswith("\n") else ""))

    return Task(text=task_text, complete=complete, line_number=line_number)


def move_task(path: Path, from_line: int, to_line: int) -> Task:
    """Reorder task by moving it to a new position.

    Args:
        path: Path to the PRD file.
        from_line: 1-based line number of task to move.
        to_line: 1-based line number where task should be moved.

    Returns:
        Moved Task object with its new line number.

    Raises:
        FileNotFoundError: If the PRD file doesn't exist.
        ValueError: If line numbers are invalid or not task lines.
    """
    if not path.exists():
        raise FileNotFoundError(f"PRD file not found: {path}")

    if from_line == to_line:
        raise ValueError("from_line and to_line cannot be the same")

    content = path.read_text()
    lines = content.splitlines()

    if from_line < 1 or from_line > len(lines):
        raise ValueError(f"Invalid from_line number: {from_line}")
    if to_line < 1 or to_line > len(lines):
        raise ValueError(f"Invalid to_line number: {to_line}")

    from_idx = from_line - 1
    to_idx = to_line - 1

    line = lines[from_idx]

    if not _is_task_line(line):
        raise ValueError(f"Line {from_line} is not a task checkbox")

    # Extract task info
    match = CHECKBOX_PATTERN.match(line)
    task_text = match.group(4).strip()
    checkbox_char = match.group(2)
    complete = checkbox_char.lower() == "x"

    # Remove from original position and insert at target position
    lines.pop(from_idx)
    lines.insert(to_idx, line)

    # Write back
    path.write_text("\n".join(lines) + ("\n" if content.endswith("\n") else ""))

    new_line_number = to_idx + 1
    return Task(text=task_text, complete=complete, line_number=new_line_number)


def toggle_task(path: Path, line_number: int) -> Task:
    """Toggle checkbox state [ ] ↔ [x].

    Args:
        path: Path to the PRD file.
        line_number: 1-based line number of the task to toggle.

    Returns:
        Updated Task object with new completion state.

    Raises:
        FileNotFoundError: If the PRD file doesn't exist.
        ValueError: If line_number is invalid or not a task line.
    """
    if not path.exists():
        raise FileNotFoundError(f"PRD file not found: {path}")

    content = path.read_text()
    lines = content.splitlines()

    if line_number < 1 or line_number > len(lines):
        raise ValueError(f"Invalid line number: {line_number}")

    line_idx = line_number - 1
    line = lines[line_idx]

    if not _is_task_line(line):
        raise ValueError(f"Line {line_number} is not a task checkbox")

    # Extract and toggle checkbox state
    match = CHECKBOX_PATTERN.match(line)
    checkbox_char = match.group(2)
    task_text = match.group(4).strip()

    # Toggle: space becomes x, anything else becomes space
    new_checkbox_char = " " if checkbox_char.lower() == "x" else "x"
    new_complete = new_checkbox_char == "x"

    # Build new line
    prefix = match.group(1) + new_checkbox_char + match.group(3)
    new_line = prefix + task_text
    lines[line_idx] = new_line

    # Write back
    path.write_text("\n".join(lines) + ("\n" if content.endswith("\n") else ""))

    return Task(text=task_text, complete=new_complete, line_number=line_number)
