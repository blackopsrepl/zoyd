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
    format_duration,
    COMMIT_PROMPT_TEMPLATE,
    COMMIT_SYSTEM_PROMPT,
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
            current_task="Task 1",
        )
        assert "Iteration 1" in prompt
        assert "0/1 tasks complete" in prompt
        assert "# PRD" in prompt
        assert "- [ ] Task 1" in prompt
        # Check for new current task section
        assert "## Current Task (COMPLETE THIS ONLY)" in prompt
        assert "Task 1" in prompt
        assert "IMPORTANT: Work on ONLY this task" in prompt
        assert "One task = one commit" in prompt

    def test_build_prompt_empty_progress(self):
        """Test that empty progress shows placeholder."""
        prompt = build_prompt(
            prd_content="# PRD",
            progress_content="",
            iteration=1,
            completed=0,
            total=1,
            current_task="Task 1",
        )
        assert "(No progress yet)" in prompt

    def test_build_prompt_current_task_displayed(self):
        """Test that current task is highlighted in the prompt."""
        prompt = build_prompt(
            prd_content="# PRD\n- [ ] Task A\n- [ ] Task B",
            progress_content="",
            iteration=1,
            completed=0,
            total=2,
            current_task="Task A",
        )
        assert "## Current Task (COMPLETE THIS ONLY)" in prompt
        assert "Task A" in prompt
        assert "Do NOT work on other tasks" in prompt


class TestAutoCommit:
    def test_auto_commit_default_true(self, tmp_path):
        """Test that auto_commit defaults to True."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert runner.auto_commit is True

    def test_auto_commit_can_be_disabled(self, tmp_path):
        """Test that auto_commit can be disabled."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            auto_commit=False,
        )
        assert runner.auto_commit is False

    def test_commit_system_prompt_no_coauthor(self):
        """Test that commit system prompt explicitly forbids signature lines."""
        assert "Co-Authored-By" in COMMIT_SYSTEM_PROMPT
        assert "Signed-off-by" in COMMIT_SYSTEM_PROMPT
        assert "Never" in COMMIT_SYSTEM_PROMPT

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
        mock_invoke.return_value = (0, "Add new feature\n\nImplemented the widget component", None)

        result = generate_commit_message("Made changes to widget", "Add widget")
        assert result == "Add new feature\n\nImplemented the widget component"

    @patch("zoyd.loop.invoke_claude")
    def test_generate_commit_message_strips_coauthor(self, mock_invoke):
        """Test that Co-Author lines are stripped from generated messages."""
        mock_invoke.return_value = (
            0,
            "Add new feature\n\nImplemented the widget component\n\nCo-Authored-By: Someone <email>",
            None,
        )

        result = generate_commit_message("Made changes", "Add widget")
        assert result == "Add new feature\n\nImplemented the widget component"
        assert "Co-Author" not in result

    @patch("zoyd.loop.invoke_claude")
    def test_generate_commit_message_failure(self, mock_invoke):
        """Test commit message generation failure."""
        mock_invoke.return_value = (1, "Error", None)

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

    def test_resume_preserves_progress_file(self, tmp_path):
        """Test that resume mode does not reinitialize progress file."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1\n- [x] Task 2")
        progress_file = tmp_path / "progress.txt"
        existing_content = "# Zoyd Progress Log\n\n## Iteration 1 - 2026-01-25\n\nSome output\n"
        progress_file.write_text(existing_content)

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            resume=True,
            max_iterations=10,
            session_logging=False,
        )
        exit_code = runner.run()
        assert exit_code == 0

        # Progress file should still have original content (not reinitialized)
        assert "## Iteration 1" in progress_file.read_text()

    def test_no_resume_initializes_progress_file(self, tmp_path):
        """Test that without resume, progress file is initialized if missing."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            resume=False,
            max_iterations=1,
            session_logging=False,
        )
        exit_code = runner.run()
        assert exit_code == 0

        # Progress file should be created
        assert progress_file.exists()
        assert "# Zoyd Progress Log" in progress_file.read_text()

    def test_resume_iteration_set_before_live_context(self, tmp_path):
        """Test that iteration is set BEFORE entering live context when resuming.

        This ensures the banner shows the correct iteration from the start,
        not 0 briefly before updating.
        """
        from io import StringIO
        from zoyd.tui.console import create_console

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"
        # Create progress with 5 iterations
        progress_content = "# Zoyd Progress Log\n"
        for i in range(1, 6):
            progress_content += f"\n## Iteration {i} - 2026-01-25\n\nSome output\n"
        progress_file.write_text(progress_content)

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            resume=True,
            max_iterations=6,  # Stop after one iteration
            dry_run=True,
        )

        # The fix ensures iteration is set before the live context is entered.
        # After run(), check that the iteration was correctly calculated from progress.
        runner.run()

        # Check that we started at the correct iteration (6 after 5 completed)
        # The live display should have been set to iteration 6 before entering
        # the context. We can verify this indirectly by checking the final state
        # and ensuring the iteration count logic is correct.
        assert runner.live.iteration == 6, \
            f"Expected final iteration 6, got {runner.live.iteration}"


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
        """Test that --resume works and shows completed tasks count correctly."""
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
                "--no-tui",
                "-n", "1",  # Limit iterations
            ])
            # PlainDisplay shows summary with task progress (2 of 3 complete)
            assert "2/3" in result.output


class TestSandboxMode:
    def test_sandbox_in_invoke_claude(self):
        """Test that invoke_claude enables sandbox via --settings file."""
        import json
        from zoyd.loop import invoke_claude

        settings_file_content = None

        def capture_settings(*args, **kwargs):
            nonlocal settings_file_content
            cmd = kwargs.get("args") or args[0]
            if "--settings" in cmd:
                settings_idx = cmd.index("--settings")
                settings_path = cmd[settings_idx + 1]
                # Read the temp file before it gets cleaned up
                try:
                    with open(settings_path) as f:
                        settings_file_content = f.read()
                except FileNotFoundError:
                    pass
            return MagicMock(returncode=0, stdout="output", stderr="")

        with patch("zoyd.loop.subprocess.run", side_effect=capture_settings):
            invoke_claude("test prompt")

            # Check that sandbox settings file was created with correct content
            assert settings_file_content is not None
            settings = json.loads(settings_file_content)
            assert "sandbox" in settings
            assert settings["sandbox"]["enabled"] is True


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


