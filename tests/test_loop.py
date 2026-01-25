"""Tests for loop module."""

import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from zoyd.loop import (
    LoopRunner,
    build_prompt,
    commit_changes,
    generate_commit_message,
    detect_cannot_complete,
    COMMIT_PROMPT_TEMPLATE,
)
from zoyd.cli import cli


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    # Create initial commit
    (tmp_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    return tmp_path


class TestLoopRunner:
    def test_default_delay(self, tmp_path):
        """Test that default delay is 1.0 second."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
        )
        assert runner.delay == 1.0

    def test_backoff_delay_no_failures(self, tmp_path):
        """Test that backoff delay is 0 with no failures."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        runner.consecutive_failures = 0
        assert runner.get_backoff_delay() == 0.0

    def test_backoff_delay_one_failure(self, tmp_path):
        """Test exponential backoff after 1 failure (2^1 = 2s)."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        runner.consecutive_failures = 1
        assert runner.get_backoff_delay() == 2.0

    def test_backoff_delay_two_failures(self, tmp_path):
        """Test exponential backoff after 2 failures (2^2 = 4s)."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        runner.consecutive_failures = 2
        assert runner.get_backoff_delay() == 4.0

    def test_backoff_delay_three_failures(self, tmp_path):
        """Test exponential backoff after 3 failures (2^3 = 8s)."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        runner.consecutive_failures = 3
        assert runner.get_backoff_delay() == 8.0

    def test_custom_delay(self, tmp_path):
        """Test that custom delay can be set."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            delay=5.0,
        )
        assert runner.delay == 5.0

    def test_zero_delay(self, tmp_path):
        """Test that zero delay is allowed."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            delay=0.0,
        )
        assert runner.delay == 0.0

    def test_rate_limit_status_default(self, tmp_path):
        """Test rate limit status with default delay."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert runner.get_rate_limit_status() == "delay=1.0s"

    def test_rate_limit_status_zero_delay(self, tmp_path):
        """Test rate limit status with zero delay."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file, delay=0.0)
        assert runner.get_rate_limit_status() == "delay=0s"

    def test_rate_limit_status_custom_delay(self, tmp_path):
        """Test rate limit status with custom delay."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file, delay=2.5)
        assert runner.get_rate_limit_status() == "delay=2.5s"

    def test_rate_limit_status_with_backoff(self, tmp_path):
        """Test rate limit status includes backoff after failure."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        runner.consecutive_failures = 2
        assert runner.get_rate_limit_status() == "delay=1.0s, backoff=4.0s"

    def test_rate_limit_status_zero_delay_with_backoff(self, tmp_path):
        """Test rate limit status with zero delay but active backoff."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file, delay=0.0)
        runner.consecutive_failures = 1
        assert runner.get_rate_limit_status() == "delay=0s, backoff=2.0s"


class TestBuildPrompt:
    def test_build_prompt_format(self):
        """Test that build_prompt generates correct format."""
        prompt = build_prompt(
            prd_content="# PRD\n- [ ] Task 1",
            progress_content="# Progress",
            iteration=1,
            completed=0,
            total=1,
        )
        assert "Iteration 1" in prompt
        assert "0/1 tasks complete" in prompt
        assert "# PRD" in prompt
        assert "- [ ] Task 1" in prompt

    def test_build_prompt_empty_progress(self):
        """Test that empty progress shows placeholder."""
        prompt = build_prompt(
            prd_content="# PRD",
            progress_content="",
            iteration=1,
            completed=0,
            total=1,
        )
        assert "(No progress yet)" in prompt


