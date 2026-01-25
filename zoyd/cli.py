"""Click CLI entry point for Zoyd."""

import json
import sys
from pathlib import Path

import click

from . import __version__, prd, progress
from .loop import LoopRunner


@click.group()
@click.version_option(version=__version__)
def cli():
    """Zoyd - Minimal autonomous agent loop for Claude Code."""
    pass


@cli.command()
@click.option(
    "--prd",
    "prd_path",
    default="PRD.md",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to PRD file (default: PRD.md)",
)
@click.option(
    "--progress",
    "progress_path",
    default="progress.txt",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to progress file (default: progress.txt)",
)
@click.option(
    "-n",
    "--max-iterations",
    default=10,
    type=int,
    help="Maximum iterations to run (default: 10)",
)
@click.option(
    "--model",
    default=None,
    help="Claude model to use (e.g., opus, sonnet)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would execute without running",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--delay",
    default=1.0,
    type=float,
    help="Seconds to pause between iterations (default: 1.0)",
)
@click.option(
    "--auto-commit/--no-auto-commit",
    default=True,
    help="Automatically commit changes after each completed task (default: enabled)",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from existing progress file (skip already-completed tasks)",
)
@click.option(
    "--fail-fast",
    is_flag=True,
    help="Exit immediately on first failure instead of retrying",
)
def run(
    prd_path: Path,
    progress_path: Path,
    max_iterations: int,
    model: str | None,
    dry_run: bool,
    verbose: bool,
    delay: float,
    auto_commit: bool,
    resume: bool,
    fail_fast: bool,
):
    """Run the Zoyd loop against a PRD file.

    Zoyd invokes Claude Code repeatedly to complete tasks defined in the PRD.
    Changes are made directly in the current directory with sandbox isolation.
    """
    click.echo(f"Zoyd v{__version__}")
    click.echo(f"PRD: {prd_path}")
    click.echo(f"Progress: {progress_path}")
    click.echo(f"Max iterations: {max_iterations}")
    if model:
        click.echo(f"Model: {model}")
    if dry_run:
        click.echo("Mode: DRY RUN")

    # Handle resume mode
    if resume:
        if not progress_path.exists():
            click.echo(f"Error: Cannot resume - progress file '{progress_path}' does not exist", err=True)
            sys.exit(1)
        progress_content = progress_path.read_text()
        iteration_count = progress.get_iteration_count(progress_content)
        if iteration_count == 0:
            click.echo("Warning: Progress file exists but has no iterations recorded")
        else:
            click.echo(f"Resuming from iteration {iteration_count + 1}")
        # Show completed tasks
        prd_content = prd.read_prd(prd_path)
        tasks = prd.parse_tasks(prd_content)
        completed_tasks = [t for t in tasks if t.complete]
        if completed_tasks:
            click.echo(f"Skipping {len(completed_tasks)} completed task(s):")
            for task in completed_tasks:
                click.echo(f"  [x] {task.text}")

    runner = LoopRunner(
        prd_path=prd_path,
        progress_path=progress_path,
        max_iterations=max_iterations,
        model=model,
        dry_run=dry_run,
        verbose=verbose,
        delay=delay,
        auto_commit=auto_commit,
        resume=resume,
        fail_fast=fail_fast,
    )

    exit_code = runner.run()
    sys.exit(exit_code)


@cli.command()
@click.option(
    "--prd",
    "prd_path",
    default="PRD.md",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to PRD file (default: PRD.md)",
)
@click.option(
    "--progress",
    "progress_path",
    default="progress.txt",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to progress file (default: progress.txt)",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output status in JSON format for machine-readable output",
)
def status(prd_path: Path, progress_path: Path, json_output: bool):
    """Show PRD completion status."""
    prd_content = prd.read_prd(prd_path)
    tasks = prd.parse_tasks(prd_content)
    completed, total = prd.get_completion_status(tasks)
    is_complete = prd.is_all_complete(tasks)
    next_task = prd.get_next_incomplete_task(tasks)

    iteration_count = 0
    if progress_path.exists():
        progress_content = progress.read_progress(progress_path)
        iteration_count = progress.get_iteration_count(progress_content)

    if json_output:
        output = {
            "prd": str(prd_path),
            "tasks": {
                "completed": completed,
                "total": total,
                "items": [
                    {
                        "text": task.text,
                        "complete": task.complete,
                        "line_number": task.line_number,
                    }
                    for task in tasks
                ],
            },
            "iterations": iteration_count,
            "status": "complete" if is_complete else "in_progress",
            "next_task": next_task.text if next_task else None,
        }
        click.echo(json.dumps(output, indent=2))
        sys.exit(0 if is_complete else 1)

    click.echo(f"PRD: {prd_path}")
    click.echo(f"Tasks: {completed}/{total} complete")
    click.echo()

    if tasks:
        click.echo("Tasks:")
        for task in tasks:
            marker = "[x]" if task.complete else "[ ]"
            click.echo(f"  {marker} {task.text}")
        click.echo()

    if iteration_count > 0:
        click.echo(f"Iterations completed: {iteration_count}")

    if is_complete:
        click.echo("\nStatus: COMPLETE")
        sys.exit(0)
    else:
        click.echo("\nStatus: IN PROGRESS")
        if next_task:
            click.echo(f"Next task: {next_task.text}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