class TestFailFast:
    """Tests for fail-fast functionality."""

    def test_fail_fast_default_false(self, tmp_path):
        """Test that fail_fast defaults to False."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file, session_logging=False)
        assert runner.fail_fast is False

    def test_fail_fast_can_be_enabled(self, tmp_path):
        """Test that fail_fast can be enabled."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            fail_fast=True,
            session_logging=False,
        )
        assert runner.fail_fast is True

    @patch("zoyd.loop.invoke_claude")
    def test_fail_fast_exits_on_first_failure(self, mock_invoke, tmp_path):
        """Test that fail_fast mode exits immediately on first failure."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1\n- [ ] Task 2")
        progress_file = tmp_path / "progress.txt"

        mock_invoke.return_value = (1, "Error: something went wrong", None)

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            fail_fast=True,
            max_iterations=10,
            session_logging=False,
        )
        exit_code = runner.run()

        assert exit_code == 2
        # Should only call Claude once (fail-fast)
        assert mock_invoke.call_count == 1

    @patch("zoyd.loop.invoke_claude")
    def test_no_fail_fast_retries_on_failure(self, mock_invoke, tmp_path):
        """Test that without fail_fast, failures are retried up to max."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        mock_invoke.return_value = (1, "Error: something went wrong", None)

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            fail_fast=False,
            max_iterations=10,
            delay=0,  # No delay for testing
            session_logging=False,
        )
        # Patch time.sleep to avoid waiting
        with patch("zoyd.loop.time.sleep"):
            exit_code = runner.run()

        assert exit_code == 2
        # Should call Claude 3 times (max_consecutive_failures)
        assert mock_invoke.call_count == 3


class TestFailFastCLI:
    """Tests for fail-fast CLI option."""

    def test_fail_fast_flag_in_help(self):
        """Test that --fail-fast flag appears in CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--fail-fast" in result.output
        assert "Exit immediately on first failure" in result.output


class TestStatusJsonCLI:
    """Tests for status --json CLI option."""

    def test_json_flag_in_help(self):
        """Test that --json flag appears in status CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "JSON format" in result.output

    def test_json_output_incomplete(self, tmp_path):
        """Test JSON output for incomplete PRD."""
        import json

        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1\n- [ ] Task 2\n- [ ] Task 3")
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Zoyd Progress Log\n\n## Iteration 1 - 2026-01-25\n\nDone\n")

        result = runner.invoke(cli, [
            "status",
            "--prd", str(prd_file),
            "--progress", str(progress_file),
            "--json",
        ])
        assert result.exit_code == 1  # IN PROGRESS status

        output = json.loads(result.output)
        assert output["prd"] == str(prd_file)
        assert output["tasks"]["completed"] == 1
        assert output["tasks"]["total"] == 3
        assert len(output["tasks"]["items"]) == 3
        assert output["tasks"]["items"][0]["text"] == "Task 1"
        assert output["tasks"]["items"][0]["complete"] is True
        assert output["tasks"]["items"][1]["text"] == "Task 2"
        assert output["tasks"]["items"][1]["complete"] is False
        assert output["iterations"] == 1
        assert output["status"] == "in_progress"
        assert output["next_task"] == "Task 2"

    def test_json_output_complete(self, tmp_path):
        """Test JSON output for complete PRD."""
        import json

        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1\n- [x] Task 2")
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("# Zoyd Progress Log\n\n## Iteration 1 - 2026-01-25\n\nDone\n\n## Iteration 2 - 2026-01-25\n\nDone\n")

        result = runner.invoke(cli, [
            "status",
            "--prd", str(prd_file),
            "--progress", str(progress_file),
            "--json",
        ])
        assert result.exit_code == 0  # COMPLETE status

        output = json.loads(result.output)
        assert output["tasks"]["completed"] == 2
        assert output["tasks"]["total"] == 2
        assert output["iterations"] == 2
        assert output["status"] == "complete"
        assert output["next_task"] is None

    def test_json_output_no_progress_file(self, tmp_path):
        """Test JSON output when progress file doesn't exist."""
        import json

        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")

        result = runner.invoke(cli, [
            "status",
            "--prd", str(prd_file),
            "--progress", str(tmp_path / "nonexistent.txt"),
            "--json",
        ])
        assert result.exit_code == 1

        output = json.loads(result.output)
        assert output["iterations"] == 0
        assert output["status"] == "in_progress"

    def test_json_output_includes_line_numbers(self, tmp_path):
        """Test that JSON output includes task line numbers."""
        import json

        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n\n## Tasks\n- [ ] Task 1\n- [ ] Task 2")

        result = runner.invoke(cli, [
            "status",
            "--prd", str(prd_file),
            "--progress", str(tmp_path / "progress.txt"),
            "--json",
        ])

        output = json.loads(result.output)
        assert output["tasks"]["items"][0]["line_number"] == 4
        assert output["tasks"]["items"][1]["line_number"] == 5


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_format_duration_seconds_only(self):
        """Test formatting durations under 60 seconds."""
        assert format_duration(0.0) == "0.0s"
        assert format_duration(5.5) == "5.5s"
        assert format_duration(30.123) == "30.1s"
        assert format_duration(59.9) == "59.9s"

    def test_format_duration_with_minutes(self):
        """Test formatting durations of 60 seconds or more."""
        assert format_duration(60.0) == "1m 0.0s"
        assert format_duration(90.5) == "1m 30.5s"
        assert format_duration(125.7) == "2m 5.7s"
        assert format_duration(3661.2) == "61m 1.2s"

    def test_format_duration_exact_minute(self):
        """Test formatting exact minute durations."""
        assert format_duration(120.0) == "2m 0.0s"
        assert format_duration(300.0) == "5m 0.0s"