class TestAutoCommit:
    def test_auto_commit_default_false(self, tmp_path):
        """Test that auto_commit defaults to False."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert runner.auto_commit is False

    def test_auto_commit_can_be_enabled(self, tmp_path):
        """Test that auto_commit can be enabled."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            auto_commit=True,
        )
        assert runner.auto_commit is True

    def test_commit_prompt_no_coauthor(self):
        """Test that commit prompt explicitly forbids Co-Author lines."""
        assert "Co-Author" in COMMIT_PROMPT_TEMPLATE
        assert "Do NOT include" in COMMIT_PROMPT_TEMPLATE
        assert "Co-Authored-By" in COMMIT_PROMPT_TEMPLATE

    @patch("zoyd.loop.subprocess.run")
    def test_commit_changes_success(self, mock_run):
        """Test successful commit creation."""
        # Mock git add, git diff --cached, and git commit
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # git add
            MagicMock(returncode=1),  # git diff --cached (has changes)
            MagicMock(returncode=0, stdout="[main abc123] Test commit\n", stderr=""),  # git commit
        ]

        success, output = commit_changes("Test commit message")
        assert success is True
        assert "abc123" in output

    @patch("zoyd.loop.subprocess.run")
    def test_commit_changes_no_changes(self, mock_run):
        """Test commit when there are no changes."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # git add
            MagicMock(returncode=0),  # git diff --cached (no changes)
        ]

        success, output = commit_changes("Test commit message")
        assert success is True
        assert "No changes to commit" in output

    @patch("zoyd.loop.subprocess.run")
    def test_commit_changes_add_fails(self, mock_run):
        """Test commit when git add fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Permission denied")

        success, output = commit_changes("Test commit message")
        assert success is False
        assert "git add failed" in output

    @patch("zoyd.loop.invoke_claude")
    def test_generate_commit_message_success(self, mock_invoke):
        """Test successful commit message generation."""
        mock_invoke.return_value = (0, "Add new feature\n\nImplemented the widget component")

        result = generate_commit_message("Made changes to widget", "Add widget")
        assert result == "Add new feature\n\nImplemented the widget component"

    @patch("zoyd.loop.invoke_claude")
    def test_generate_commit_message_strips_coauthor(self, mock_invoke):
        """Test that Co-Author lines are stripped from generated messages."""
        mock_invoke.return_value = (
            0,
            "Add new feature\n\nImplemented the widget component\n\nCo-Authored-By: Someone <email>"
        )

        result = generate_commit_message("Made changes", "Add widget")
        assert result == "Add new feature\n\nImplemented the widget component"
        assert "Co-Author" not in result

    @patch("zoyd.loop.invoke_claude")
    def test_generate_commit_message_failure(self, mock_invoke):
        """Test commit message generation failure."""
        mock_invoke.return_value = (1, "Error")

        result = generate_commit_message("Made changes", "Add widget")
        assert result is None


class TestResume:
    def test_resume_default_false(self, tmp_path):
        """Test that resume defaults to False."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert runner.resume is False

    def test_resume_can_be_enabled(self, tmp_path):
        """Test that resume can be enabled."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Zoyd Progress Log\n")

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            resume=True,
        )
        assert runner.resume is True

    @patch("zoyd.loop.create_jail")
    @patch("zoyd.loop.get_repo_root")
    def test_resume_preserves_progress_file(self, mock_get_repo, mock_create_jail, git_repo):
        """Test that resume mode does not reinitialize progress file."""
        prd_file = git_repo / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1\n- [x] Task 2")
        progress_file = git_repo / "progress.txt"
        existing_content = "# Zoyd Progress Log\n\n## Iteration 1 - 2026-01-25\n\nSome output\n"
        progress_file.write_text(existing_content)

        # Mock jail to avoid actual worktree creation
        mock_get_repo.return_value = git_repo
        mock_jail = MagicMock()
        mock_jail.worktree_path = git_repo  # Use same path for simplicity
        mock_jail.branch_name = "test-branch"
        mock_jail.source_repo = git_repo
        mock_jail.sync_to_source.return_value = (True, "Synced")
        mock_create_jail.return_value = mock_jail

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            resume=True,
            max_iterations=10,
        )
        exit_code = runner.run()
        assert exit_code == 0

        # Progress file should still have original content (not reinitialized)
        assert "## Iteration 1" in progress_file.read_text()

    @patch("zoyd.loop.create_jail")
    @patch("zoyd.loop.get_repo_root")
    def test_no_resume_initializes_progress_file(self, mock_get_repo, mock_create_jail, git_repo):
        """Test that without resume, progress file is initialized if missing."""
        prd_file = git_repo / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")
        progress_file = git_repo / "progress.txt"

        # Mock jail
        mock_get_repo.return_value = git_repo
        mock_jail = MagicMock()
        mock_jail.worktree_path = git_repo
        mock_jail.branch_name = "test-branch"
        mock_jail.source_repo = git_repo
        mock_jail.sync_to_source.return_value = (True, "Synced")
        mock_create_jail.return_value = mock_jail

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            resume=False,
            max_iterations=1,
        )
        exit_code = runner.run()
        assert exit_code == 0

        # Progress file should be created
        assert progress_file.exists()
        assert "# Zoyd Progress Log" in progress_file.read_text()


