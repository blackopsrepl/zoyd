"""Main loop orchestrator - invoke Claude Code repeatedly."""

import subprocess
import sys
import time
from pathlib import Path

from . import prd, progress

# Default prompt template
PROMPT_TEMPLATE = """You are working on a project defined by the PRD.
Complete the next incomplete task marked with [ ].

When you complete a task:
1. Make code changes
2. Run tests to verify
3. Mark task complete ([ ] -> [x]) in PRD
4. Commit with descriptive message

Status: Iteration {iteration}, {completed}/{total} tasks complete

## PRD
{prd_content}

## Progress Log
{progress_content}
"""


def build_prompt(
    prd_content: str,
    progress_content: str,
    iteration: int,
    completed: int,
    total: int,
) -> str:
    """Build the prompt for Claude.

    Args:
        prd_content: Content of the PRD file.
        progress_content: Content of the progress file.
        iteration: Current iteration number.
        completed: Number of completed tasks.
        total: Total number of tasks.

    Returns:
        Formatted prompt string.
    """
    return PROMPT_TEMPLATE.format(
        iteration=iteration,
        completed=completed,
        total=total,
        prd_content=prd_content,
        progress_content=progress_content or "(No progress yet)",
    )


def invoke_claude(prompt: str, model: str | None = None) -> tuple[int, str]:
    """Invoke Claude Code with the given prompt.

    Args:
        prompt: The prompt to send to Claude.
        model: Optional model to use (e.g., "opus", "sonnet").

    Returns:
        Tuple of (return_code, output).
    """
    cmd = ["claude", "--print", "--permission-mode", "acceptEdits"]

    if model:
        cmd.extend(["--model", model])

    cmd.extend(["--prompt", prompt])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n\nSTDERR:\n{result.stderr}"
        return result.returncode, output
    except FileNotFoundError:
        return 1, "Error: 'claude' command not found. Is Claude Code installed?"
    except Exception as e:
        return 1, f"Error invoking Claude: {e}"


class LoopRunner:
    """Orchestrates the Ralph loop."""

    def __init__(
        self,
        prd_path: Path,
        progress_path: Path,
        max_iterations: int = 10,
        model: str | None = None,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.prd_path = prd_path
        self.progress_path = progress_path
        self.max_iterations = max_iterations
        self.model = model
        self.dry_run = dry_run
        self.verbose = verbose
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3

    def log(self, message: str) -> None:
        """Print a log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[ralph] {message}", file=sys.stderr)

    def run(self) -> int:
        """Run the main loop.

        Returns:
            Exit code: 0 = all complete, 1 = max iterations, 2 = failures, 130 = interrupted
        """
        # Initialize progress file
        progress.init_progress_file(self.progress_path)

        # Get starting iteration from existing progress
        progress_content = progress.read_progress(self.progress_path)
        iteration = progress.get_iteration_count(progress_content) + 1

        self.log(f"Starting at iteration {iteration}")

        try:
            while iteration <= self.max_iterations:
                # Read current state
                prd_content = prd.read_prd(self.prd_path)
                progress_content = progress.read_progress(self.progress_path)
                tasks = prd.parse_tasks(prd_content)
                completed, total = prd.get_completion_status(tasks)

                print(f"\n=== Iteration {iteration}/{self.max_iterations} ({completed}/{total} tasks) ===")

                # Check if all tasks complete
                if prd.is_all_complete(tasks):
                    print("All tasks complete!")
                    return 0

                # Show next task
                next_task = prd.get_next_incomplete_task(tasks)
                if next_task:
                    print(f"Next task: {next_task.text}")

                # Build prompt
                prompt = build_prompt(
                    prd_content=prd_content,
                    progress_content=progress_content,
                    iteration=iteration,
                    completed=completed,
                    total=total,
                )

                if self.dry_run:
                    print("\n--- DRY RUN: Would send prompt ---")
                    print(prompt)
                    print("--- END PROMPT ---\n")
                    iteration += 1
                    continue

                # Invoke Claude
                self.log("Invoking Claude...")
                return_code, output = invoke_claude(prompt, self.model)

                if return_code != 0:
                    self.consecutive_failures += 1
                    print(f"Claude returned error (code {return_code})")
                    if self.verbose:
                        print(output)

                    if self.consecutive_failures >= self.max_consecutive_failures:
                        print(f"Too many consecutive failures ({self.consecutive_failures})")
                        return 2
                else:
                    self.consecutive_failures = 0
                    if self.verbose:
                        print(output)

                # Record progress
                progress.append_iteration(self.progress_path, iteration, output)
                self.log(f"Recorded iteration {iteration}")

                iteration += 1

                # Brief rate limiting pause
                if iteration <= self.max_iterations:
                    time.sleep(1)

            print(f"Reached max iterations ({self.max_iterations})")
            return 1

        except KeyboardInterrupt:
            print("\nInterrupted by user")
            return 130
