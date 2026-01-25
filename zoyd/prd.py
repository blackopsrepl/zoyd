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