class TestVerboseModeTiming:
    """Tests for elapsed time and iteration timing in verbose mode."""

    def test_start_time_initialized_on_run(self, tmp_path):
        """Test that start_time is initialized when run() is called."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert runner.start_time is None

        runner.run()
        assert runner.start_time is not None

    @patch("zoyd.loop.invoke_claude")
    @patch("zoyd.loop.time.time")
    def test_verbose_shows_elapsed_time(self, mock_time, mock_invoke, tmp_path, capsys):
        """Test that verbose mode displays elapsed time."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1\n- [x] Task 2")
        progress_file = tmp_path / "progress.txt"

        # Mock time: start at 1000, then 1000 (first time.time call for start),
        # iteration_start at 1005, elapsed check at 1010, iteration end at 1015
        mock_time.side_effect = [1000.0, 1005.0, 1010.0, 1015.0, 1020.0]
        mock_invoke.return_value = (0, "Task completed", None)

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            verbose=True,
            max_iterations=1,
            delay=0,
            auto_commit=False,
            tui_enabled=False,  # Use PlainDisplay for capturable output
        )
        runner.run()

        captured = capsys.readouterr()
        # PlainDisplay outputs verbose log messages to stdout
        assert "Elapsed time:" in captured.out

    @patch("zoyd.loop.invoke_claude")
    @patch("zoyd.loop.time.time")
    def test_verbose_shows_iteration_timing(self, mock_time, mock_invoke, tmp_path, capsys):
        """Test that verbose mode displays iteration timing."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        # Mock time for iteration duration calculation
        mock_time.side_effect = [1000.0, 1005.0, 1010.0, 1015.0, 1020.0, 1025.0]
        mock_invoke.return_value = (0, "Task completed", None)

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            verbose=True,
            max_iterations=1,
            delay=0,
            auto_commit=False,
            tui_enabled=False,  # Use PlainDisplay for capturable output
        )
        runner.run()

        captured = capsys.readouterr()
        # PlainDisplay outputs verbose log messages to stdout
        assert "Iteration 1 completed in" in captured.out

    def test_no_timing_in_non_verbose_mode(self, tmp_path, capsys):
        """Test that timing info is not shown without verbose mode."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            verbose=False,
        )
        runner.run()

        captured = capsys.readouterr()
        assert "Elapsed time:" not in captured.err
        assert "completed in" not in captured.err


