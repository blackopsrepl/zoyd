"""Tests for TUI console module."""

import io

import pytest

# Skip all tests if rich is not installed
rich = pytest.importorskip("rich")


class TestGetConsole:
    def test_returns_console_instance(self):
        from rich.console import Console

        from zoyd.tui.console import get_console, reset_console

        reset_console()  # Ensure fresh state
        console = get_console()
        assert isinstance(console, Console)

    def test_returns_singleton(self):
        from zoyd.tui.console import get_console, reset_console

        reset_console()
        console1 = get_console()
        console2 = get_console()
        assert console1 is console2

    def test_reset_creates_new_instance(self):
        from zoyd.tui.console import get_console, reset_console

        reset_console()
        console1 = get_console()
        console2 = get_console(_reset=True)
        assert console1 is not console2

    def test_console_has_zoyd_theme(self):
        from zoyd.tui.console import get_console, reset_console
        from zoyd.tui.theme import ZOYD_THEME

        reset_console()
        console = get_console()
        # Check that some zoyd-specific styles are present
        assert "zoyd.banner" in console._theme.styles

    def test_custom_file_output(self):
        from zoyd.tui.console import get_console, reset_console

        reset_console()
        output = io.StringIO()
        console = get_console(file=output, force_terminal=True, _reset=True)
        console.print("test output")
        assert "test output" in output.getvalue()

    def test_custom_width(self):
        from zoyd.tui.console import get_console, reset_console

        reset_console()
        console = get_console(width=100, _reset=True)
        assert console.width == 100

    def test_emoji_disabled(self):
        from zoyd.tui.console import get_console, reset_console

        reset_console()
        console = get_console()
        # Rich Console has emoji attribute
        assert console._emoji is False


class TestResetConsole:
    def test_reset_clears_singleton(self):
        from zoyd.tui.console import _console, get_console, reset_console

        # First get a console
        get_console()

        # Then reset
        reset_console()

        # Import fresh to check module-level variable
        import zoyd.tui.console as console_module

        assert console_module._console is None

    def test_reset_allows_new_options(self):
        from zoyd.tui.console import get_console, reset_console

        reset_console()
        console1 = get_console(width=80)
        assert console1.width == 80

        reset_console()
        console2 = get_console(width=120)
        assert console2.width == 120


class TestCreateConsole:
    def test_creates_new_instance(self):
        from rich.console import Console

        from zoyd.tui.console import create_console

        console = create_console()
        assert isinstance(console, Console)

    def test_not_singleton(self):
        from zoyd.tui.console import create_console

        console1 = create_console()
        console2 = create_console()
        assert console1 is not console2

    def test_has_zoyd_theme(self):
        from zoyd.tui.console import create_console

        console = create_console()
        assert "zoyd.banner" in console._theme.styles

    def test_custom_file_output(self):
        from zoyd.tui.console import create_console

        output = io.StringIO()
        console = create_console(file=output, force_terminal=True)
        console.print("hello")
        assert "hello" in output.getvalue()

    def test_record_mode(self):
        from zoyd.tui.console import create_console

        console = create_console(record=True)
        console.print("recorded output")
        # Can export to text
        text = console.export_text()
        assert "recorded output" in text

    def test_emoji_disabled(self):
        from zoyd.tui.console import create_console

        console = create_console()
        assert console._emoji is False


class TestModuleLevelConsole:
    def test_console_exported(self):
        from zoyd.tui.console import console

        from rich.console import Console

        assert isinstance(console, Console)

    def test_console_has_theme(self):
        from zoyd.tui.console import console

        assert "zoyd.banner" in console._theme.styles


class TestConsoleOutput:
    def test_styled_output(self):
        from zoyd.tui.console import create_console

        output = io.StringIO()
        console = create_console(file=output, force_terminal=True)
        console.print("[zoyd.banner]Banner Text[/]")
        result = output.getvalue()
        # Should contain the text (styling produces ANSI codes)
        assert "Banner Text" in result

    def test_markup_enabled(self):
        from zoyd.tui.console import create_console

        output = io.StringIO()
        console = create_console(file=output, force_terminal=True)
        console.print("[bold]bold text[/bold]")
        result = output.getvalue()
        # Should have ANSI escape codes for bold
        assert "\x1b[" in result

    def test_highlight_enabled(self):
        from zoyd.tui.console import create_console

        output = io.StringIO()
        console = create_console(file=output, force_terminal=True)
        # Highlight should colorize things like numbers
        console.print("The number 42 should be highlighted")
        # Just verify it doesn't crash - highlighting is subtle
        assert "42" in output.getvalue()
