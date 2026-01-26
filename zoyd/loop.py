"""Main loop orchestrator - invoke Claude Code repeatedly."""

from __future__ import annotations

import json as json_module
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import prd, progress
from .config import load_config
from .session.logger import SessionLogger
from .session.storage import create_storage
from .tui.console import create_console
from .tui.events import EventEmitter, EventType
from .tui.live import (
    LiveDisplay,
    PlainDisplay,
    create_live_display,
    create_plain_display,
)

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

## Current Task (COMPLETE THIS ONLY)
{current_task}

IMPORTANT: Work on ONLY this task. Do NOT work on other tasks. One task = one commit.

## PRD (for context only)
{prd_content}

## Progress Log
{progress_content}
"""

# Prompt template for generating commit messages (conventional commits, no signatures)
COMMIT_PROMPT_TEMPLATE = """Generate a git commit message for the changes below.

Changes made this iteration:
{iteration_output}

Task completed: {task_text}

Respond with ONLY the commit message, nothing else."""

# System-level rules for commit message generation (delivered via --append-system-prompt)
COMMIT_SYSTEM_PROMPT = """\
Use Conventional Commits format: <type>(<scope>): <description>
Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert.
Subject line: type(scope): description (72 chars max, lowercase).
Scope is optional but encouraged (e.g., feat(cli): add --json flag).
Body is optional, separated by blank line, explains why not what.
Never add Co-Authored-By, Signed-off-by, or any signature lines to commits."""


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
    current_task: str,
) -> str:
    """Build the prompt for Claude.

    Args:
        prd_content: Content of the PRD file.
        progress_content: Content of the progress file.
        iteration: Current iteration number.
        completed: Number of completed tasks.
        total: Total number of tasks.
        current_task: Text of the current task to complete.

    Returns:
        Formatted prompt string.
    """
    return PROMPT_TEMPLATE.format(
        iteration=iteration,
        completed=completed,
        total=total,
        current_task=current_task,
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
    return_code, output, _ = invoke_claude(prompt, model, append_system_prompt=COMMIT_SYSTEM_PROMPT)
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
    track_cost: bool = False,
    append_system_prompt: str | None = None,
) -> tuple[int, str, float | None]:
    """Invoke Claude Code with the given prompt in sandbox mode.

    Args:
        prompt: The prompt to send to Claude.
        model: Optional model to use (e.g., "opus", "sonnet").
        cwd: Working directory for Claude.
        track_cost: If True, use JSON output format to track cost.
        append_system_prompt: Optional text appended to the system prompt.

    Returns:
        Tuple of (return_code, output, cost_usd). cost_usd is None if not tracking or unavailable.
    """
    # Enable sandbox mode via settings for filesystem/network isolation
    # Claude expects --settings to be a file path, not inline JSON
    sandbox_settings = {"sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True}}

    # Create a temp file for settings
    settings_fd, settings_path = tempfile.mkstemp(suffix=".json", prefix="zoyd_settings_")
    try:
        with open(settings_fd, "w") as f:
            json_module.dump(sandbox_settings, f)

        cmd = ["claude", "--print", "--permission-mode", "acceptEdits", "--settings", settings_path]

        if model:
            cmd.extend(["--model", model])

        if track_cost:
            cmd.extend(["--output-format", "json"])

        if append_system_prompt:
            cmd.extend(["--append-system-prompt", append_system_prompt])

        # Prompt is passed as a positional argument, not via --prompt
        cmd.append(prompt)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        output = result.stdout
        cost_usd = None

        if track_cost and result.returncode == 0:
            # Parse JSON output to extract cost and text
            try:
                json_output = json_module.loads(output)
                # Claude JSON output has 'result' and 'cost_usd' fields
                cost_usd = json_output.get("cost_usd")
                # Extract the actual text content from the result
                output = json_output.get("result", output)
            except (json_module.JSONDecodeError, TypeError):
                # If JSON parsing fails, keep original output
                pass

        if result.stderr:
            output += f"\n\nSTDERR:\n{result.stderr}"
        return result.returncode, output, cost_usd
    except FileNotFoundError:
        return 1, "Error: 'claude' command not found. Is Claude Code installed?", None
    except Exception as e:
        return 1, f"Error invoking Claude: {e}", None
    finally:
        # Clean up temp file
        Path(settings_path).unlink(missing_ok=True)


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
        max_iterations: int | None = None,
        model: str | None = None,
        dry_run: bool = False,
        verbose: bool | None = None,
        delay: float | None = None,
        auto_commit: bool | None = None,
        resume: bool = False,
        fail_fast: bool | None = None,
        max_cost: float | None = None,
        tui_enabled: bool | None = None,
        tui_refresh_rate: float | None = None,
        tui_compact: bool | None = None,
        session_logging: bool | None = None,
        sessions_dir: str | None = None,
        storage_backend: str | None = None,
        redis_host: str | None = None,
        redis_port: int | None = None,
        redis_db: int | None = None,
        redis_password: str | None = None,
    ):
        # Load config for resolving None sentinels
        cfg = load_config()

        self.prd_path = prd_path.resolve()
        self.progress_path = progress_path.resolve()
        self.max_iterations = max_iterations if max_iterations is not None else cfg.max_iterations
        self.model = model if model is not None else cfg.model
        self.dry_run = dry_run
        self.verbose = verbose if verbose is not None else cfg.verbose
        self.delay = delay if delay is not None else cfg.delay
        self.auto_commit = auto_commit if auto_commit is not None else cfg.auto_commit
        self.resume = resume
        self.fail_fast = fail_fast if fail_fast is not None else cfg.fail_fast
        self.max_cost = max_cost if max_cost is not None else cfg.max_cost
        self.tui_enabled = tui_enabled if tui_enabled is not None else cfg.tui_enabled
        self.tui_refresh_rate = tui_refresh_rate if tui_refresh_rate is not None else cfg.tui_refresh_rate
        self.tui_compact = tui_compact if tui_compact is not None else cfg.tui_compact
        self.session_logging = session_logging if session_logging is not None else cfg.session_logging
        self.sessions_dir = sessions_dir if sessions_dir is not None else cfg.sessions_dir
        self.storage_backend = storage_backend if storage_backend is not None else cfg.storage_backend
        self.redis_host = redis_host if redis_host is not None else cfg.redis_host
        self.redis_port = redis_port if redis_port is not None else cfg.redis_port
        self.redis_db = redis_db if redis_db is not None else cfg.redis_db
        self.redis_password = redis_password if redis_password is not None else cfg.redis_password
        # Create display for output (TUI or plain depending on settings)
        if not self.tui_enabled:
            self.live: LiveDisplay | PlainDisplay = create_plain_display(
                prd_path=str(self.prd_path),
                progress_path=str(self.progress_path),
                max_iterations=self.max_iterations,
                model=self.model,
                max_cost=self.max_cost,
            )
        else:
            self.live = create_live_display(
                create_console(),
                prd_path=str(self.prd_path),
                progress_path=str(self.progress_path),
                max_iterations=self.max_iterations,
                model=self.model,
                max_cost=self.max_cost,
                refresh_per_second=int(self.tui_refresh_rate),
            )
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
        # Cost tracking
        self.stats_total_cost: float = 0.0
        # Event emitter for TUI dashboard integration
        self.events = EventEmitter()
        # Session logger for persistent logging
        # Skip session logging in dry-run mode (no point logging a dry run)
        self.session_logger: SessionLogger | None = None
        if self.session_logging and not self.dry_run:
            storage = create_storage(
                backend=self.storage_backend,
                sessions_dir=self.sessions_dir,
                redis_host=self.redis_host,
                redis_port=self.redis_port,
                redis_db=self.redis_db,
                redis_password=self.redis_password,
            )
            self.session_logger = SessionLogger(storage=storage)
            self.session_logger.subscribe_to(self.events)

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

    def print_summary(self) -> None:
        """Print summary statistics at end of run."""
        self.live.log("=== Summary ===", style="bold")

        # Total time
        if self.start_time:
            total_time = time.time() - self.start_time
            self.live.log(f"Total time: {format_duration(total_time)}")

        # Iterations
        self.live.log(f"Iterations: {self.stats_iterations}")

        # Success rate
        total_attempts = self.stats_successes + self.stats_failures
        if total_attempts > 0:
            success_rate = (self.stats_successes / total_attempts) * 100
            self.live.log(f"Success rate: {success_rate:.1f}% ({self.stats_successes}/{total_attempts})")
        else:
            self.live.log("Success rate: N/A (no iterations run)")

        # Tasks completed
        tasks_completed_this_run = self.stats_tasks_completed_end - self.stats_tasks_completed_start
        self.live.log(f"Tasks completed: {tasks_completed_this_run} ({self.stats_tasks_completed_end}/{self.stats_total_tasks} total)")

        # Cost tracking (only show if we tracked cost)
        if self.max_cost is not None or self.stats_total_cost > 0:
            self.live.log(f"Total cost: ${self.stats_total_cost:.4f}")
            if self.max_cost is not None:
                self.live.log(f"Cost limit: ${self.max_cost:.2f}")

    def run(self) -> int:
        """Run the main loop.

        Returns:
            Exit code: 0 = all complete, 1 = max iterations, 2 = failures, 130 = interrupted
        """
        # Track run start time
        self.start_time = time.time()

        # Start session logging if enabled
        if self.session_logger is not None:
            self.session_logger.start_session(
                working_dir=str(Path.cwd()),
                prd_path=str(self.prd_path),
                progress_path=str(self.progress_path),
                model=self.model,
                max_iterations=self.max_iterations,
                max_cost=self.max_cost,
                auto_commit=self.auto_commit,
                fail_fast=self.fail_fast,
            )

        # Emit LOOP_START event
        self.events.emit(EventType.LOOP_START, {
            "prd_path": str(self.prd_path),
            "progress_path": str(self.progress_path),
            "max_iterations": self.max_iterations,
            "model": self.model,
            "max_cost": self.max_cost,
        })

        # Verify PRD exists (before creating live display)
        if not self.prd_path.exists():
            print(f"Error: PRD file not found: {self.prd_path}")
            print("Make sure the PRD file exists before running zoyd.")
            if self.session_logger is not None:
                self.session_logger.end_session(exit_code=1, exit_reason="prd_not_found")
            return 1

        # Initialize progress file (skip if resuming to preserve existing progress)
        if not self.resume:
            progress.init_progress_file(self.progress_path)

        # Get starting iteration from existing progress
        progress_content = progress.read_progress(self.progress_path)
        iteration = progress.get_iteration_count(progress_content) + 1

        # Initialize statistics tracking
        prd_content = prd.read_prd(self.prd_path)
        tasks = prd.parse_tasks(prd_content)
        completed, total = prd.get_completion_status(tasks)
        self.stats_tasks_completed_start = completed
        self.stats_total_tasks = total

        # Set iteration before entering live context so banner shows correct value
        self.live.iteration = iteration

        with self.live:
            if self.verbose:
                self.live.log(f"[zoyd] Starting at iteration {iteration}", style="dim")

            # Validate PRD and show any warnings
            validation_warnings = prd.validate_prd(prd_content)
            if validation_warnings:
                self.live.log_warning("PRD Validation:")
                for warning in validation_warnings:
                    self.live.log(f"  Line {warning.line_number}: {warning.message}")

            try:
                while iteration <= self.max_iterations:
                    # Track iteration start time
                    iteration_start = time.time()

                    # Read current state
                    prd_content = prd.read_prd(self.prd_path)
                    progress_content = progress.read_progress(self.progress_path)
                    tasks = prd.parse_tasks(prd_content)
                    completed, total = prd.get_completion_status(tasks)

                    # Update live display
                    self.live.iteration = iteration
                    self.live.cost = self.stats_total_cost
                    self.live.log_iteration_start(iteration, completed, total)
                    self.live.log(f"Rate limit: {self.get_rate_limit_status()}")

                    # Emit ITERATION_START event
                    self.events.emit(EventType.ITERATION_START, {
                        "iteration": iteration,
                        "completed": completed,
                        "total": total,
                    })

                    # Show elapsed time in verbose mode
                    if self.verbose and self.start_time:
                        elapsed = time.time() - self.start_time
                        self.live.log(f"[zoyd] Elapsed time: {format_duration(elapsed)}", style="dim")

                    # Check if all tasks complete
                    if prd.is_all_complete(tasks):
                        self.live.log_success("All tasks complete!")
                        self.stats_tasks_completed_end = completed
                        self.events.emit(EventType.LOOP_END, {
                            "status": "complete",
                            "exit_code": 0,
                            "iterations": self.stats_iterations,
                            "total_cost": self.stats_total_cost,
                        })
                        if self.session_logger is not None:
                            self.session_logger.end_session(exit_code=0, exit_reason="complete")
                        self.print_summary()
                        return 0

                    # Show next task
                    next_task = prd.get_next_incomplete_task(tasks)
                    if next_task:
                        self.live.set_task(next_task.text)
                        self.live.log(f"Next task: {next_task.text}")

                    # Build prompt
                    prompt = build_prompt(
                        prd_content=prd_content,
                        progress_content=progress_content,
                        iteration=iteration,
                        completed=completed,
                        total=total,
                        current_task=next_task.text if next_task else "(No incomplete tasks)",
                    )

                    if self.dry_run:
                        self.live.log("--- DRY RUN: Would send prompt ---")
                        self.live.log(prompt)
                        self.live.log("--- END PROMPT ---")
                        iteration += 1
                        continue

                    # Invoke Claude in sandbox mode with spinner
                    self.live.start_spinner("Invoking Claude...")
                    if self.verbose:
                        self.live.log("[zoyd] Invoking Claude in sandbox mode...", style="dim")

                    # Emit CLAUDE_INVOKE event
                    self.events.emit(EventType.CLAUDE_INVOKE, {
                        "iteration": iteration,
                        "task": next_task.text if next_task else None,
                        "model": self.model,
                    })

                    track_cost = self.max_cost is not None
                    return_code, output, cost_usd = invoke_claude(
                        prompt, self.model, track_cost=track_cost
                    )
                    self.live.stop_spinner()

                    # Emit CLAUDE_RESPONSE or CLAUDE_ERROR event
                    if return_code == 0:
                        self.events.emit(EventType.CLAUDE_RESPONSE, {
                            "iteration": iteration,
                            "return_code": return_code,
                            "cost_usd": cost_usd,
                            "output_length": len(output),
                            "output": output,
                        })
                    else:
                        self.events.emit(EventType.CLAUDE_ERROR, {
                            "iteration": iteration,
                            "return_code": return_code,
                            "output": output[:500],  # Truncate for event
                        })

                    # Track cost if available
                    if cost_usd is not None:
                        self.stats_total_cost += cost_usd
                        self.live.cost = self.stats_total_cost
                        if self.verbose:
                            self.live.log(f"[zoyd] Iteration cost: ${cost_usd:.4f}, Total: ${self.stats_total_cost:.4f}", style="dim")

                        # Emit COST_UPDATE event
                        self.events.emit(EventType.COST_UPDATE, {
                            "iteration_cost": cost_usd,
                            "total_cost": self.stats_total_cost,
                            "max_cost": self.max_cost,
                        })

                        # Check if we've exceeded max cost
                        if self.max_cost is not None and self.stats_total_cost >= self.max_cost:
                            self.live.log_error(f"Cost limit exceeded: ${self.stats_total_cost:.4f} >= ${self.max_cost:.2f}")
                            # Emit COST_LIMIT_EXCEEDED event
                            self.events.emit(EventType.COST_LIMIT_EXCEEDED, {
                                "total_cost": self.stats_total_cost,
                                "max_cost": self.max_cost,
                            })
                            self.stats_tasks_completed_end = completed
                            self.stats_iterations += 1
                            self.stats_successes += 1
                            self.events.emit(EventType.LOOP_END, {
                                "status": "cost_limit",
                                "exit_code": 4,
                                "iterations": self.stats_iterations,
                                "total_cost": self.stats_total_cost,
                            })
                            if self.session_logger is not None:
                                self.session_logger.end_session(exit_code=4, exit_reason="cost_limit")
                            self.print_summary()
                            return 4  # Exit code 4 for cost limit exceeded

                    if return_code != 0:
                        self.consecutive_failures += 1
                        self.stats_failures += 1
                        self.stats_iterations += 1
                        self.live.log_error(f"Claude returned error (code {return_code})")
                        if self.verbose:
                            self.live.log_markdown(output)

                        # Fail-fast: exit immediately on first failure
                        if self.fail_fast:
                            self.live.log_error("Fail-fast mode: exiting on first failure")
                            self.stats_tasks_completed_end = completed
                            self.events.emit(EventType.LOOP_END, {
                                "status": "fail_fast",
                                "exit_code": 2,
                                "iterations": self.stats_iterations,
                                "total_cost": self.stats_total_cost,
                            })
                            if self.session_logger is not None:
                                self.session_logger.end_session(exit_code=2, exit_reason="fail_fast")
                            self.print_summary()
                            return 2

                        if self.consecutive_failures >= self.max_consecutive_failures:
                            self.live.log_error(f"Too many consecutive failures ({self.consecutive_failures})")
                            self.stats_tasks_completed_end = completed
                            self.events.emit(EventType.LOOP_END, {
                                "status": "max_failures",
                                "exit_code": 2,
                                "iterations": self.stats_iterations,
                                "total_cost": self.stats_total_cost,
                            })
                            if self.session_logger is not None:
                                self.session_logger.end_session(exit_code=2, exit_reason="max_failures")
                            self.print_summary()
                            return 2

                        # Apply exponential backoff on failure
                        backoff = self.get_backoff_delay()
                        if self.verbose:
                            self.live.log(f"[zoyd] Backing off for {backoff:.1f}s after failure {self.consecutive_failures}", style="dim")
                        time.sleep(backoff)
                    else:
                        self.consecutive_failures = 0
                        self.stats_successes += 1
                        self.stats_iterations += 1
                        if self.verbose:
                            self.live.log_markdown(output)

                        # Check if Claude indicated it cannot complete the task
                        cannot_complete, reason = detect_cannot_complete(output)
                        if cannot_complete:
                            self.live.log_warning(f"[BLOCKED] Claude cannot complete task: {reason}")
                            if self.verbose:
                                self.live.log(f"[zoyd] Task blocked - detected pattern: {reason}", style="dim")
                            # Emit TASK_BLOCKED event
                            self.events.emit(EventType.TASK_BLOCKED, {
                                "iteration": iteration,
                                "task": next_task.text if next_task else None,
                                "reason": reason,
                            })
                        else:
                            # Auto-commit if enabled and iteration succeeded
                            if self.auto_commit and next_task:
                                if self.verbose:
                                    self.live.log("[zoyd] Generating commit message...", style="dim")
                                commit_msg = generate_commit_message(
                                    output, next_task.text, self.model
                                )
                                if commit_msg:
                                    if self.verbose:
                                        self.live.log("[zoyd] Creating commit...", style="dim")
                                    # Emit COMMIT_START event
                                    self.events.emit(EventType.COMMIT_START, {
                                        "iteration": iteration,
                                        "task": next_task.text,
                                        "message": commit_msg.split("\n")[0],
                                    })
                                    success, commit_output = commit_changes(commit_msg)
                                    if success:
                                        self.live.log_success(f"Committed: {commit_msg.split(chr(10))[0]}")
                                        # Emit COMMIT_SUCCESS event
                                        self.events.emit(EventType.COMMIT_SUCCESS, {
                                            "iteration": iteration,
                                            "message": commit_msg.split("\n")[0],
                                        })
                                        # Emit TASK_COMPLETE event on successful commit
                                        self.events.emit(EventType.TASK_COMPLETE, {
                                            "iteration": iteration,
                                            "task": next_task.text,
                                        })
                                    else:
                                        if self.verbose:
                                            self.live.log(f"[zoyd] Commit failed: {commit_output}", style="dim")
                                        # Emit COMMIT_FAILED event
                                        self.events.emit(EventType.COMMIT_FAILED, {
                                            "iteration": iteration,
                                            "message": commit_msg.split("\n")[0],
                                            "error": commit_output,
                                        })
                                elif self.verbose:
                                    self.live.log("[zoyd] Failed to generate commit message", style="dim")

                    # Record progress (with blocked status if detected)
                    cannot_complete, reason = detect_cannot_complete(output)
                    progress.append_iteration(
                        self.progress_path,
                        iteration,
                        output,
                        cannot_complete=cannot_complete,
                        cannot_complete_reason=reason,
                    )
                    if self.verbose:
                        self.live.log(f"[zoyd] Recorded iteration {iteration}", style="dim")

                    # Show iteration timing in verbose mode
                    iteration_duration = time.time() - iteration_start
                    if self.verbose:
                        self.live.log(f"[zoyd] Iteration {iteration} completed in {format_duration(iteration_duration)}", style="dim")

                    # Emit ITERATION_END event
                    self.events.emit(EventType.ITERATION_END, {
                        "iteration": iteration,
                        "duration": iteration_duration,
                        "success": return_code == 0,
                        "cost_usd": cost_usd,
                    })

                    iteration += 1
                    self.live.set_task(None)

                    # Rate limiting pause between iterations
                    if iteration <= self.max_iterations and self.delay > 0:
                        time.sleep(self.delay)

                self.live.log(f"Reached max iterations ({self.max_iterations})")
                # Get final task count
                tasks = prd.parse_tasks(prd.read_prd(self.prd_path))
                completed, _ = prd.get_completion_status(tasks)
                self.stats_tasks_completed_end = completed
                self.events.emit(EventType.LOOP_END, {
                    "status": "max_iterations",
                    "exit_code": 1,
                    "iterations": self.stats_iterations,
                    "total_cost": self.stats_total_cost,
                })
                if self.session_logger is not None:
                    self.session_logger.end_session(exit_code=1, exit_reason="max_iterations")
                self.print_summary()
                return 1

            except KeyboardInterrupt:
                self.live.log("\nInterrupted by user")
                # Get final task count
                tasks = prd.parse_tasks(prd.read_prd(self.prd_path))
                completed, _ = prd.get_completion_status(tasks)
                self.stats_tasks_completed_end = completed
                self.events.emit(EventType.LOOP_END, {
                    "status": "interrupted",
                    "exit_code": 130,
                    "iterations": self.stats_iterations,
                    "total_cost": self.stats_total_cost,
                })
                if self.session_logger is not None:
                    self.session_logger.end_session(exit_code=130, exit_reason="interrupted")
                self.print_summary()
                return 130
