"""Main loop orchestrator - invoke Claude Code repeatedly."""

import re
import subprocess
import sys
import time
from pathlib import Path

from . import prd, progress

# Patterns that indicate Claude cannot complete a task
CANNOT_COMPLETE_PATTERNS = [
    r"(?i)i (?:cannot|can't|am unable to|am not able to) (?:complete|finish|accomplish|do|perform) (?:this|the) task",
    r"(?i)(?:this|the) task (?:cannot|can't) be completed",
    r"(?i)unable to (?:complete|finish|accomplish) (?:this|the) task",
    r"(?i)(?:i'm|i am) (?:blocked|stuck) (?:on|by)",
    r"(?i)(?:cannot|can't) proceed (?:with|further)",
    r"(?i)task (?:is )?(?:impossible|infeasible|not possible)",
    r"(?i)(?:i )?(?:need|require) (?:more information|clarification|help)",
    r"(?i)(?:blocking|blocker|blocked)(?:\s+issue)?:",
    r"(?i)this (?:is )?beyond (?:my|the) (?:capabilities|ability|scope)",
]

PROMPT_TEMPLATE = """You are working on a project defined by the PRD.
Complete the next incomplete task marked with [ ].

When you complete a task:
1. Make code changes
2. Run tests to verify
3. Mark task complete ([ ] -> [x]) in PRD

Status: Iteration {iteration}, {completed}/{total} tasks complete

## PRD
{prd_content}

## Progress Log
{progress_content}
"""

# Prompt template for generating commit messages (conventional commits, no signatures)
COMMIT_PROMPT_TEMPLATE = """Generate a git commit message using Conventional Commits format.

Format: <type>(<scope>): <description>

Types:
- feat: new feature
- fix: bug fix
- docs: documentation only
- style: formatting, no code change
- refactor: code restructuring, no feature/fix
- test: adding/updating tests
- chore: maintenance, build, config

Rules:
- Subject line: type(scope): description (72 chars max, lowercase)
- Scope is optional but encouraged (e.g., feat(cli): add --json flag)
- Body is optional, separated by blank line, explains why not what
- NO Co-Author, Co-Authored-By, Signed-off-by, or similar signatures

Changes made this iteration:
{iteration_output}

Task completed: {task_text}

Respond with ONLY the commit message, nothing else."""


def detect_cannot_complete(output: str) -> tuple[bool, str | None]:
    """Detect if Claude's output indicates it cannot complete the task.

    Args:
        output: Claude's output text.

    Returns:
        Tuple of (detected, matched_pattern). If detected is True, matched_pattern
        contains the first matching phrase found.
    """
    for pattern in CANNOT_COMPLETE_PATTERNS:
        match = re.search(pattern, output)
        if match:
            return True, match.group(0)
    return False, None


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
    return_code, output = invoke_claude(prompt, model)
    if return_code != 0:
        return None
    # Clean up the output - remove any accidental signatures
    lines = output.strip().split("\n")
    clean_lines = [
        line for line in lines
        if not any(sig in line.lower() for sig in ["co-author", "signed-off", "co-authored"])
    ]
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