class TestVerboseCLI:
    """Tests for verbose CLI option."""

    def test_verbose_flag_in_help(self):
        """Test that -v/--verbose flag appears in CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.output
        assert "-v" in result.output


class TestSummaryStatistics:
    """Tests for summary statistics at end of run."""

    def test_stats_initialized(self, tmp_path):
        """Test that stats are initialized properly."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert runner.stats_iterations == 0
        assert runner.stats_successes == 0
        assert runner.stats_failures == 0
        assert runner.stats_tasks_completed_start == 0
        assert runner.stats_tasks_completed_end == 0
        assert runner.stats_total_tasks == 0

    def test_summary_printed_on_completion(self, tmp_path, capsys):
        """Test that summary is printed when all tasks are complete."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1\n- [x] Task 2")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file, tui_enabled=False)
        exit_code = runner.run()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "=== Summary ===" in captured.out
        assert "Total time:" in captured.out
        assert "Iterations:" in captured.out
        assert "Tasks completed:" in captured.out

    @patch("zoyd.loop.invoke_claude")
    @patch("zoyd.loop.time.time")
    def test_summary_shows_correct_stats(self, mock_time, mock_invoke, tmp_path, capsys):
        """Test that summary shows correct statistics after iterations."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")
        progress_file = tmp_path / "progress.txt"

        # Mock time: start, then iteration timing
        mock_time.side_effect = [1000.0, 1005.0, 1010.0, 1030.0, 1035.0]
        mock_invoke.return_value = (0, "Task completed")

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            delay=0,
            auto_commit=False,
            tui_enabled=False,  # Use PlainDisplay for capturable output
        )
        exit_code = runner.run()

        # Exit code 0 because tasks are already complete
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "=== Summary ===" in captured.out
        assert "Iterations: 0" in captured.out
        assert "Tasks completed: 0 (1/1 total)" in captured.out

    @patch("zoyd.loop.invoke_claude")
    @patch("zoyd.loop.time.time")
    @patch("zoyd.loop.time.sleep")
    def test_summary_on_max_iterations(self, mock_sleep, mock_time, mock_invoke, tmp_path, capsys):
        """Test that summary is printed when max iterations reached."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        mock_time.side_effect = [1000.0] + [1000.0 + i*5 for i in range(20)]
        mock_invoke.return_value = (0, "Working on task", None)

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=2,
            delay=0,
            auto_commit=False,
            tui_enabled=False,  # Use PlainDisplay for capturable output
        )
        exit_code = runner.run()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "=== Summary ===" in captured.out
        assert "Iterations: 2" in captured.out
        assert "Success rate: 100.0% (2/2)" in captured.out

    @patch("zoyd.loop.invoke_claude")
    @patch("zoyd.loop.time.time")
    @patch("zoyd.loop.time.sleep")
    def test_summary_on_failure(self, mock_sleep, mock_time, mock_invoke, tmp_path, capsys):
        """Test that summary is printed on consecutive failures."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        mock_time.side_effect = [1000.0] + [1000.0 + i*5 for i in range(20)]
        mock_invoke.return_value = (1, "Error occurred", None)

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=10,
            delay=0,
            auto_commit=False,
            tui_enabled=False,  # Use PlainDisplay for capturable output
        )
        exit_code = runner.run()

        assert exit_code == 2
        captured = capsys.readouterr()
        assert "=== Summary ===" in captured.out
        assert "Iterations: 3" in captured.out  # max_consecutive_failures
        assert "Success rate: 0.0% (0/3)" in captured.out

    @patch("zoyd.loop.invoke_claude")
    @patch("zoyd.loop.time.time")
    def test_summary_on_fail_fast(self, mock_time, mock_invoke, tmp_path, capsys):
        """Test that summary is printed on fail-fast exit."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        mock_time.side_effect = [1000.0, 1005.0, 1010.0, 1015.0]
        mock_invoke.return_value = (1, "Error occurred", None)

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            fail_fast=True,
            delay=0,
            auto_commit=False,
            tui_enabled=False,  # Use PlainDisplay for capturable output
        )
        exit_code = runner.run()

        assert exit_code == 2
        captured = capsys.readouterr()
        assert "=== Summary ===" in captured.out
        assert "Iterations: 1" in captured.out
        assert "Success rate: 0.0% (0/1)" in captured.out

    def test_print_summary_method(self, tmp_path, capsys):
        """Test that run() prints summary with statistics."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1\n- [ ] Task 2")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            dry_run=True,  # Dry run so we don't actually invoke Claude
            delay=0,
            tui_enabled=False,  # Use PlainDisplay for capturable output
        )
        runner.run()

        captured = capsys.readouterr()
        assert "=== Summary ===" in captured.out
        assert "Iterations:" in captured.out

    def test_print_summary_no_iterations(self, tmp_path, capsys):
        """Test print_summary when all tasks complete (no iterations needed)."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            delay=0,
            tui_enabled=False,  # Use PlainDisplay for capturable output
        )
        runner.run()

        captured = capsys.readouterr()
        assert "Success rate: N/A (no iterations run)" in captured.out


class TestInitCommand:
    """Tests for zoyd init command."""

    def test_init_help(self):
        """Test that init command appears in CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.output

    def test_init_creates_prd_file(self, tmp_path):
        """Test that init creates a PRD.md file with default name."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"

        result = runner.invoke(cli, ["init", "--output", str(prd_file), "Test Project"])
        assert result.exit_code == 0
        assert "Created" in result.output
        assert "Next steps:" in result.output

        assert prd_file.exists()
        content = prd_file.read_text()
        assert "# Project: Test Project" in content
        assert "## Tasks" in content
        assert "- [ ]" in content
        assert "## Notes" in content
        assert "## Success Criteria" in content

    def test_init_custom_output_path(self, tmp_path):
        """Test that init can write to a custom path."""
        runner = CliRunner()
        output_path = tmp_path / "docs" / "tasks.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(cli, ["init", "--output", str(output_path), "My Feature"])
        assert result.exit_code == 0
        assert str(output_path) in result.output

        assert output_path.exists()
        content = output_path.read_text()
        assert "# Project: My Feature" in content

    def test_init_refuses_to_overwrite(self, tmp_path):
        """Test that init refuses to overwrite existing file."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# Existing PRD")

        result = runner.invoke(cli, ["init", "--output", str(prd_file), "New Project"])
        assert result.exit_code == 1
        assert "already exists" in result.output
        assert "--force" in result.output

        # Original content should be unchanged
        assert prd_file.read_text() == "# Existing PRD"

    def test_init_force_overwrites(self, tmp_path):
        """Test that init --force overwrites existing file."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# Existing PRD")

        result = runner.invoke(cli, ["init", "--force", "--output", str(prd_file), "New Project"])
        assert result.exit_code == 0
        assert "Created" in result.output

        content = prd_file.read_text()
        assert "# Project: New Project" in content

    def test_init_default_project_name(self, tmp_path):
        """Test that init uses default project name."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"

        result = runner.invoke(cli, ["init", "--output", str(prd_file)])
        assert result.exit_code == 0

        content = prd_file.read_text()
        assert "# Project: My Project" in content

    def test_init_command_help(self):
        """Test that init --help shows proper documentation."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "-o" in result.output
        assert "--force" in result.output
        assert "-f" in result.output
        assert "starter PRD.md template" in result.output


class TestPrdValidationCLI:
    """Tests for PRD validation in CLI.

    Note: All tests use --no-tui to get capturable output (screen=True uses alternate buffer),
    and -n 1 to limit iterations and keep output manageable.
    """

    def test_valid_prd_no_warnings(self, tmp_path):
        """Valid PRD should show no warnings."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# Project\n- [ ] Valid task\n- [x] Completed task\n")
        progress_file = tmp_path / "progress.txt"

        result = runner.invoke(cli, ["run", "--prd", str(prd_file), "--progress", str(progress_file), "--dry-run", "-n", "1", "--no-tui", "--no-session-log"])
        assert "prd validation" not in result.output.lower()

    def test_empty_task_text_warning(self, tmp_path):
        """Empty task text should show warning."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# Project\n- [ ]\n- [ ] Valid task\n")
        progress_file = tmp_path / "progress.txt"

        result = runner.invoke(cli, ["run", "--prd", str(prd_file), "--progress", str(progress_file), "--dry-run", "-n", "1", "--no-tui", "--no-session-log"])
        assert "prd validation" in result.output.lower()
        assert "Empty task text" in result.output

    def test_malformed_checkbox_warning(self, tmp_path):
        """Malformed checkbox should show warning."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# Project\n-[]\n- [ ] Valid task\n")
        progress_file = tmp_path / "progress.txt"

        result = runner.invoke(cli, ["run", "--prd", str(prd_file), "--progress", str(progress_file), "--dry-run", "-n", "1", "--no-tui", "--no-session-log"])
        assert "prd validation" in result.output.lower()
        assert "Missing space" in result.output

    def test_multiple_warnings(self, tmp_path):
        """Multiple issues should show multiple warnings."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# Project\n- [ ]\n-[]\n- [ ] Valid task\n")
        progress_file = tmp_path / "progress.txt"

        result = runner.invoke(cli, ["run", "--prd", str(prd_file), "--progress", str(progress_file), "--dry-run", "-n", "1", "--no-tui", "--no-session-log"])
        assert "prd validation" in result.output.lower()
        assert "Empty task text" in result.output
        assert "Missing space" in result.output

    def test_warning_shows_line_number(self, tmp_path):
        """Warnings should show line numbers."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# Project\n- [ ]\n")
        progress_file = tmp_path / "progress.txt"

        result = runner.invoke(cli, ["run", "--prd", str(prd_file), "--progress", str(progress_file), "--dry-run", "-n", "1", "--no-tui", "--no-session-log"])
        assert "Line 2" in result.output

    def test_validation_does_not_stop_execution(self, tmp_path):
        """Validation warnings should not stop execution."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# Project\n- [ ]\n- [ ] Valid task\n")
        progress_file = tmp_path / "progress.txt"

        result = runner.invoke(cli, ["run", "--prd", str(prd_file), "--progress", str(progress_file), "--dry-run", "-n", "1", "--no-tui", "--no-session-log"])
        # Should show warning but continue to summary
        assert "prd validation" in result.output.lower()
        assert "Summary" in result.output


class TestMaxCost:
    """Tests for max cost functionality."""

    def test_max_cost_default_none(self, tmp_path):
        """Test that max_cost defaults to None."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert runner.max_cost is None

    def test_max_cost_can_be_set(self, tmp_path):
        """Test that max_cost can be set."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_cost=5.0,
        )
        assert runner.max_cost == 5.0

    def test_stats_total_cost_initialized(self, tmp_path):
        """Test that total cost starts at 0."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert runner.stats_total_cost == 0.0

    @patch("zoyd.loop.invoke_claude")
    @patch("zoyd.loop.time.time")
    def test_max_cost_stops_when_exceeded(self, mock_time, mock_invoke, tmp_path, capsys):
        """Test that run stops when cost limit is exceeded."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1\n- [ ] Task 2")
        progress_file = tmp_path / "progress.txt"

        mock_time.side_effect = [1000.0] + [1000.0 + i*5 for i in range(20)]
        # Return cost_usd that exceeds limit on first iteration
        mock_invoke.return_value = (0, "Task completed", 1.5)  # $1.50 cost

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_cost=1.0,  # $1.00 limit
            max_iterations=10,
            delay=0,
            auto_commit=False,
            tui_enabled=False,  # Use PlainDisplay for capturable output
        )
        exit_code = runner.run()

        # Exit code 4 for cost limit exceeded
        assert exit_code == 4
        captured = capsys.readouterr()
        assert "Cost limit exceeded" in captured.out
        assert "$1.50" in captured.out or "$1.5" in captured.out

    @patch("zoyd.loop.invoke_claude")
    @patch("zoyd.loop.time.time")
    def test_cost_accumulates_across_iterations(self, mock_time, mock_invoke, tmp_path):
        """Test that cost accumulates across iterations."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        mock_time.side_effect = [1000.0] + [1000.0 + i*5 for i in range(20)]
        # Each iteration costs $0.50
        mock_invoke.return_value = (0, "Working on task", 0.5)

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_cost=1.0,  # Will be exceeded after 2 iterations
            max_iterations=5,
            delay=0,
            auto_commit=False,
        )
        exit_code = runner.run()

        # Should stop after cost exceeds limit
        assert exit_code == 4
        # Should have accumulated cost from 2 iterations ($1.00)
        assert runner.stats_total_cost >= 1.0

    def test_summary_shows_cost_when_tracking(self, tmp_path, capsys):
        """Test that summary shows cost limit when max_cost is set."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")  # All complete
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_cost=5.0,
            delay=0,
            tui_enabled=False,  # Use PlainDisplay for capturable output
        )
        runner.run()

        captured = capsys.readouterr()
        # Summary should show cost limit even if no cost was incurred
        assert "Cost limit: $5.00" in captured.out

    def test_summary_hides_cost_when_not_tracking(self, tmp_path, capsys):
        """Test that summary hides cost info when max_cost is not set."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_cost=None,
        )
        runner.start_time = 1000.0
        runner.stats_total_cost = 0.0

        with patch("zoyd.loop.time.time", return_value=1010.0):
            runner.print_summary()

        captured = capsys.readouterr()
        assert "Total cost:" not in captured.out
        assert "Cost limit:" not in captured.out


