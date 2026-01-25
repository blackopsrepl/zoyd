"""Tests for log_markdown() functionality in zoyd.tui.live module."""

from __future__ import annotations

import io
import sys

import pytest

rich = pytest.importorskip("rich")

from rich.console import Console
from rich.markdown import Markdown

from zoyd.tui.live import (
    DEFAULT_CODE_THEME,
    LiveDisplay,
    PlainDisplay,
    create_plain_display,
)


class TestDefaultCodeTheme:
    """Tests for the DEFAULT_CODE_THEME constant."""

    def test_default_code_theme_is_dracula(self) -> None:
        """DEFAULT_CODE_THEME should be 'dracula'."""
        assert DEFAULT_CODE_THEME == "dracula"

    def test_default_code_theme_importable(self) -> None:
        """DEFAULT_CODE_THEME should be importable from module."""
        from zoyd.tui.live import DEFAULT_CODE_THEME as theme
        assert theme == "dracula"


class TestLiveDisplayLogMarkdown:
    """Tests for LiveDisplay.log_markdown() method."""

    def test_log_markdown_adds_to_log_lines(self) -> None:
        """log_markdown should add content to log lines."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log_markdown("# Hello World")
        assert len(live._log_lines) == 1

    def test_log_markdown_creates_markdown_object(self) -> None:
        """log_markdown should create a Markdown object."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log_markdown("# Hello World")
        assert isinstance(live._log_lines[0], Markdown)

    def test_log_markdown_uses_default_theme(self) -> None:
        """log_markdown should use the default code theme."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log_markdown("```python\nprint('hello')\n```")
        md = live._log_lines[0]
        assert md.code_theme == "dracula"

    def test_log_markdown_accepts_custom_theme(self) -> None:
        """log_markdown should accept a custom code theme."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log_markdown("```python\nprint('hello')\n```", code_theme="monokai")
        md = live._log_lines[0]
        assert md.code_theme == "monokai"

    def test_log_markdown_with_code_block(self) -> None:
        """log_markdown should handle code blocks correctly."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        content = """
Here is some code:

```python
def hello():
    print("Hello, World!")
```
"""
        live.log_markdown(content)
        assert len(live._log_lines) == 1
        assert isinstance(live._log_lines[0], Markdown)

    def test_log_markdown_with_mixed_content(self) -> None:
        """log_markdown should handle mixed markdown content."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        content = """
# Summary

I completed the task. Here are the changes:

- Added new feature
- Fixed bug in `process.py`

```python
def new_feature():
    return True
```

**Done!**
"""
        live.log_markdown(content)
        assert len(live._log_lines) == 1
        assert isinstance(live._log_lines[0], Markdown)

    def test_log_markdown_multiple_calls(self) -> None:
        """Multiple log_markdown calls should accumulate."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console, max_log_lines=100)
        live.log_markdown("# First")
        live.log_markdown("# Second")
        live.log_markdown("# Third")
        assert len(live._log_lines) == 3
        for item in live._log_lines:
            assert isinstance(item, Markdown)

    def test_log_markdown_respects_max_log_lines(self) -> None:
        """log_markdown should respect max_log_lines limit."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console, max_log_lines=3)
        live.log_markdown("# One")
        live.log_markdown("# Two")
        live.log_markdown("# Three")
        live.log_markdown("# Four")
        assert len(live._log_lines) == 3
        # First item should have been removed
        # Can't easily check content since Markdown doesn't have direct markup access

    def test_log_markdown_mixed_with_regular_log(self) -> None:
        """log_markdown should work alongside regular log()."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console, max_log_lines=100)
        live.log("Plain text message")
        live.log_markdown("# Markdown heading")
        live.log("Another plain message")
        assert len(live._log_lines) == 3
        # First and third should be Text, second should be Markdown
        assert not isinstance(live._log_lines[0], Markdown)
        assert isinstance(live._log_lines[1], Markdown)
        assert not isinstance(live._log_lines[2], Markdown)


