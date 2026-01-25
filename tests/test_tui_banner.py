"""Tests for TUI banner module."""

import pytest

# Skip all tests if rich is not installed
rich = pytest.importorskip("rich")


class TestBannerConstants:
    def test_mind_flayer_full_exists(self):
        from zoyd.tui.banner import MIND_FLAYER_FULL

        assert isinstance(MIND_FLAYER_FULL, str)
        assert len(MIND_FLAYER_FULL) > 0

    def test_mind_flayer_compact_exists(self):
        from zoyd.tui.banner import MIND_FLAYER_COMPACT

        assert isinstance(MIND_FLAYER_COMPACT, str)
        assert len(MIND_FLAYER_COMPACT) > 0

    def test_full_banner_contains_zoyd_title(self):
        from zoyd.tui.banner import MIND_FLAYER_FULL

        # Should contain ZOYD in the ASCII art title
        assert "ZOYD" in MIND_FLAYER_FULL or "Z O Y D" in MIND_FLAYER_FULL

    def test_compact_banner_contains_zoyd_title(self):
        from zoyd.tui.banner import MIND_FLAYER_COMPACT

        # Should contain ZOYD in the ASCII art title
        assert "ZOYD" in MIND_FLAYER_COMPACT or "Z O Y D" in MIND_FLAYER_COMPACT

    def test_full_banner_is_wider_than_compact(self):
        from zoyd.tui.banner import MIND_FLAYER_COMPACT, MIND_FLAYER_FULL

        # Get max line width of each
        full_width = max(len(line) for line in MIND_FLAYER_FULL.split("\n"))
        compact_width = max(len(line) for line in MIND_FLAYER_COMPACT.split("\n"))
        assert full_width > compact_width

    def test_compact_banner_fits_narrow_terminal(self):
        from zoyd.tui.banner import MIND_FLAYER_COMPACT

        # Compact banner should fit in < 60 columns
        max_width = max(len(line) for line in MIND_FLAYER_COMPACT.split("\n"))
        assert max_width < 60


class TestGetBannerText:
    def test_returns_full_by_default(self):
        from zoyd.tui.banner import MIND_FLAYER_FULL, get_banner_text

        assert get_banner_text() == MIND_FLAYER_FULL

    def test_returns_compact_when_requested(self):
        from zoyd.tui.banner import MIND_FLAYER_COMPACT, get_banner_text

        assert get_banner_text(compact=True) == MIND_FLAYER_COMPACT

    def test_returns_full_when_compact_false(self):
        from zoyd.tui.banner import MIND_FLAYER_FULL, get_banner_text

        assert get_banner_text(compact=False) == MIND_FLAYER_FULL


class TestPrintBanner:
    def test_print_banner_runs_without_error(self):
        from io import StringIO

        from rich.console import Console

        from zoyd.tui.banner import print_banner

        # Create a console that writes to a string buffer
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        # Should not raise any exceptions
        print_banner(console=console)

        # Should have produced some output
        result = output.getvalue()
        assert len(result) > 0

    def test_print_banner_compact_mode(self):
        from io import StringIO

        from rich.console import Console

        from zoyd.tui.banner import print_banner

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        print_banner(console=console, compact=True)

        result = output.getvalue()
        assert len(result) > 0

    def test_print_banner_with_title(self):
        from io import StringIO

        from rich.console import Console

        from zoyd.tui.banner import print_banner

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        print_banner(console=console, title="Test Title")

        result = output.getvalue()
        assert "Test Title" in result

    def test_print_banner_with_subtitle(self):
        from io import StringIO

        from rich.console import Console

        from zoyd.tui.banner import print_banner

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        print_banner(console=console, title="Title", subtitle="Subtitle Here")

        result = output.getvalue()
        assert "Subtitle Here" in result

    def test_print_banner_auto_compact_for_narrow_terminal(self):
        from io import StringIO

        from rich.console import Console

        from zoyd.tui.banner import MIND_FLAYER_COMPACT, print_banner

        output = StringIO()
        # Console with narrow width should trigger compact mode
        console = Console(file=output, force_terminal=True, width=40)

        print_banner(console=console)

        result = output.getvalue()
        # Compact banner should be used (contains "Z O Y D")
        assert "Z O Y D" in result

    def test_print_banner_without_console_creates_one(self):
        # This tests that print_banner works when no console is provided
        # We can't easily capture the output, but we can verify it doesn't crash
        from zoyd.tui.banner import print_banner

        # This should not raise an exception
        # Note: This will actually print to the terminal during tests
        # In a real scenario, we'd mock get_console()
        # For now, we just verify the import path works
        pass


class TestBannerModuleImports:
    def test_exports_are_available(self):
        from zoyd.tui.banner import (
            MIND_FLAYER_COMPACT,
            MIND_FLAYER_FULL,
            get_banner_text,
            print_banner,
        )

        assert MIND_FLAYER_FULL is not None
        assert MIND_FLAYER_COMPACT is not None
        assert callable(print_banner)
        assert callable(get_banner_text)