class TestMaxCostCLI:
    """Tests for max cost CLI option."""

    def test_max_cost_flag_in_help(self):
        """Test that --max-cost flag appears in CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--max-cost" in result.output
        assert "Maximum cost in USD" in result.output

    def test_max_cost_shown_in_output(self, tmp_path):
        """Test that max cost is shown in CLI output."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")

        result = runner.invoke(cli, [
            "run",
            "--prd", str(prd_file),
            "--max-cost", "10.50",
            "--dry-run",
            "--no-tui",  # Use PlainDisplay for capturable output
            "--no-session-log",  # Avoid Redis config from zoyd.toml
        ])
        # Max cost is shown in the summary at the end
        assert "Cost limit: $10.50" in result.output


class TestInvokeClaudeCostTracking:
    """Tests for invoke_claude cost tracking."""

    @patch("zoyd.loop.subprocess.run")
    def test_invoke_claude_returns_cost_from_json(self, mock_run):
        """Test that invoke_claude extracts cost from JSON output."""
        from zoyd.loop import invoke_claude
        import json

        json_output = json.dumps({
            "result": "Task completed successfully",
            "cost_usd": 0.25,
        })
        mock_run.return_value = MagicMock(returncode=0, stdout=json_output, stderr="")

        return_code, output, cost = invoke_claude("test prompt", track_cost=True)

        assert return_code == 0
        assert output == "Task completed successfully"
        assert cost == 0.25

    @patch("zoyd.loop.subprocess.run")
    def test_invoke_claude_no_cost_when_not_tracking(self, mock_run):
        """Test that invoke_claude returns None cost when not tracking."""
        from zoyd.loop import invoke_claude

        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        return_code, output, cost = invoke_claude("test prompt", track_cost=False)

        assert return_code == 0
        assert output == "output"
        assert cost is None

    @patch("zoyd.loop.subprocess.run")
    def test_invoke_claude_uses_json_output_format_when_tracking(self, mock_run):
        """Test that --output-format json is added when tracking cost."""
        from zoyd.loop import invoke_claude
        import json

        json_output = json.dumps({"result": "done", "cost_usd": 0.1})
        mock_run.return_value = MagicMock(returncode=0, stdout=json_output, stderr="")

        invoke_claude("test prompt", track_cost=True)

        call_args = mock_run.call_args
        cmd = call_args[1].get("args") or call_args[0][0]
        assert "--output-format" in cmd
        assert "json" in cmd

    @patch("zoyd.loop.subprocess.run")
    def test_invoke_claude_handles_json_parse_error(self, mock_run):
        """Test that invoke_claude handles invalid JSON gracefully."""
        from zoyd.loop import invoke_claude

        # Return invalid JSON
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")

        return_code, output, cost = invoke_claude("test prompt", track_cost=True)

        assert return_code == 0
        assert output == "not json"
        assert cost is None

    @patch("zoyd.loop.subprocess.run")
    def test_invoke_claude_handles_missing_cost_field(self, mock_run):
        """Test that invoke_claude handles JSON without cost_usd field."""
        from zoyd.loop import invoke_claude
        import json

        json_output = json.dumps({"result": "done"})  # No cost_usd field
        mock_run.return_value = MagicMock(returncode=0, stdout=json_output, stderr="")

        return_code, output, cost = invoke_claude("test prompt", track_cost=True)

        assert return_code == 0
        assert output == "done"
        assert cost is None


