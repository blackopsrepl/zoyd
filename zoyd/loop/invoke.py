"""Claude invocation utilities."""

from __future__ import annotations

import json as json_module
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple


def invoke_claude(
    prompt: str,
    model: str | None = None,
    cwd: Path | None = None,
    track_cost: bool = False,
    append_system_prompt: str | None = None,
    sandbox: bool = True,
) -> tuple[int, str, float | None]:
    """Invoke Claude Code with the given prompt.

    Args:
        prompt: The prompt to send to Claude.
        model: Optional model to use (e.g., "opus", "sonnet").
        cwd: Working directory for Claude.
        track_cost: If True, use JSON output format to track cost.
        append_system_prompt: Optional text appended to the system prompt.
        sandbox: If True (default), enable filesystem/network sandbox isolation.
            If False, disable sandbox mode (e.g. for commit message generation).

    Returns:
        Tuple of (return_code, output, cost_usd). cost_usd is None if not tracking or unavailable.
    """
    # Configure sandbox settings for filesystem/network isolation
    # Claude expects --settings to be a file path, not inline JSON
    if sandbox:
        sandbox_settings = {"sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True}}
        # Create a temp file for settings
        settings_fd, settings_path = tempfile.mkstemp(suffix=".json", prefix="zoyd_settings_")
        with open(settings_fd, "w") as f:
            json_module.dump(sandbox_settings, f)
        cmd = ["claude", "--print", "--permission-mode", "acceptEdits",
               "--disallowedTools", "Bash(git *)", "--settings", settings_path]
    else:
        # Rabid mode: bypass all permissions (no sandbox)
        settings_path = None
        cmd = ["claude", "--print", "--dangerously-skip-permissions",
               "--disallowedTools", "Bash(git *)"]

    try:

        if model:
            cmd.extend(["--model", model])

        if track_cost:
            cmd.extend(["--output-format", "json"])

        if append_system_prompt:
            cmd.extend(["--append-system-prompt", append_system_prompt])

        # Pass prompt via stdin to avoid OS ARG_MAX limit (E2BIG) on large prompts
        result = subprocess.run(
            cmd,
            input=prompt,
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
        # Clean up temp file (only exists when sandbox=True)
        if settings_path:
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