class TestResumeCLI:
    def test_resume_flag_in_help(self):
        """Test that --resume flag appears in CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--resume" in result.output
        assert "Resume from existing progress file" in result.output

    def test_resume_without_progress_file_fails(self, tmp_path):
        """Test that --resume fails if progress file doesn't exist."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, [
                "run",
                "--prd", str(prd_file),
                "--progress", str(progress_file),
                "--resume",
            ])
            assert result.exit_code == 1
            assert "Cannot resume" in result.output
            assert "does not exist" in result.output

    def test_resume_shows_completed_tasks(self, tmp_path):
        """Test that --resume displays which tasks are already completed."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1\n- [x] Task 2\n- [ ] Task 3")
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Zoyd Progress Log\n\n## Iteration 1 - 2026-01-25\n\nDone\n")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, [
                "run",
                "--prd", str(prd_file),
                "--progress", str(progress_file),
                "--resume",
                "--dry-run",
            ])
            assert "Resuming from iteration 2" in result.output
            assert "Skipping 2 completed task(s)" in result.output
            assert "[x] Task 1" in result.output
            assert "[x] Task 2" in result.output


class TestJailCLI:
    def test_jail_dir_flag_in_help(self):
        """Test that --jail-dir flag appears in CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--jail-dir" in result.output
        assert "Directory for jail worktrees" in result.output

    def test_jail_mode_displayed(self, tmp_path):
        """Test that jail mode is shown in output."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")
        progress_file = tmp_path / "progress.txt"

        # This will fail due to not being a git repo, but we can check output before that
        result = runner.invoke(cli, [
            "run",
            "--prd", str(prd_file),
            "--progress", str(progress_file),
        ])
        assert "Mode: JAIL (worktree + sandbox isolation)" in result.output

    def test_sandbox_in_invoke_claude(self):
        """Test that invoke_claude uses --sandbox flag."""
        from zoyd.loop import invoke_claude

        with patch("zoyd.loop.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")
            invoke_claude("test prompt")

            # Check that --sandbox is in the command
            call_args = mock_run.call_args
            cmd = call_args[1].get("args") or call_args[0][0]
            assert "--sandbox" in cmd


class TestJailDir:
    def test_jail_dir_default_none(self, tmp_path):
        """Test that jail_dir defaults to None."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert runner.jail_dir is None

    def test_jail_dir_can_be_set(self, tmp_path):
        """Test that jail_dir can be set."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"
        jail_dir = tmp_path / "jails"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            jail_dir=jail_dir,
        )
        assert runner.jail_dir == jail_dir


class TestDetectCannotComplete:
    """Tests for detecting when Claude cannot complete a task."""

    def test_detect_cannot_complete_direct(self):
        """Test detection of 'I cannot complete this task'."""
        output = "I cannot complete this task because the file doesn't exist."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "cannot complete this task" in reason.lower()

    def test_detect_cant_complete(self):
        """Test detection of 'I can't complete the task'."""
        output = "I can't complete the task without additional permissions."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "can't complete the task" in reason.lower()

    def test_detect_unable_to_complete(self):
        """Test detection of 'unable to complete'."""
        output = "I am unable to complete this task due to missing dependencies."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "unable to" in reason.lower()

    def test_detect_blocked(self):
        """Test detection of 'I'm blocked on'."""
        output = "I'm blocked on getting access to the database configuration."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "blocked" in reason.lower()

    def test_detect_cannot_proceed(self):
        """Test detection of 'cannot proceed with'."""
        output = "I cannot proceed with the implementation until the API is available."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "cannot proceed" in reason.lower()

    def test_detect_task_impossible(self):
        """Test detection of 'task is impossible'."""
        output = "This task is impossible without root access."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "impossible" in reason.lower()

    def test_detect_need_more_info(self):
        """Test detection of 'need more information'."""
        output = "I need more information about the expected output format."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "need more information" in reason.lower()

    def test_detect_blocker_label(self):
        """Test detection of 'Blocker:'."""
        output = "Blocker: The test server is not responding."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "blocker" in reason.lower()

    def test_detect_beyond_capabilities(self):
        """Test detection of 'beyond my capabilities'."""
        output = "This is beyond my capabilities as it requires hardware access."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "beyond" in reason.lower()

    def test_no_detection_normal_output(self):
        """Test that normal output is not detected as blocked."""
        output = "I completed the task successfully. All tests pass."
        detected, reason = detect_cannot_complete(output)
        assert detected is False
        assert reason is None

    def test_no_detection_partial_match(self):
        """Test that partial matches don't trigger false positives."""
        output = "The task can be completed in the next iteration."
        detected, reason = detect_cannot_complete(output)
        assert detected is False
        assert reason is None

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        output = "I CANNOT COMPLETE THIS TASK due to restrictions."
        detected, reason = detect_cannot_complete(output)
        assert detected is True

    def test_detect_require_clarification(self):
        """Test detection of 'require clarification'."""
        output = "I require clarification on which database to use."
        detected, reason = detect_cannot_complete(output)
        assert detected is True
        assert "require" in reason.lower()
