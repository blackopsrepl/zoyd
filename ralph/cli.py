"""Click CLI entry point for Ralph."""

import sys
from pathlib import Path

import click

from . import __version__, prd, progress
from .loop import LoopRunner


@click.group()
@click.version_option(version=__version__)
def cli():
    """Ralph - Minimal autonomous agent loop for Claude Code."""
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
def run(
    prd_path: Path,
    progress_path: Path,
    max_iterations: int,
    model: str | None,
    dry_run: bool,
    verbose: bool,
):
    """Run the Ralph loop against a PRD file."""
    click.echo(f"Ralph v{__version__}")
    click.echo(f"PRD: {prd_path}")
    click.echo(f"Progress: {progress_path}")
    click.echo(f"Max iterations: {max_iterations}")
    if model:
        click.echo(f"Model: {model}")
    if dry_run:
        click.echo("Mode: DRY RUN")

    runner = LoopRunner(
        prd_path=prd_path,
        progress_path=progress_path,
        max_iterations=max_iterations,
        model=model,
        dry_run=dry_run,
        verbose=verbose,
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
def status(prd_path: Path, progress_path: Path):
    """Show PRD completion status."""
    # Read and parse PRD
    prd_content = prd.read_prd(prd_path)
    tasks = prd.parse_tasks(prd_content)
    completed, total = prd.get_completion_status(tasks)

    click.echo(f"PRD: {prd_path}")
    click.echo(f"Tasks: {completed}/{total} complete")
    click.echo()

    if tasks:
        click.echo("Tasks:")
        for task in tasks:
            marker = "[x]" if task.complete else "[ ]"
            click.echo(f"  {marker} {task.text}")
        click.echo()

    # Show iteration count if progress exists
    if progress_path.exists():
        progress_content = progress.read_progress(progress_path)
        iteration_count = progress.get_iteration_count(progress_content)
        click.echo(f"Iterations completed: {iteration_count}")

    # Exit with appropriate code
    if prd.is_all_complete(tasks):
        click.echo("\nStatus: COMPLETE")
        sys.exit(0)
    else:
        click.echo("\nStatus: IN PROGRESS")
        next_task = prd.get_next_incomplete_task(tasks)
        if next_task:
            click.echo(f"Next task: {next_task.text}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