def invoke_claude(
    prompt: str,
    model: str | None = None,
    cwd: Path | None = None,
) -> tuple[int, str]:
    """Invoke Claude Code with the given prompt in sandbox mode.

    Args:
        prompt: The prompt to send to Claude.
        model: Optional model to use (e.g., "opus", "sonnet").
        cwd: Working directory for Claude.

    Returns:
        Tuple of (return_code, output).
    """
    # Enable sandbox mode via settings for filesystem/network isolation
    sandbox_settings = '{"sandbox": {"enabled": true, "autoAllowBashIfSandboxed": true}}'
    cmd = ["claude", "--print", "--permission-mode", "acceptEdits", "--settings", sandbox_settings]

    if model:
        cmd.extend(["--model", model])

    # Prompt is passed as a positional argument, not via --prompt
    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n\nSTDERR:\n{result.stderr}"
        return result.returncode, output
    except FileNotFoundError:
        return 1, "Error: 'claude' command not found. Is Claude Code installed?"
    except Exception as e:
        return 1, f"Error invoking Claude: {e}"


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string like "1m 23s" or "45.2s".
    """
    if seconds >= 60:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    return f"{seconds:.1f}s"


class LoopRunner:
    """Orchestrates the Zoyd loop."""

    def __init__(
        self,
        prd_path: Path,
        progress_path: Path,
        max_iterations: int = 10,
        model: str | None = None,
        dry_run: bool = False,
        verbose: bool = False,
        delay: float = 1.0,
        auto_commit: bool = True,
        resume: bool = False,
        fail_fast: bool = False,
    ):
        self.prd_path = prd_path.resolve()
        self.progress_path = progress_path.resolve()
        self.max_iterations = max_iterations
        self.model = model
        self.dry_run = dry_run
        self.verbose = verbose
        self.delay = delay
        self.auto_commit = auto_commit
        self.resume = resume
        self.fail_fast = fail_fast
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        self.base_backoff = 2.0  # Base for exponential backoff
        self.start_time: float | None = None  # Track run start time
        # Statistics tracking
        self.stats_iterations: int = 0
        self.stats_successes: int = 0
        self.stats_failures: int = 0
        self.stats_tasks_completed_start: int = 0
        self.stats_tasks_completed_end: int = 0
        self.stats_total_tasks: int = 0

    def get_backoff_delay(self) -> float:
        """Calculate exponential backoff delay based on consecutive failures.

        Returns:
            Delay in seconds: 2^failures (2s, 4s, 8s, etc.) or 0 if no failures.
        """
        if self.consecutive_failures == 0:
            return 0.0
        return self.base_backoff ** self.consecutive_failures

    def get_rate_limit_status(self) -> str:
        """Get a human-readable rate limit status string.

        Returns:
            Status string showing delay configuration and any active backoff.
        """
        parts = []
        if self.delay > 0:
            parts.append(f"delay={self.delay:.1f}s")
        else:
            parts.append("delay=0s")

        backoff = self.get_backoff_delay()
        if backoff > 0:
            parts.append(f"backoff={backoff:.1f}s")

        return ", ".join(parts)

    def log(self, message: str) -> None:
        """Print a log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[zoyd] {message}", file=sys.stderr)

    def print_summary(self) -> None:
        """Print summary statistics at end of run."""
        print("\n=== Summary ===")

        # Total time
        if self.start_time:
            total_time = time.time() - self.start_time
            print(f"Total time: {format_duration(total_time)}")

        # Iterations
        print(f"Iterations: {self.stats_iterations}")

        # Success rate
        total_attempts = self.stats_successes + self.stats_failures
        if total_attempts > 0:
            success_rate = (self.stats_successes / total_attempts) * 100
            print(f"Success rate: {success_rate:.1f}% ({self.stats_successes}/{total_attempts})")
        else:
            print("Success rate: N/A (no iterations run)")

        # Tasks completed
        tasks_completed_this_run = self.stats_tasks_completed_end - self.stats_tasks_completed_start
        print(f"Tasks completed: {tasks_completed_this_run} ({self.stats_tasks_completed_end}/{self.stats_total_tasks} total)")

    def run(self) -> int:
        """Run the main loop.

        Returns:
            Exit code: 0 = all complete, 1 = max iterations, 2 = failures, 130 = interrupted
        """
        # Track run start time
        self.start_time = time.time()

        # Verify PRD exists
        if not self.prd_path.exists():
            print(f"Error: PRD file not found: {self.prd_path}")
            print("Make sure the PRD file exists before running zoyd.")
            return 1

        # Initialize progress file (skip if resuming to preserve existing progress)
        if not self.resume:
            progress.init_progress_file(self.progress_path)

        # Get starting iteration from existing progress
        progress_content = progress.read_progress(self.progress_path)
        iteration = progress.get_iteration_count(progress_content) + 1

        self.log(f"Starting at iteration {iteration}")

        # Initialize statistics tracking
        prd_content = prd.read_prd(self.prd_path)
        tasks = prd.parse_tasks(prd_content)
        completed, total = prd.get_completion_status(tasks)
        self.stats_tasks_completed_start = completed
        self.stats_total_tasks = total

        try:
            while iteration <= self.max_iterations:
                # Track iteration start time
                iteration_start = time.time()

                # Read current state
                prd_content = prd.read_prd(self.prd_path)
                progress_content = progress.read_progress(self.progress_path)
                tasks = prd.parse_tasks(prd_content)
                completed, total = prd.get_completion_status(tasks)

                print(f"\n=== Iteration {iteration}/{self.max_iterations} ({completed}/{total} tasks) ===")
                print(f"Rate limit: {self.get_rate_limit_status()}")

                # Show elapsed time in verbose mode
                if self.verbose and self.start_time:
                    elapsed = time.time() - self.start_time
                    self.log(f"Elapsed time: {format_duration(elapsed)}")

                # Check if all tasks complete
                if prd.is_all_complete(tasks):
                    print("All tasks complete!")
                    self.stats_tasks_completed_end = completed
                    self.print_summary()
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

                # Invoke Claude in sandbox mode
                self.log("Invoking Claude in sandbox mode...")
                return_code, output = invoke_claude(prompt, self.model)

                if return_code != 0:
                    self.consecutive_failures += 1
                    self.stats_failures += 1
                    self.stats_iterations += 1
                    print(f"Claude returned error (code {return_code})")
                    if self.verbose:
                        print(output)

                    # Fail-fast: exit immediately on first failure
                    if self.fail_fast:
                        print("Fail-fast mode: exiting on first failure")
                        self.stats_tasks_completed_end = completed
                        self.print_summary()
                        return 2

                    if self.consecutive_failures >= self.max_consecutive_failures:
                        print(f"Too many consecutive failures ({self.consecutive_failures})")
                        self.stats_tasks_completed_end = completed
                        self.print_summary()
                        return 2

                    # Apply exponential backoff on failure
                    backoff = self.get_backoff_delay()
                    self.log(f"Backing off for {backoff:.1f}s after failure {self.consecutive_failures}")
                    time.sleep(backoff)
                else:
                    self.consecutive_failures = 0
                    self.stats_successes += 1
                    self.stats_iterations += 1
                    if self.verbose:
                        print(output)

                    # Check if Claude indicated it cannot complete the task
                    cannot_complete, reason = detect_cannot_complete(output)
                    if cannot_complete:
                        print(f"[BLOCKED] Claude cannot complete task: {reason}")
                        self.log(f"Task blocked - detected pattern: {reason}")
                    else:
                        # Auto-commit if enabled and iteration succeeded
                        if self.auto_commit and next_task:
                            self.log("Generating commit message...")
                            commit_msg = generate_commit_message(
                                output, next_task.text, self.model
                            )
                            if commit_msg:
                                self.log("Creating commit...")
                                success, commit_output = commit_changes(commit_msg)
                                if success:
                                    print(f"Committed: {commit_msg.split(chr(10))[0]}")
                                else:
                                    self.log(f"Commit failed: {commit_output}")
                            else:
                                self.log("Failed to generate commit message")

                # Record progress (with blocked status if detected)
                cannot_complete, reason = detect_cannot_complete(output)
                progress.append_iteration(
                    self.progress_path,
                    iteration,
                    output,
                    cannot_complete=cannot_complete,
                    cannot_complete_reason=reason,
                )
                self.log(f"Recorded iteration {iteration}")

                # Show iteration timing in verbose mode
                if self.verbose:
                    iteration_duration = time.time() - iteration_start
                    self.log(f"Iteration {iteration} completed in {format_duration(iteration_duration)}")

                iteration += 1

                # Rate limiting pause between iterations
                if iteration <= self.max_iterations and self.delay > 0:
                    time.sleep(self.delay)

            print(f"Reached max iterations ({self.max_iterations})")
            # Get final task count
            tasks = prd.parse_tasks(prd.read_prd(self.prd_path))
            completed, _ = prd.get_completion_status(tasks)
            self.stats_tasks_completed_end = completed
            self.print_summary()
            return 1

        except KeyboardInterrupt:
            print("\nInterrupted by user")
            # Get final task count
            tasks = prd.parse_tasks(prd.read_prd(self.prd_path))
            completed, _ = prd.get_completion_status(tasks)
            self.stats_tasks_completed_end = completed
            self.print_summary()
            return 130
