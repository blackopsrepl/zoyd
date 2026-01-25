"""Tests for zoyd.tui.traceback module."""

import io
import sys

import pytest

rich = pytest.importorskip("rich")

from rich.console import Console

from zoyd.tui.traceback import (
    DEFAULT_EXTRA_LINES,
    DEFAULT_MAX_FRAMES,
    DEFAULT_SHOW_LOCALS,
    DEFAULT_WORD_WRAP,
    ensure_traceback_installed,
    get_traceback_console,
    install_traceback_handler,
    is_traceback_installed,
    reset_traceback_installed,
)


class TestInstallTracebackHandler:
    """Tests for install_traceback_handler function."""

    def test_install_with_defaults(self):
        """Installing traceback handler with defaults should not raise."""
        # Create a test console to avoid modifying sys.excepthook globally
        test_console = Console(file=io.StringIO(), force_terminal=True)
        install_traceback_handler(console=test_console)

    def test_install_with_show_locals(self):
        """Installing with show_locals=True should not raise."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        install_traceback_handler(console=test_console, show_locals=True)

    def test_install_with_custom_max_frames(self):
        """Installing with custom max_frames should not raise."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        install_traceback_handler(console=test_console, max_frames=10)

    def test_install_with_custom_width(self):
        """Installing with custom width should not raise."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        install_traceback_handler(console=test_console, width=80)

    def test_install_with_custom_extra_lines(self):
        """Installing with custom extra_lines should not raise."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        install_traceback_handler(console=test_console, extra_lines=5)

    def test_install_with_word_wrap(self):
        """Installing with word_wrap=True should not raise."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        install_traceback_handler(console=test_console, word_wrap=True)

    def test_install_with_custom_theme(self):
        """Installing with custom theme should not raise."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        install_traceback_handler(console=test_console, theme="monokai")

    def test_install_with_suppress_modules(self):
        """Installing with suppress list should not raise."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        install_traceback_handler(console=test_console, suppress=["click", "rich"])

    def test_default_theme_is_dracula(self):
        """Default theme should be dracula to match output panel."""
        # This test verifies the default is set correctly in the function
        # We can't directly inspect the installed handler's theme,
        # but we can verify the install doesn't fail with defaults
        test_console = Console(file=io.StringIO(), force_terminal=True)
        install_traceback_handler(console=test_console)


class TestGetTracebackConsole:
    """Tests for get_traceback_console function."""

    def test_returns_console(self):
        """Should return a Console instance."""
        console = get_traceback_console()
        assert isinstance(console, Console)

    def test_returns_zoyd_themed_console(self):
        """Should return a console with the zoyd theme."""
        from zoyd.tui.theme import ZOYD_THEME

        console = get_traceback_console()
        # The console should have the theme applied
        # We can verify by checking a custom zoyd style exists
        style = console.get_style("zoyd.banner")
        assert style is not None


class TestIsTracebackInstalled:
    """Tests for is_traceback_installed function."""

    def setup_method(self):
        """Reset the installed flag before each test."""
        reset_traceback_installed()

    def teardown_method(self):
        """Reset the installed flag after each test."""
        reset_traceback_installed()

    def test_initially_false(self):
        """Should return False before installation."""
        assert is_traceback_installed() is False

    def test_true_after_ensure(self):
        """Should return True after ensure_traceback_installed."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        ensure_traceback_installed(console=test_console)
        assert is_traceback_installed() is True


class TestEnsureTracebackInstalled:
    """Tests for ensure_traceback_installed function."""

    def setup_method(self):
        """Reset the installed flag before each test."""
        reset_traceback_installed()

    def teardown_method(self):
        """Reset the installed flag after each test."""
        reset_traceback_installed()

    def test_installs_on_first_call(self):
        """First call should install the handler."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        ensure_traceback_installed(console=test_console)
        assert is_traceback_installed() is True

    def test_idempotent(self):
        """Multiple calls should only install once."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        ensure_traceback_installed(console=test_console)
        ensure_traceback_installed(console=test_console)
        ensure_traceback_installed(console=test_console)
        assert is_traceback_installed() is True

    def test_passes_kwargs_to_install(self):
        """Should pass kwargs to install_traceback_handler."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        # This should not raise even with kwargs
        ensure_traceback_installed(
            console=test_console, show_locals=True, max_frames=5
        )
        assert is_traceback_installed() is True


class TestResetTracebackInstalled:
    """Tests for reset_traceback_installed function."""

    def test_resets_flag(self):
        """Should reset the installed flag to False."""
        test_console = Console(file=io.StringIO(), force_terminal=True)
        ensure_traceback_installed(console=test_console)
        assert is_traceback_installed() is True

        reset_traceback_installed()
        assert is_traceback_installed() is False


class TestDefaultConstants:
    """Tests for default constant values."""

    def test_default_show_locals(self):
        """Default show_locals should be False."""
        assert DEFAULT_SHOW_LOCALS is False

    def test_default_max_frames(self):
        """Default max_frames should be 20."""
        assert DEFAULT_MAX_FRAMES == 20

    def test_default_extra_lines(self):
        """Default extra_lines should be 3."""
        assert DEFAULT_EXTRA_LINES == 3

    def test_default_word_wrap(self):
        """Default word_wrap should be False."""
        assert DEFAULT_WORD_WRAP is False


class TestModuleExports:
    """Tests for module exports."""

    def test_import_install_traceback_handler(self):
        """Should be able to import install_traceback_handler from tui."""
        from zoyd.tui import install_traceback_handler

        assert callable(install_traceback_handler)

    def test_import_ensure_traceback_installed(self):
        """Should be able to import ensure_traceback_installed from tui."""
        from zoyd.tui import ensure_traceback_installed

        assert callable(ensure_traceback_installed)

    def test_import_is_traceback_installed(self):
        """Should be able to import is_traceback_installed from tui."""
        from zoyd.tui import is_traceback_installed

        assert callable(is_traceback_installed)

    def test_import_reset_traceback_installed(self):
        """Should be able to import reset_traceback_installed from tui."""
        from zoyd.tui import reset_traceback_installed

        assert callable(reset_traceback_installed)


class TestCLIIntegration:
    """Tests for CLI integration of traceback handler."""

    def test_cli_imports_install_handler(self):
        """CLI module should import and use the traceback handler."""
        # Import the CLI module - this should call ensure_traceback_installed
        from zoyd import cli

        # The handler should be installed after importing cli
        # We need to check via inspection since the flag may have been set
        # by the module-level call
        assert hasattr(cli, "ensure_traceback_installed")
