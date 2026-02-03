"""Commit management utilities for the Zoyd loop."""

import re
import subprocess
import uuid
from pathlib import Path

from .prompt_templates import COMMIT_PROMPT_TEMPLATE, COMMIT_SYSTEM_PROMPT

from .invoke import invoke_claude


def generate_commit_message(iteration_output: str, task_text: str, model: str | None = None) -> str | None:
    """Generate a commit message using Claude.

    Args:
        iteration_output: The output from the completed iteration.
        task_text: The text of the completed task.
        model: Optional model to use.

    Returns:
        Generated commit message, or None if generation failed.
    """
    prompt = COMMIT_PROMPT_TEMPLATE.format(
        iteration_output=iteration_output[:2000],  # Limit context size
        task_text=task_text,
    )
    return_code, output, _ = invoke_claude(prompt, model, append_system_prompt=COMMIT_SYSTEM_PROMPT, sandbox=False)
    if return_code != 0:
        return None
    # Clean up the output - remove any accidental signatures
    lines = output.strip().split("\n")
    clean_lines = [
        line for line in lines
        if not any(sig in line.lower() for sig in ["co-author", "signed-off", "co-authored"])
    ]
    # Strip code block fences (``` or ```lang) and inline backticks
    clean_lines = [line for line in clean_lines if not re.match(r"^```\w*$", line.strip())]
    clean_lines = [line.replace("`", "") for line in clean_lines]
    return "\n".join(clean_lines).strip() or None


def commit_changes(message: str, cwd: Path | None = None) -> tuple[bool, str]:
    """Create a git commit with the given message.

    Args:
        message: The commit message.
        cwd: Working directory.

    Returns:
        Tuple of (success, output).
    """
    try:
        # Stage all changes except PRD and progress files (those stay tracked but uncommitted)
        add_result = subprocess.run(
            ["git", "add", "-A", "--", ".", ":!PRD.md", ":!progress.txt", ":!*.PRD.md", ":!*progress.txt"],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        if add_result.returncode != 0:
            return False, f"git add failed: {add_result.stderr}"

        # Check if there are changes to commit
        status_result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        if status_result.returncode == 0:
            return True, "No changes to commit"

        # Commit with the message
        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        if commit_result.returncode != 0:
            return False, f"git commit failed: {commit_result.stderr}"

        return True, commit_result.stdout
    except FileNotFoundError:
        return False, "git command not found"
    except Exception as e:
        return False, f"Error during commit: {e}"