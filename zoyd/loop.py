"""Main loop orchestrator - invoke Claude Code repeatedly."""

import re
import subprocess
import sys
import time
from pathlib import Path

from . import prd, progress
from .jail import Jail, JailError, create_jail, get_repo_root

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

# Prompt template for generating commit messages (no Co-Author signature)
COMMIT_PROMPT_TEMPLATE = """Generate a git commit message for the following changes.

IMPORTANT: Do NOT include any Co-Author, Co-Authored-By, Signed-off-by, or similar signature lines.
The commit message should be clean and contain only:
1. A concise subject line (50 chars or less)
2. A blank line
3. A brief body explaining what was done (optional, 2-3 lines max)

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
        cwd: Working directory (typically the jail worktree).

    Returns:
        Tuple of (success, output).
    """
    try:
        # First stage all changes
        add_result = subprocess.run(
            ["git", "add", "-A"],
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
        cwd: Working directory for Claude (typically the jail worktree).

    Returns:
        Tuple of (return_code, output).
    """
    # Always use sandbox mode for isolation
    cmd = ["claude", "--print", "--permission-mode", "acceptEdits", "--sandbox"]

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


class LoopRunner:
    """Orchestrates the Zoyd loop with jail isolation."""

    def __init__(
        self,
        prd_path: Path,
        progress_path: Path,
        max_iterations: int = 10,
        model: str | None = None,
        dry_run: bool = False,
        verbose: bool = False,
        delay: float = 1.0,
        auto_commit: bool = False,
        resume: bool = False,
        jail_dir: Path | None = None,
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
        self.jail_dir = jail_dir
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        self.base_backoff = 2.0  # Base for exponential backoff
        self._jail: Jail | None = None

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

    def _get_jail_paths(self, jail: Jail) -> tuple[Path, Path]:
        """Get paths to PRD and progress files within the jail.

        Args:
            jail: The jail environment.

        Returns:
            Tuple of (jail_prd_path, jail_progress_path).
        """
        # Calculate relative paths from source repo
        source_repo = jail.source_repo
        try:
            prd_rel = self.prd_path.relative_to(source_repo)
            progress_rel = self.progress_path.relative_to(source_repo)
        except ValueError:
            # Files are outside repo, use their basenames in jail root
            prd_rel = Path(self.prd_path.name)
            progress_rel = Path(self.progress_path.name)

        return jail.worktree_path / prd_rel, jail.worktree_path / progress_rel

    def run(self) -> int:
        """Run the main loop with jail isolation.

        Returns:
            Exit code: 0 = all complete, 1 = max iterations, 2 = failures, 130 = interrupted, 3 = jail error
        """
        # Set up jail (worktree isolation)
        try:
            source_repo = get_repo_root(self.prd_path.parent)
        except JailError as e:
            print(f"Error: {e}")
            print("Zoyd requires a git repository to create isolated worktrees.")
            return 3

        self._jail = create_jail(source_repo, worktree_base=self.jail_dir)

        try:
            self._jail.setup()
            self.log(f"Created jail worktree at {self._jail.worktree_path}")
            self.log(f"Jail branch: {self._jail.branch_name}")
        except JailError as e:
            print(f"Failed to create jail: {e}")
            return 3

        # Get paths within the jail
        jail_prd_path, jail_progress_path = self._get_jail_paths(self._jail)

        try:
            return self._run_loop(jail_prd_path, jail_progress_path)
        finally:
            # Clean up jail on exit
            if self._jail:
                self.log("Tearing down jail...")
                try:
                    self._jail.teardown()
                except JailError as e:
                    self.log(f"Warning: Failed to clean up jail: {e}")

    def _run_loop(self, jail_prd_path: Path, jail_progress_path: Path) -> int:
        """Run the main loop inside the jail.

        Args:
            jail_prd_path: Path to PRD file in jail.
            jail_progress_path: Path to progress file in jail.

        Returns:
            Exit code.
        """
        # Initialize progress file (skip if resuming to preserve existing progress)
        if not self.resume:
            progress.init_progress_file(jail_progress_path)

        # Get starting iteration from existing progress
        progress_content = progress.read_progress(jail_progress_path)
        iteration = progress.get_iteration_count(progress_content) + 1

        self.log(f"Starting at iteration {iteration}")
        self.log(f"Working in jail: {self._jail.worktree_path}")

        try:
            while iteration <= self.max_iterations:
                # Read current state from jail
                prd_content = prd.read_prd(jail_prd_path)
                progress_content = progress.read_progress(jail_progress_path)
                tasks = prd.parse_tasks(prd_content)
                completed, total = prd.get_completion_status(tasks)

                print(f"\n=== Iteration {iteration}/{self.max_iterations} ({completed}/{total} tasks) ===")
                print(f"Rate limit: {self.get_rate_limit_status()}")
                print(f"Jail: {self._jail.worktree_path}")

                # Check if all tasks complete
                if prd.is_all_complete(tasks):
                    print("All tasks complete!")
                    # Sync changes back to source
                    self._sync_jail_to_source()
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

                # Invoke Claude in sandbox mode, working in jail directory
                self.log("Invoking Claude in sandbox mode...")
                return_code, output = invoke_claude(
                    prompt, self.model, cwd=self._jail.worktree_path
                )

                if return_code != 0:
                    self.consecutive_failures += 1
                    print(f"Claude returned error (code {return_code})")
                    if self.verbose:
                        print(output)

                    if self.consecutive_failures >= self.max_consecutive_failures:
                        print(f"Too many consecutive failures ({self.consecutive_failures})")
                        return 2

                    # Apply exponential backoff on failure
                    backoff = self.get_backoff_delay()
                    self.log(f"Backing off for {backoff:.1f}s after failure {self.consecutive_failures}")
                    time.sleep(backoff)
                else:
                    self.consecutive_failures = 0
                    if self.verbose:
                        print(output)

                    # Check if Claude indicated it cannot complete the task
                    cannot_complete, reason = detect_cannot_complete(output)
                    if cannot_complete:
                        print(f"[BLOCKED] Claude cannot complete task: {reason}")
                        self.log(f"Task blocked - detected pattern: {reason}")
                    else:
                        # Auto-commit if enabled and iteration succeeded (in jail)
                        if self.auto_commit and next_task:
                            self.log("Generating commit message...")
                            commit_msg = generate_commit_message(
                                output, next_task.text, self.model
                            )
                            if commit_msg:
                                self.log("Creating commit in jail...")
                                success, commit_output = commit_changes(
                                    commit_msg, cwd=self._jail.worktree_path
                                )
                                if success:
                                    print(f"Committed: {commit_msg.split(chr(10))[0]}")
                                else:
                                    self.log(f"Commit failed: {commit_output}")
                            else:
                                self.log("Failed to generate commit message")

                # Record progress in jail (with blocked status if detected)
                cannot_complete, reason = detect_cannot_complete(output)
                progress.append_iteration(
                    jail_progress_path,
                    iteration,
                    output,
                    cannot_complete=cannot_complete,
                    cannot_complete_reason=reason,
                )
                self.log(f"Recorded iteration {iteration}")

                iteration += 1

                # Rate limiting pause between iterations
                if iteration <= self.max_iterations and self.delay > 0:
                    time.sleep(self.delay)

            print(f"Reached max iterations ({self.max_iterations})")
            # Sync partial progress back to source
            self._sync_jail_to_source()
            return 1

        except KeyboardInterrupt:
            print("\nInterrupted by user")
            # Offer to sync on interrupt
            self._sync_jail_to_source()
            return 130

    def _sync_jail_to_source(self) -> None:
        """Sync changes from jail worktree back to source repository."""
        if not self._jail:
            return

        self.log("Syncing jail changes to source repository...")
        success, message = self._jail.sync_to_source()
        if success:
            print(f"Synced: {message}")
        else:
            self.log(f"Warning: Sync failed: {message}")
