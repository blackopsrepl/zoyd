"""Jail isolation - worktree and sandbox management for zoyd."""

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


class JailError(Exception):
    """Raised when jail setup or teardown fails."""


@dataclass
class Jail:
    """Represents an isolated jail environment using git worktree."""

    worktree_path: Path
    branch_name: str
    source_repo: Path
    _created: bool = False

    def __enter__(self) -> "Jail":
        """Set up the jail (worktree) on context entry."""
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Tear down the jail (worktree) on context exit."""
        self.teardown()

    def setup(self) -> None:
        """Create the git worktree for this jail.

        Raises:
            JailError: If worktree creation fails.
        """
        if self._created:
            return

        # Create parent directory if needed
        self.worktree_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a new branch for this worktree
        try:
            result = subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    self.branch_name,
                    str(self.worktree_path),
                ],
                cwd=self.source_repo,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise JailError(f"Failed to create worktree: {result.stderr}")
            self._created = True
        except FileNotFoundError:
            raise JailError("git command not found")

    def teardown(self) -> None:
        """Remove the git worktree.

        Raises:
            JailError: If worktree removal fails.
        """
        if not self._created:
            return

        try:
            # Remove the worktree
            result = subprocess.run(
                ["git", "worktree", "remove", "--force", str(self.worktree_path)],
                cwd=self.source_repo,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                # Try to clean up manually if git worktree remove fails
                import shutil

                if self.worktree_path.exists():
                    shutil.rmtree(self.worktree_path)

                # Prune the worktree reference
                subprocess.run(
                    ["git", "worktree", "prune"],
                    cwd=self.source_repo,
                    capture_output=True,
                    check=False,
                )

            # Delete the branch
            subprocess.run(
                ["git", "branch", "-D", self.branch_name],
                cwd=self.source_repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self._created = False
        except FileNotFoundError:
            raise JailError("git command not found")

    def sync_to_source(self) -> tuple[bool, str]:
        """Merge changes from jail worktree back to source branch.

        Returns:
            Tuple of (success, message).
        """
        if not self._created:
            return False, "Jail not set up"

        try:
            # Get the current branch of the source repo
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.source_repo,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return False, f"Failed to get source branch: {result.stderr}"
            source_branch = result.stdout.strip()

            # Merge jail branch into source branch
            result = subprocess.run(
                ["git", "merge", "--no-ff", self.branch_name, "-m", f"Merge zoyd jail branch {self.branch_name}"],
                cwd=self.source_repo,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return False, f"Failed to merge jail branch: {result.stderr}"

            return True, f"Merged {self.branch_name} into {source_branch}"
        except FileNotFoundError:
            return False, "git command not found"


def create_jail(
    source_repo: Path,
    worktree_base: Path | None = None,
    branch_prefix: str = "zoyd-jail",
) -> Jail:
    """Create a new jail environment.

    Args:
        source_repo: Path to the source git repository.
        worktree_base: Base directory for worktrees. Defaults to source_repo/.zoyd-jails/
        branch_prefix: Prefix for jail branch names.

    Returns:
        A Jail object (not yet set up, use as context manager or call setup()).

    Raises:
        JailError: If source_repo is not a git repository.
    """
    # Verify source is a git repo
    if not (source_repo / ".git").exists() and not _is_git_worktree(source_repo):
        raise JailError(f"Not a git repository: {source_repo}")

    # Generate unique jail ID
    jail_id = uuid.uuid4().hex[:8]
    branch_name = f"{branch_prefix}-{jail_id}"

    # Default worktree location
    if worktree_base is None:
        worktree_base = source_repo / ".zoyd-jails"

    worktree_path = worktree_base / jail_id

    return Jail(
        worktree_path=worktree_path,
        branch_name=branch_name,
        source_repo=source_repo,
    )


def _is_git_worktree(path: Path) -> bool:
    """Check if path is inside a git worktree.

    Args:
        path: Path to check.

    Returns:
        True if path is a git worktree.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def get_repo_root(path: Path) -> Path:
    """Get the root directory of the git repository.

    Args:
        path: A path within the git repository.

    Returns:
        Path to the repository root.

    Raises:
        JailError: If path is not in a git repository.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise JailError(f"Not a git repository: {path}")
    return Path(result.stdout.strip())