class TestLoopRunnerEvents:
    """Tests for LoopRunner event emission."""

    def test_events_attribute_exists(self, tmp_path):
        """Test that LoopRunner has an events attribute."""
        from zoyd.tui.events import EventEmitter

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)
        assert hasattr(runner, "events")
        assert isinstance(runner.events, EventEmitter)

    def test_loop_start_event_emitted(self, tmp_path):
        """Test that LOOP_START event is emitted at start of run."""
        from zoyd.tui.events import EventType

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")  # All complete
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)

        received_events = []
        runner.events.on(EventType.LOOP_START, lambda e: received_events.append(e))

        runner.run()

        assert len(received_events) == 1
        assert received_events[0].type == EventType.LOOP_START
        assert "prd_path" in received_events[0].data
        assert "max_iterations" in received_events[0].data

    def test_loop_end_event_on_complete(self, tmp_path):
        """Test that LOOP_END event is emitted when all tasks complete."""
        from zoyd.tui.events import EventType

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(prd_path=prd_file, progress_path=progress_file)

        received_events = []
        runner.events.on(EventType.LOOP_END, lambda e: received_events.append(e))

        runner.run()

        assert len(received_events) == 1
        assert received_events[0].data.get("status") == "complete"
        assert received_events[0].data.get("exit_code") == 0

    @patch("zoyd.loop.invoke_claude")
    def test_iteration_start_event_emitted(self, mock_invoke, tmp_path):
        """Test that ITERATION_START event is emitted at start of each iteration."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "done", None)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            auto_commit=False,
        )

        received_events = []
        runner.events.on(EventType.ITERATION_START, lambda e: received_events.append(e))

        runner.run()

        assert len(received_events) == 1
        assert received_events[0].data.get("iteration") == 1
        assert "completed" in received_events[0].data
        assert "total" in received_events[0].data

    @patch("zoyd.loop.invoke_claude")
    def test_iteration_end_event_emitted(self, mock_invoke, tmp_path):
        """Test that ITERATION_END event is emitted at end of each iteration."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "done", None)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            auto_commit=False,
        )

        received_events = []
        runner.events.on(EventType.ITERATION_END, lambda e: received_events.append(e))

        runner.run()

        assert len(received_events) == 1
        assert received_events[0].data.get("iteration") == 1
        assert "duration" in received_events[0].data
        assert "success" in received_events[0].data

    @patch("zoyd.loop.invoke_claude")
    def test_claude_invoke_event_emitted(self, mock_invoke, tmp_path):
        """Test that CLAUDE_INVOKE event is emitted before invoking Claude."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "done", None)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            auto_commit=False,
        )

        received_events = []
        runner.events.on(EventType.CLAUDE_INVOKE, lambda e: received_events.append(e))

        runner.run()

        assert len(received_events) == 1
        assert received_events[0].data.get("iteration") == 1
        assert "task" in received_events[0].data

    @patch("zoyd.loop.invoke_claude")
    def test_claude_response_event_on_success(self, mock_invoke, tmp_path):
        """Test that CLAUDE_RESPONSE event is emitted on successful invocation."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "done", 0.05)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            auto_commit=False,
            max_cost=1.0,  # Enable cost tracking
        )

        received_events = []
        runner.events.on(EventType.CLAUDE_RESPONSE, lambda e: received_events.append(e))

        runner.run()

        assert len(received_events) == 1
        assert received_events[0].data.get("return_code") == 0
        assert received_events[0].data.get("cost_usd") == 0.05

    @patch("zoyd.loop.invoke_claude")
    def test_claude_error_event_on_failure(self, mock_invoke, tmp_path):
        """Test that CLAUDE_ERROR event is emitted on failed invocation."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (1, "Error occurred", None)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            fail_fast=True,
            auto_commit=False,
        )

        received_events = []
        runner.events.on(EventType.CLAUDE_ERROR, lambda e: received_events.append(e))

        runner.run()

        assert len(received_events) == 1
        assert received_events[0].data.get("return_code") == 1
        assert "output" in received_events[0].data

    @patch("zoyd.loop.invoke_claude")
    def test_task_blocked_event_emitted(self, mock_invoke, tmp_path):
        """Test that TASK_BLOCKED event is emitted when Claude can't complete task."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "I cannot complete this task because of X", None)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            auto_commit=False,
        )

        received_events = []
        runner.events.on(EventType.TASK_BLOCKED, lambda e: received_events.append(e))

        runner.run()

        assert len(received_events) == 1
        assert "task" in received_events[0].data
        assert "reason" in received_events[0].data

    @patch("zoyd.loop.invoke_claude")
    def test_cost_update_event_emitted(self, mock_invoke, tmp_path):
        """Test that COST_UPDATE event is emitted when cost is tracked."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "done", 0.05)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            max_cost=1.0,
            auto_commit=False,
        )

        received_events = []
        runner.events.on(EventType.COST_UPDATE, lambda e: received_events.append(e))

        runner.run()

        assert len(received_events) == 1
        assert received_events[0].data.get("iteration_cost") == 0.05
        assert received_events[0].data.get("total_cost") == 0.05
        assert received_events[0].data.get("max_cost") == 1.0

    @patch("zoyd.loop.invoke_claude")
    def test_cost_limit_exceeded_event_emitted(self, mock_invoke, tmp_path):
        """Test that COST_LIMIT_EXCEEDED event is emitted when cost exceeds max."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "done", 0.10)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=10,
            max_cost=0.05,  # Lower than iteration cost
            auto_commit=False,
        )

        received_events = []
        runner.events.on(EventType.COST_LIMIT_EXCEEDED, lambda e: received_events.append(e))

        exit_code = runner.run()

        assert exit_code == 4
        assert len(received_events) == 1
        assert received_events[0].data.get("total_cost") == 0.10
        assert received_events[0].data.get("max_cost") == 0.05

    @patch("zoyd.loop.commit_changes")
    @patch("zoyd.loop.generate_commit_message")
    @patch("zoyd.loop.invoke_claude")
    def test_commit_events_emitted(self, mock_invoke, mock_gen_msg, mock_commit, tmp_path):
        """Test that commit events are emitted during auto-commit."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "done", None)
        mock_gen_msg.return_value = "feat: add feature"
        mock_commit.return_value = (True, "commit success")

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            auto_commit=True,
        )

        start_events = []
        success_events = []
        runner.events.on(EventType.COMMIT_START, lambda e: start_events.append(e))
        runner.events.on(EventType.COMMIT_SUCCESS, lambda e: success_events.append(e))

        runner.run()

        assert len(start_events) == 1
        assert start_events[0].data.get("message") == "feat: add feature"
        assert len(success_events) == 1

    @patch("zoyd.loop.commit_changes")
    @patch("zoyd.loop.generate_commit_message")
    @patch("zoyd.loop.invoke_claude")
    def test_commit_failed_event_emitted(self, mock_invoke, mock_gen_msg, mock_commit, tmp_path):
        """Test that COMMIT_FAILED event is emitted when commit fails."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "done", None)
        mock_gen_msg.return_value = "feat: add feature"
        mock_commit.return_value = (False, "commit failed")

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            auto_commit=True,
        )

        failed_events = []
        runner.events.on(EventType.COMMIT_FAILED, lambda e: failed_events.append(e))

        runner.run()

        assert len(failed_events) == 1
        assert "error" in failed_events[0].data

    @patch("zoyd.loop.commit_changes")
    @patch("zoyd.loop.generate_commit_message")
    @patch("zoyd.loop.invoke_claude")
    def test_task_complete_event_on_successful_commit(self, mock_invoke, mock_gen_msg, mock_commit, tmp_path):
        """Test that TASK_COMPLETE event is emitted on successful commit."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "done", None)
        mock_gen_msg.return_value = "feat: add feature"
        mock_commit.return_value = (True, "commit success")

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=1,
            auto_commit=True,
        )

        complete_events = []
        runner.events.on(EventType.TASK_COMPLETE, lambda e: complete_events.append(e))

        runner.run()

        assert len(complete_events) == 1
        assert complete_events[0].data.get("task") == "Task 1"

    def test_loop_end_event_on_max_iterations(self, tmp_path):
        """Test LOOP_END event with max_iterations status."""
        from zoyd.tui.events import EventType

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=0,  # Immediate max
            auto_commit=False,
        )

        received_events = []
        runner.events.on(EventType.LOOP_END, lambda e: received_events.append(e))

        exit_code = runner.run()

        assert exit_code == 1
        assert len(received_events) == 1
        assert received_events[0].data.get("status") == "max_iterations"
        assert received_events[0].data.get("exit_code") == 1

    @patch("zoyd.loop.invoke_claude")
    def test_loop_end_event_on_fail_fast(self, mock_invoke, tmp_path):
        """Test LOOP_END event with fail_fast status."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (1, "error", None)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=10,
            fail_fast=True,
            auto_commit=False,
        )

        received_events = []
        runner.events.on(EventType.LOOP_END, lambda e: received_events.append(e))

        exit_code = runner.run()

        assert exit_code == 2
        assert len(received_events) == 1
        assert received_events[0].data.get("status") == "fail_fast"

    @patch("zoyd.loop.invoke_claude")
    def test_loop_end_event_on_max_failures(self, mock_invoke, tmp_path):
        """Test LOOP_END event with max_failures status."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (1, "error", None)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=10,
            auto_commit=False,
        )

        received_events = []
        runner.events.on(EventType.LOOP_END, lambda e: received_events.append(e))

        exit_code = runner.run()

        assert exit_code == 2
        assert len(received_events) == 1
        assert received_events[0].data.get("status") == "max_failures"

    @patch("zoyd.loop.invoke_claude")
    def test_multiple_iterations_emit_multiple_events(self, mock_invoke, tmp_path):
        """Test that multiple iterations emit events for each iteration."""
        from zoyd.tui.events import EventType

        mock_invoke.return_value = (0, "done", None)

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            max_iterations=3,
            auto_commit=False,
            delay=0,
        )

        start_events = []
        end_events = []
        runner.events.on(EventType.ITERATION_START, lambda e: start_events.append(e))
        runner.events.on(EventType.ITERATION_END, lambda e: end_events.append(e))

        runner.run()

        assert len(start_events) == 3
        assert len(end_events) == 3
        # Verify iteration numbers
        assert [e.data.get("iteration") for e in start_events] == [1, 2, 3]
        assert [e.data.get("iteration") for e in end_events] == [1, 2, 3]


class TestNoTui:
    """Tests for TUI disabled mode."""

    def test_tui_enabled_default_true(self, tmp_path):
        """Test that TUI is enabled by default."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
        )
        assert runner.tui_enabled is True

    def test_tui_can_be_disabled(self, tmp_path):
        """Test that TUI can be disabled."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            tui_enabled=False,
        )
        assert runner.tui_enabled is False

    def test_live_display_used_when_tui_enabled(self, tmp_path):
        """Test that LiveDisplay is used when TUI is enabled."""
        from zoyd.tui.live import LiveDisplay

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            tui_enabled=True,
        )
        assert isinstance(runner.live, LiveDisplay)

    def test_plain_display_used_when_tui_disabled(self, tmp_path):
        """Test that PlainDisplay is used when TUI is disabled."""
        from zoyd.tui.live import PlainDisplay

        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        runner = LoopRunner(
            prd_path=prd_file,
            progress_path=progress_file,
            tui_enabled=False,
        )
        assert isinstance(runner.live, PlainDisplay)


class TestNoTuiCLI:
    """Tests for --no-tui CLI option."""

    def test_no_tui_flag_in_help(self):
        """Test that --no-tui flag appears in CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--no-tui" in result.output
        assert "Disable Rich TUI" in result.output or "plain text output" in result.output

    def test_no_tui_shows_plain_output(self, tmp_path):
        """Test that --no-tui shows plain text output."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")

        result = runner.invoke(cli, [
            "run",
            "--prd", str(prd_file),
            "--no-tui",
            "--dry-run",
            "--no-session-log",  # Avoid Redis config from zoyd.toml
        ])
        # Plain output shows "Zoyd - Autonomous Loop" instead of ASCII art
        assert "Zoyd - Autonomous Loop" in result.output
        assert "PRD:" in result.output

    def test_no_tui_shows_plain_iteration(self, tmp_path):
        """Test that --no-tui shows plain iteration messages."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [x] Task 1")
        progress_file = tmp_path / "progress.txt"

        result = runner.invoke(cli, [
            "run",
            "--prd", str(prd_file),
            "--progress", str(progress_file),
            "--no-tui",
            "-n", "1",
            "--no-session-log",  # Avoid Redis config from zoyd.toml
        ])
        # Should show iteration header in plain format or "All tasks complete" for completed PRD
        assert "=== Iteration" in result.output or "[SUCCESS] All tasks complete" in result.output

    def test_no_tui_with_dry_run(self, tmp_path):
        """Test that --no-tui works with --dry-run."""
        runner = CliRunner()
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n- [ ] Task 1")
        progress_file = tmp_path / "progress.txt"

        result = runner.invoke(cli, [
            "run",
            "--prd", str(prd_file),
            "--progress", str(progress_file),
            "--no-tui",
            "--dry-run",
            "-n", "1",
            "--no-session-log",  # Avoid Redis config from zoyd.toml
        ])
        # Exit code 1 means max iterations reached (which is expected for dry run)
        assert result.exit_code in [0, 1]
        assert "DRY RUN" in result.output or "Would send prompt" in result.output


