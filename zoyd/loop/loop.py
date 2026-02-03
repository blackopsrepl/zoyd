"""Main loop orchestrator - invoke Claude Code repeatedly."""

from __future__ import annotations

import json as json_module
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from .invoke import invoke_claude, format_duration
from zoyd import prd, progress
from zoyd.config import load_config
from zoyd.session.embedding import get_provider
from zoyd.session.logger import SessionLogger
from zoyd.session.storage import create_storage
from zoyd.session.vectors import VectorMemory
from zoyd.tui.console import create_console
from zoyd.tui.events import EventEmitter, EventType
from zoyd.tui.live import (
    LiveDisplay,
    PlainDisplay,
    create_live_display,
    create_plain_display,
)

from .prompt_templates import (
    CANNOT_COMPLETE_PATTERNS,
    PROMPT_TEMPLATE,
    PROMPT_TEMPLATE_WITH_MEMORY,
    COMMIT_PROMPT_TEMPLATE,
    COMMIT_SYSTEM_PROMPT,
    detect_cannot_complete,
)

from .prompt_builder import (
    build_prompt,
    build_prompt_with_memory,
    _extract_recent_iterations,
    _format_relevant_context,
)

from .commit_manager import (
    generate_commit_message,
    commit_changes,
)


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
        vector_memory: bool | None = None,
        vector_top_k: int | None = None,
        vector_recent_n: int | None = None,
        sandbox: bool = True,
        rabid: bool = False,
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
        # Vector memory options
        self.vector_memory_enabled = vector_memory if vector_memory is not None else cfg.vector_memory
        self.vector_top_k = vector_top_k if vector_top_k is not None else cfg.vector_top_k
        self.vector_recent_n = vector_recent_n if vector_recent_n is not None else cfg.vector_recent_n
        self.sandbox = sandbox
        self.rabid = rabid
        # Create display for output (TUI or plain depending on settings)
        if not self.tui_enabled:
            self.live: LiveDisplay | PlainDisplay = create_plain_display(
                prd_path=str(self.prd_path),
                progress_path=str(self.progress_path),
                max_iterations=self.max_iterations,
                model=self.model,
                max_cost=self.max_cost,
                rabid=self.rabid,
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
                rabid=self.rabid,
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
        # Vector memory for semantic retrieval
        # Skip in dry-run mode (no point connecting to Redis for a dry run)
        self.vector_mem: VectorMemory | None = None
        if self.vector_memory_enabled and not self.dry_run:
            provider = get_provider(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
            )
            if provider.is_available():
                self.vector_mem = VectorMemory(
                    provider=provider,
                    host=self.redis_host,
                    port=self.redis_port,
                    db=self.redis_db,
                    password=self.redis_password,
                )

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

        # Generate a session ID for vector memory (shared across all iterations)
        self.vector_session_id = uuid.uuid4().hex

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
                    self.live.set_completion(completed, total)

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

                    # Store incomplete task embeddings for vector memory
                    if self.vector_mem is not None:
                        for task in tasks:
                            if not task.complete:
                                self.vector_mem.store_task(
                                    session_id=self.vector_session_id,
                                    task_text=task.text,
                                    line_number=task.line_number,
                                )

                    # Build prompt
                    current_task_text = next_task.text if next_task else "(No incomplete tasks)"
                    if self.vector_mem is not None and self.vector_mem.is_available:
                        # Use vector memory for semantic retrieval
                        results = self.vector_mem.find_relevant_outputs(
                            query_text=current_task_text,
                            count=self.vector_top_k,
                        )
                        relevant_context = _format_relevant_context(results)
                        recent_progress = _extract_recent_iterations(
                            progress_content, self.vector_recent_n
                        )
                        prompt = build_prompt_with_memory(
                            prd_content=prd_content,
                            relevant_context=relevant_context,
                            recent_progress=recent_progress,
                            iteration=iteration,
                            completed=completed,
                            total=total,
                            current_task=current_task_text,
                        )
                    else:
                        prompt = build_prompt(
                            prd_content=prd_content,
                            progress_content=progress_content,
                            iteration=iteration,
                            completed=completed,
                            total=total,
                            current_task=current_task_text,
                        )

                    if self.dry_run:
                        self.live.log("--- DRY RUN: Would send prompt ---")
                        self.live.log(prompt)
                        self.live.log("--- END PROMPT ---")
                        iteration += 1
                        continue

                    # Invoke Claude with spinner
                    self.live.start_spinner("Invoking Claude...")
                    if self.verbose:
                        mode = "sandbox" if self.sandbox else "rabid"
                        self.live.log(f"[zoyd] Invoking Claude in {mode} mode...", style="dim")

                    # Emit CLAUDE_INVOKE event
                    self.events.emit(EventType.CLAUDE_INVOKE, {
                        "iteration": iteration,
                        "task": next_task.text if next_task else None,
                        "model": self.model,
                    })

                    track_cost = self.max_cost is not None
                    return_code, output, cost_usd = invoke_claude(
                        prompt, self.model, track_cost=track_cost, sandbox=self.sandbox
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
                        self.live.log_lines(output)

                        # Store error in vector memory for pattern matching
                        if self.vector_mem is not None:
                            self.vector_mem.store_error(
                                session_id=self.vector_session_id,
                                iteration=iteration,
                                output=output,
                                task_text=next_task.text if next_task else "",
                            )

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
                        self.live.log_lines(output)

                        # Store output in vector memory for semantic retrieval
                        if self.vector_mem is not None:
                            self.vector_mem.store_output(
                                session_id=self.vector_session_id,
                                iteration=iteration,
                                output=output,
                                task_text=next_task.text if next_task else "",
                                return_code=return_code,
                            )

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