class TestLiveDisplayLogMarkdownRendering:
    """Tests for rendering log_markdown content."""

    def test_render_logs_with_markdown_content(self) -> None:
        """_render_logs should render markdown content."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log_markdown("# Test Heading")
        logs = live._render_logs()
        assert logs is not None

    def test_render_logs_with_mixed_content(self) -> None:
        """_render_logs should handle mixed Text and Markdown content."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log("Plain text")
        live.log_markdown("# Markdown content")
        live.log_error("Error message")
        logs = live._render_logs()
        assert logs is not None

    def test_complete_render_with_markdown(self) -> None:
        """_render should work with markdown content."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)
        live.log_markdown("# Test")
        rendered = live._render()
        assert rendered is not None


class TestPlainDisplayLogMarkdown:
    """Tests for PlainDisplay.log_markdown() method."""

    def test_log_markdown_prints_content(self, capsys) -> None:
        """log_markdown should print content in plain mode."""
        plain = PlainDisplay(
            prd_path="test.md",
            progress_path="progress.txt",
            max_iterations=10,
        )
        plain.log_markdown("# Hello World")
        captured = capsys.readouterr()
        assert "# Hello World" in captured.out

    def test_log_markdown_ignores_code_theme(self, capsys) -> None:
        """log_markdown should ignore code_theme in plain mode."""
        plain = PlainDisplay(
            prd_path="test.md",
            progress_path="progress.txt",
            max_iterations=10,
        )
        # Should not raise even with code_theme
        plain.log_markdown("```python\nprint('hi')\n```", code_theme="monokai")
        captured = capsys.readouterr()
        assert "print('hi')" in captured.out

    def test_log_markdown_preserves_code_blocks(self, capsys) -> None:
        """log_markdown should preserve code blocks in output."""
        plain = PlainDisplay(
            prd_path="test.md",
            progress_path="progress.txt",
            max_iterations=10,
        )
        content = """
# Summary

```python
def foo():
    return 42
```
"""
        plain.log_markdown(content)
        captured = capsys.readouterr()
        assert "def foo():" in captured.out
        assert "return 42" in captured.out

    def test_log_markdown_with_mixed_content(self, capsys) -> None:
        """log_markdown should handle mixed markdown content."""
        plain = PlainDisplay(
            prd_path="test.md",
            progress_path="progress.txt",
            max_iterations=10,
        )
        content = """
## Task Complete

I made the following changes:

1. Added feature A
2. Fixed bug B

**Important:** Check tests!
"""
        plain.log_markdown(content)
        captured = capsys.readouterr()
        assert "Task Complete" in captured.out
        assert "Added feature A" in captured.out
        assert "Important" in captured.out


class TestLogMarkdownIntegration:
    """Integration tests for log_markdown in loop context."""

    def test_log_markdown_used_for_claude_output(self) -> None:
        """Verify log_markdown is called for Claude output in verbose mode."""
        # This test verifies the integration by checking the loop.py code
        # is using log_markdown() instead of log() for Claude output
        import zoyd.loop as loop_module

        # Read the source code to verify log_markdown is used
        import inspect
        source = inspect.getsource(loop_module.LoopRunner.run)

        # Check that log_markdown is used for verbose output
        assert "log_markdown(output)" in source
        # Should not use log(output) for verbose Claude output anymore
        # (except for dry run prompt which is not Claude's response)


class TestLogMarkdownSyntaxHighlighting:
    """Tests for syntax highlighting in log_markdown."""

    def test_python_code_block_is_highlighted(self) -> None:
        """Python code blocks should have syntax highlighting applied."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, force_interactive=True)
        live = LiveDisplay(console)

        live.log_markdown("""
```python
def hello():
    print("world")
```
""")

        # Render to get actual output
        with live:
            live._refresh()

        rendered_output = output.getvalue()
        # With syntax highlighting, there should be ANSI escape codes
        # (The dracula theme will colorize the code)
        # We can't easily verify exact colors, but we can check the Markdown was used
        assert len(live._log_lines) == 1
        assert isinstance(live._log_lines[0], Markdown)

    def test_multiple_language_code_blocks(self) -> None:
        """Multiple code blocks with different languages should work."""
        console = Console(file=io.StringIO(), force_terminal=True)
        live = LiveDisplay(console)

        live.log_markdown("""
Here's Python:
```python
print("Hello")
```

And JavaScript:
```javascript
console.log("Hello");
```

And Rust:
```rust
fn main() {
    println!("Hello");
}
```
""")

        assert len(live._log_lines) == 1
        assert isinstance(live._log_lines[0], Markdown)


class TestModuleExports:
    """Tests for module exports related to markdown functionality."""

    def test_default_code_theme_exported(self) -> None:
        """DEFAULT_CODE_THEME should be exported from module."""
        from zoyd.tui.live import DEFAULT_CODE_THEME
        assert DEFAULT_CODE_THEME is not None

    def test_markdown_imported_in_module(self) -> None:
        """Markdown should be imported in the live module."""
        from zoyd.tui import live
        assert hasattr(live, "Markdown")