class TestPlainDisplay:
    """Tests for PlainDisplay class."""

    def test_plain_display_log_method(self, capsys):
        """Test that PlainDisplay.log prints to stdout."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        display.log("Test message")

        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_plain_display_log_strips_markup(self, capsys):
        """Test that PlainDisplay.log strips Rich markup tags."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        display.log("[bold]Bold text[/bold]")

        captured = capsys.readouterr()
        assert "Bold text" in captured.out
        assert "[bold]" not in captured.out

    def test_plain_display_log_success(self, capsys):
        """Test that PlainDisplay.log_success prints with [SUCCESS] prefix."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        display.log_success("Task completed")

        captured = capsys.readouterr()
        assert "[SUCCESS]" in captured.out
        assert "Task completed" in captured.out

    def test_plain_display_log_error(self, capsys):
        """Test that PlainDisplay.log_error prints with [ERROR] prefix."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        display.log_error("Something failed")

        captured = capsys.readouterr()
        assert "[ERROR]" in captured.out
        assert "Something failed" in captured.out

    def test_plain_display_log_warning(self, capsys):
        """Test that PlainDisplay.log_warning prints with [WARNING] prefix."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        display.log_warning("Be careful")

        captured = capsys.readouterr()
        assert "[WARNING]" in captured.out
        assert "Be careful" in captured.out

    def test_plain_display_iteration_property(self):
        """Test that PlainDisplay.iteration property works."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        assert display.iteration == 0
        display.iteration = 5
        assert display.iteration == 5

    def test_plain_display_cost_property(self):
        """Test that PlainDisplay.cost property works."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        assert display.cost == 0.0
        display.cost = 1.25
        assert display.cost == 1.25

    def test_plain_display_set_task(self):
        """Test that PlainDisplay.set_task works."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        display.set_task("Task 1")
        assert display._task_text == "Task 1"
        display.set_task(None)
        assert display._task_text is None

    def test_plain_display_set_completion_initial(self):
        """Test that PlainDisplay._completed and _total start at zero."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        assert display._completed == 0
        assert display._total == 0

    def test_plain_display_set_completion(self):
        """Test that PlainDisplay.set_completion stores state."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        display.set_completion(5, 10)
        assert display._completed == 5
        assert display._total == 10

    def test_plain_display_set_completion_noop_output(self, capsys):
        """Test that PlainDisplay.set_completion produces no output."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        display.set_completion(3, 7)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_plain_display_context_manager(self, capsys):
        """Test that PlainDisplay context manager prints startup banner."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(
            prd_path="test.md",
            progress_path="progress.txt",
            max_iterations=10,
            model="opus",
            max_cost=5.0,
        )

        with display:
            pass

        captured = capsys.readouterr()
        assert "Zoyd - Autonomous Loop" in captured.out
        assert "PRD: test.md" in captured.out
        assert "Progress: progress.txt" in captured.out
        assert "Max iterations: 10" in captured.out
        assert "Model: opus" in captured.out
        assert "Cost limit: $5.00" in captured.out

    def test_plain_display_spinner_noop(self):
        """Test that spinner methods are no-ops in PlainDisplay."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        # These should not raise any errors
        display.start_spinner("Loading...")
        display.stop_spinner()

    def test_plain_display_log_iteration_start(self, capsys):
        """Test that PlainDisplay.log_iteration_start formats correctly."""
        from zoyd.tui.live import PlainDisplay

        display = PlainDisplay(prd_path="test.md", max_iterations=10)
        display.log_iteration_start(3, 5, 10)

        captured = capsys.readouterr()
        assert "=== Iteration 3/10 (5/10 tasks) ===" in captured.out
        assert display.iteration == 3


class TestCreatePlainDisplay:
    """Tests for create_plain_display factory function."""

    def test_create_plain_display_defaults(self):
        """Test create_plain_display with default values."""
        from zoyd.tui.live import create_plain_display

        display = create_plain_display()
        assert display.prd_path == ""
        assert display.progress_path == ""
        assert display.max_iterations == 10
        assert display.model is None
        assert display.max_cost is None

    def test_create_plain_display_with_options(self):
        """Test create_plain_display with custom options."""
        from zoyd.tui.live import create_plain_display

        display = create_plain_display(
            prd_path="my_prd.md",
            progress_path="my_progress.txt",
            max_iterations=20,
            model="sonnet",
            max_cost=10.0,
        )
        assert display.prd_path == "my_prd.md"
        assert display.progress_path == "my_progress.txt"
        assert display.max_iterations == 20
        assert display.model == "sonnet"
        assert display.max_cost == 10.0


class TestTUIConfigOptionsLoopRunner:
    """Tests for TUI config options (tui_refresh_rate, tui_compact) in LoopRunner."""

    def test_tui_refresh_rate_default(self, tmp_path):
        """Test that tui_refresh_rate has a default of 4.0."""
        prd = tmp_path / "PRD.md"
        prd.write_text("# Tasks\n- [ ] Test task")
        runner = LoopRunner(prd_path=prd, progress_path=tmp_path / "progress.txt")
        assert runner.tui_refresh_rate == 4.0

    def test_tui_refresh_rate_can_be_set(self, tmp_path):
        """Test that tui_refresh_rate can be customized."""
        prd = tmp_path / "PRD.md"
        prd.write_text("# Tasks\n- [ ] Test task")
        runner = LoopRunner(
            prd_path=prd, progress_path=tmp_path / "progress.txt", tui_refresh_rate=10.0
        )
        assert runner.tui_refresh_rate == 10.0

    def test_tui_compact_default(self, tmp_path):
        """Test that tui_compact has a default of False."""
        prd = tmp_path / "PRD.md"
        prd.write_text("# Tasks\n- [ ] Test task")
        runner = LoopRunner(prd_path=prd, progress_path=tmp_path / "progress.txt")
        assert runner.tui_compact is False

    def test_tui_compact_can_be_set(self, tmp_path):
        """Test that tui_compact can be enabled."""
        prd = tmp_path / "PRD.md"
        prd.write_text("# Tasks\n- [ ] Test task")
        runner = LoopRunner(
            prd_path=prd, progress_path=tmp_path / "progress.txt", tui_compact=True
        )
        assert runner.tui_compact is True

    def test_tui_refresh_rate_passed_to_live_display(self, tmp_path):
        """Test that tui_refresh_rate is passed to LiveDisplay."""
        rich = pytest.importorskip("rich")
        from zoyd.tui.live import LiveDisplay

        prd = tmp_path / "PRD.md"
        prd.write_text("# Tasks\n- [ ] Test task")
        runner = LoopRunner(
            prd_path=prd,
            progress_path=tmp_path / "progress.txt",
            tui_enabled=True,
            tui_refresh_rate=12.0,
        )
        assert isinstance(runner.live, LiveDisplay)
        # LiveDisplay stores refresh_per_second
        assert runner.live.refresh_per_second == 12
