"""Tests for jail module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zoyd.jail import Jail, JailError, create_jail, get_repo_root, _is_git_worktree


class TestJail:
    def test_jail_creation(self, tmp_path):
        """Test that Jail object can be created with correct attributes."""
        worktree_path = tmp_path / "worktree"
        jail = Jail(
            worktree_path=worktree_path,
            branch_name="test-branch",
            source_repo=tmp_path,
        )
        assert jail.worktree_path == worktree_path
        assert jail.branch_name == "test-branch"
        assert jail.source_repo == tmp_path
        assert jail._created is False

    @patch("zoyd.jail.subprocess.run")
    def test_jail_setup_success(self, mock_run, tmp_path):
        """Test successful jail setup creates worktree."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree_path = tmp_path / "worktree"

        jail = Jail(
            worktree_path=worktree_path,
            branch_name="test-branch",
            source_repo=tmp_path,
        )
        jail.setup()

        assert jail._created is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "worktree" in call_args[0][0]
        assert "add" in call_args[0][0]

    @patch("zoyd.jail.subprocess.run")
    def test_jail_setup_failure(self, mock_run, tmp_path):
        """Test that jail setup raises JailError on failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="fatal: error")
        worktree_path = tmp_path / "worktree"

        jail = Jail(
            worktree_path=worktree_path,
            branch_name="test-branch",
            source_repo=tmp_path,
        )

        with pytest.raises(JailError) as exc_info:
            jail.setup()
        assert "Failed to create worktree" in str(exc_info.value)

    @patch("zoyd.jail.subprocess.run")
    def test_jail_setup_git_not_found(self, mock_run, tmp_path):
        """Test that jail setup raises JailError when git not found."""
        mock_run.side_effect = FileNotFoundError("git not found")
        worktree_path = tmp_path / "worktree"

        jail = Jail(
            worktree_path=worktree_path,
            branch_name="test-branch",
            source_repo=tmp_path,
        )

        with pytest.raises(JailError) as exc_info:
            jail.setup()
        assert "git command not found" in str(exc_info.value)

    @patch("zoyd.jail.subprocess.run")
    def test_jail_setup_copy_files(self, mock_run, tmp_path):
        """Test that setup copies uncommitted files into the jail."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir(parents=True)

        # Create source files
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# My PRD\n- [ ] Task 1")
        progress_file = tmp_path / "subdir" / "progress.txt"
        progress_file.parent.mkdir(parents=True)
        progress_file.write_text("# Progress")
        nonexistent_file = tmp_path / "does-not-exist.txt"

        jail = Jail(
            worktree_path=worktree_path,
            branch_name="test-branch",
            source_repo=tmp_path,
        )
        jail.setup(copy_files=[prd_file, progress_file, nonexistent_file])

        # Check files were copied with correct relative paths
        assert (worktree_path / "PRD.md").exists()
        assert (worktree_path / "PRD.md").read_text() == "# My PRD\n- [ ] Task 1"
        assert (worktree_path / "subdir" / "progress.txt").exists()
        assert (worktree_path / "subdir" / "progress.txt").read_text() == "# Progress"
        # Non-existent file should be silently skipped
        assert not (worktree_path / "does-not-exist.txt").exists()

    @patch("zoyd.jail.subprocess.run")
    def test_jail_teardown_success(self, mock_run, tmp_path):
        """Test successful jail teardown removes worktree."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree_path = tmp_path / "worktree"

        jail = Jail(
            worktree_path=worktree_path,
            branch_name="test-branch",
            source_repo=tmp_path,
            _created=True,
        )
        jail.teardown()

        assert jail._created is False
        # Should call worktree remove and branch delete
        assert mock_run.call_count == 2

    @patch("zoyd.jail.subprocess.run")
    def test_jail_teardown_skips_if_not_created(self, mock_run, tmp_path):
        """Test that teardown does nothing if jail was never created."""
        worktree_path = tmp_path / "worktree"

        jail = Jail(
            worktree_path=worktree_path,
            branch_name="test-branch",
            source_repo=tmp_path,
            _created=False,
        )
        jail.teardown()

        mock_run.assert_not_called()

    @patch("zoyd.jail.subprocess.run")
    def test_jail_context_manager(self, mock_run, tmp_path):
        """Test that Jail works as a context manager."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree_path = tmp_path / "worktree"

        jail = Jail(
            worktree_path=worktree_path,
            branch_name="test-branch",
            source_repo=tmp_path,
        )

        with jail as j:
            assert j._created is True
            assert j.worktree_path == worktree_path

        assert jail._created is False

    @patch("zoyd.jail.subprocess.run")
    def test_jail_sync_to_source_success(self, mock_run, tmp_path):
        """Test successful sync from jail to source."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n", stderr=""),  # rev-parse HEAD
            MagicMock(returncode=0, stdout="Merge successful", stderr=""),  # merge
        ]
        worktree_path = tmp_path / "worktree"

        jail = Jail(
            worktree_path=worktree_path,
            branch_name="test-branch",
            source_repo=tmp_path,
            _created=True,
        )

        success, message = jail.sync_to_source()
        assert success is True
        assert "test-branch" in message

    @patch("zoyd.jail.subprocess.run")
    def test_jail_sync_to_source_not_created(self, mock_run, tmp_path):
        """Test sync fails gracefully if jail not set up."""
        worktree_path = tmp_path / "worktree"

        jail = Jail(
            worktree_path=worktree_path,
            branch_name="test-branch",
            source_repo=tmp_path,
            _created=False,
        )

        success, message = jail.sync_to_source()
        assert success is False
        assert "not set up" in message
        mock_run.assert_not_called()


class TestCreateJail:
    def test_create_jail_not_git_repo(self, tmp_path):
        """Test that create_jail raises error for non-git directory."""
        with pytest.raises(JailError) as exc_info:
            create_jail(tmp_path)
        assert "Not a git repository" in str(exc_info.value)

    def test_create_jail_with_git_repo(self, tmp_path):
        """Test create_jail works with a git repository."""
        # Create a fake .git directory
        (tmp_path / ".git").mkdir()

        jail = create_jail(tmp_path)
        assert jail.source_repo == tmp_path
        assert jail.branch_name.startswith("zoyd-jail-")
        assert ".zoyd-jails" in str(jail.worktree_path)

    def test_create_jail_custom_worktree_base(self, tmp_path):
        """Test create_jail with custom worktree base directory."""
        (tmp_path / ".git").mkdir()
        custom_base = tmp_path / "custom-jails"

        jail = create_jail(tmp_path, worktree_base=custom_base)
        assert str(custom_base) in str(jail.worktree_path)

    def test_create_jail_custom_branch_prefix(self, tmp_path):
        """Test create_jail with custom branch prefix."""
        (tmp_path / ".git").mkdir()

        jail = create_jail(tmp_path, branch_prefix="my-prefix")
        assert jail.branch_name.startswith("my-prefix-")


class TestGetRepoRoot:
    @patch("zoyd.jail.subprocess.run")
    def test_get_repo_root_success(self, mock_run, tmp_path):
        """Test get_repo_root returns correct path."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=str(tmp_path) + "\n",
            stderr="",
        )

        result = get_repo_root(tmp_path / "subdir")
        assert result == tmp_path

    @patch("zoyd.jail.subprocess.run")
    def test_get_repo_root_not_repo(self, mock_run, tmp_path):
        """Test get_repo_root raises error for non-repo."""
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        with pytest.raises(JailError) as exc_info:
            get_repo_root(tmp_path)
        assert "Not a git repository" in str(exc_info.value)


class TestIsGitWorktree:
    @patch("zoyd.jail.subprocess.run")
    def test_is_git_worktree_true(self, mock_run, tmp_path):
        """Test _is_git_worktree returns True for git directory."""
        mock_run.return_value = MagicMock(returncode=0)

        assert _is_git_worktree(tmp_path) is True

    @patch("zoyd.jail.subprocess.run")
    def test_is_git_worktree_false(self, mock_run, tmp_path):
        """Test _is_git_worktree returns False for non-git directory."""
        mock_run.return_value = MagicMock(returncode=128)

        assert _is_git_worktree(tmp_path) is False
