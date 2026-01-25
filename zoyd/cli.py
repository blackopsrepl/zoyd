"""Click CLI entry point for Zoyd."""

import json
import sys
from pathlib import Path

import click

from . import __version__, prd, progress
from .config import load_config
from .loop import LoopRunner
from .tui.banner import print_banner
from .tui.console import create_console
from .tui.status import print_status


@click.group()
@click.version_option(version=__version__)
def cli():
    """Zoyd - Minimal autonomous agent loop for Claude Code."""
    pass


@cli.command()
@click.option(
    "--prd",
    "prd_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to PRD file (default: PRD.md or from zoyd.toml)",
)
@click.option(
    "--progress",
    "progress_path",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to progress file (default: progress.txt or from zoyd.toml)",
)
@click.option(
    "-n",
    "--max-iterations",
    default=None,
    type=int,
    help="Maximum iterations to run (default: 10 or from zoyd.toml)",
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
    default=None,
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--delay",
    default=None,
    type=float,
    help="Seconds to pause between iterations (default: 1.0 or from zoyd.toml)",
)
@click.option(
    "--auto-commit/--no-auto-commit",
    default=None,
    help="Automatically commit changes after each completed task (default: enabled)",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from existing progress file (skip already-completed tasks)",
)
@click.option(
    "--fail-fast",
    default=None,
    is_flag=True,
    help="Exit immediately on first failure instead of retrying",
)
@click.option(
    "--max-cost",
    default=None,
    type=float,
    help="Maximum cost in USD before stopping (estimates token usage)",
)
@click.pass_context
def run(
    ctx: click.Context,
    prd_path: Path | None,
    progress_path: Path | None,
    max_iterations: int | None,
    model: str | None,
    dry_run: bool,
    verbose: bool | None,
    delay: float | None,
    auto_commit: bool | None,
    resume: bool,
    fail_fast: bool | None,
    max_cost: float | None,
):
    """Run the Zoyd loop against a PRD file.

    Zoyd invokes Claude Code repeatedly to complete tasks defined in the PRD.
    Changes are made directly in the current directory with sandbox isolation.

    Options can be set in zoyd.toml config file. CLI options override config values.
    """
    # Load config file and apply defaults
    config = load_config()

    # Apply config defaults where CLI options weren't provided
    if prd_path is None:
        prd_path = Path(config.prd)
        if not prd_path.exists():
            click.echo(f"Error: PRD file '{prd_path}' does not exist", err=True)
            sys.exit(1)
    if progress_path is None:
        progress_path = Path(config.progress)
    if max_iterations is None:
        max_iterations = config.max_iterations
    if model is None:
        model = config.model
    if delay is None:
        delay = config.delay
    if auto_commit is None:
        auto_commit = config.auto_commit
    if verbose is None:
        verbose = config.verbose
    if fail_fast is None:
        fail_fast = config.fail_fast
    if max_cost is None:
        max_cost = config.max_cost

    # Display startup banner with version info
    console = create_console(file=sys.stdout)
    print_banner(
        console=console,
        title=f"v{__version__}",
        subtitle="Autonomous Loop" if not dry_run else "Autonomous Loop [DRY RUN]",
    )

    # Validate PRD on startup
    prd_content = prd.read_prd(prd_path)
    warnings = prd.validate_prd(prd_content)
    if warnings:
        click.echo()
        click.echo(click.style("PRD validation warnings:", fg="yellow"))
        for warning in warnings:
            click.echo(click.style(f"  Line {warning.line_number}: {warning.message}", fg="yellow"))
            click.echo(click.style(f"    {warning.line_content.strip()}", fg="yellow", dim=True))
        click.echo()

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
        max_cost=max_cost,
    )

    exit_code = runner.run()
    sys.exit(exit_code)


PRD_TEMPLATE = """\
# Project: {project_name}

Brief description of your project and what you want to accomplish.

## Tasks

- [ ] First task to complete
- [ ] Second task to complete
- [ ] Third task to complete

## Notes

Each task should be:
- Specific and completable in one iteration
- Marked with `[ ]` when incomplete
- Marked with `[x]` when complete

Zoyd will work through tasks sequentially until all are complete.

## Success Criteria

- All checkboxes marked `[x]`
- Tests pass
- Code works as expected
"""


@cli.command()
@click.option(
    "--output",
    "-o",
    "output_path",
    default="PRD.md",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path for the PRD file (default: PRD.md)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing file",
)
@click.argument("project_name", default="My Project")
def init(output_path: Path, force: bool, project_name: str):
    """Create a starter PRD.md template.

    Creates a new PRD file with a basic structure including tasks,
    notes, and success criteria sections.

    Examples:

        zoyd init "My Awesome Project"

        zoyd init --output docs/tasks.md "Feature Work"
    """
    if output_path.exists() and not force:
        click.echo(f"Error: '{output_path}' already exists. Use --force to overwrite.", err=True)
        sys.exit(1)

    content = PRD_TEMPLATE.format(project_name=project_name)
    output_path.write_text(content)
    click.echo(f"Created {output_path}")
    click.echo(f"\nNext steps:")
    click.echo(f"  1. Edit {output_path} to add your tasks")
    click.echo(f"  2. Run: zoyd run --prd {output_path}")


@cli.command()
@click.option(
    "--prd",
    "prd_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to PRD file (default: PRD.md or from zoyd.toml)",
)
@click.option(
    "--progress",
    "progress_path",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to progress file (default: progress.txt or from zoyd.toml)",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output status in JSON format for machine-readable output",
)
def status(prd_path: Path | None, progress_path: Path | None, json_output: bool):
    """Show PRD completion status.

    Options can be set in zoyd.toml config file. CLI options override config values.
    """
    # Load config file and apply defaults
    config = load_config()

    if prd_path is None:
        prd_path = Path(config.prd)
        if not prd_path.exists():
            click.echo(f"Error: PRD file '{prd_path}' does not exist", err=True)
            sys.exit(1)
    if progress_path is None:
        progress_path = Path(config.progress)

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

    # Use rich TUI components for display
    # Create a fresh console that writes to current stdout (important for test runners)
    console = create_console(file=sys.stdout)
    print_status(
        console,
        tasks,
        prd_path=prd_path,
        iterations=iteration_count,
        show_tree=True,
        show_progress=True,
    )

    sys.exit(0 if is_complete else 1)


if __name__ == "__main__":
    cli()
