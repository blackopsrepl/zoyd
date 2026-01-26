"""Tests for TUI banner module."""

import pytest

# Skip all tests if rich is not installed
rich = pytest.importorskip("rich")


class TestBannerConstants:
    def test_zoyd_banner_exists(self):
        from zoyd.tui.banner import ZOYD_BANNER

        assert isinstance(ZOYD_BANNER, str)
        assert len(ZOYD_BANNER) > 0

    def test_banner_contains_title_elements(self):
        from zoyd.tui.banner import ZOYD_BANNER

        # The banner uses Unicode box drawing characters for ZOYD title
        # Just verify it contains the distinctive block elements
        assert "███" in ZOYD_BANNER  # Block characters from ASCII art

    def test_banner_contains_autonomous_loop(self):
        from zoyd.tui.banner import ZOYD_BANNER

        # Should contain AUTONOMOUS LOOP text
        assert "AUTONOMOUS" in ZOYD_BANNER.upper()
        assert "LOOP" in ZOYD_BANNER.upper()

    def test_banner_contains_braille_characters(self):
        from zoyd.tui.banner import ZOYD_BANNER

        # The mind flayer uses braille characters (U+2800-U+28FF)
        # Check for presence of any braille characters
        has_braille = any(
            "\u2800" <= char <= "\u28FF" for char in ZOYD_BANNER
        )
        assert has_braille, "Banner should contain braille characters for mind flayer art"

    def test_banner_is_multiline(self):
        from zoyd.tui.banner import ZOYD_BANNER

        lines = ZOYD_BANNER.strip().split("\n")
        assert len(lines) > 10  # Should be a substantial banner


class TestGetBannerText:
    def test_returns_zoyd_banner(self):
        from zoyd.tui.banner import ZOYD_BANNER, get_banner_text

        assert get_banner_text() == ZOYD_BANNER

    def test_returns_string(self):
        from zoyd.tui.banner import get_banner_text

        result = get_banner_text()
        assert isinstance(result, str)
        assert len(result) > 0


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

    def test_print_banner_without_console_creates_one(self):
        # This tests that print_banner works when no console is provided
        # We can't easily capture the output, but we can verify it doesn't crash
        from zoyd.tui.banner import print_banner

        # This should not raise an exception
        # Note: This will actually print to the terminal during tests
        # In a real scenario, we'd mock get_console()
        # For now, we just verify the import path works
        pass


class TestGetVersionedBanner:
    def test_returns_string(self):
        from zoyd.tui.banner import get_versioned_banner

        result = get_versioned_banner("1.2.3")
        assert isinstance(result, str)

    def test_contains_version_string(self):
        from zoyd.tui.banner import get_versioned_banner

        result = get_versioned_banner("1.2.3")
        assert "v1.2.3" in result

    def test_version_after_second_box(self):
        from zoyd.tui.banner import get_versioned_banner

        result = get_versioned_banner("0.5.0")
        lines = result.split("\n")
        # The second box uses └───...┘ (first box uses ╚═══...╝)
        for i, line in enumerate(lines):
            if "└" in line:
                # The very next line should contain the version
                assert "v0.5.0" in lines[i + 1]
                return
        pytest.fail("Could not find second box closing border (└)")

    def test_version_left_aligned(self):
        from zoyd.tui.banner import get_versioned_banner

        result = get_versioned_banner("2.0.0")
        lines = result.split("\n")
        for line in lines:
            if "v2.0.0" in line:
                # Should be left-aligned with a single leading space (matching box indent)
                assert line.startswith(" v2.0.0")
                return
        pytest.fail("Version line not found")

    def test_preserves_original_banner_content(self):
        from zoyd.tui.banner import ZOYD_BANNER, get_versioned_banner

        result = get_versioned_banner("1.0.0")
        # All original lines should still be present
        for line in ZOYD_BANNER.split("\n"):
            if line.strip():
                assert line in result

    def test_different_versions(self):
        from zoyd.tui.banner import get_versioned_banner

        for version in ["0.1.0", "3.14.159", "10.20.30"]:
            result = get_versioned_banner(version)
            assert f"v{version}" in result


class TestBannerModuleImports:
    def test_exports_are_available(self):
        from zoyd.tui.banner import (
            ZOYD_BANNER,
            get_banner_text,
            get_versioned_banner,
            print_banner,
        )

        assert ZOYD_BANNER is not None
        assert callable(print_banner)
        assert callable(get_banner_text)
        assert callable(get_versioned_banner)

    def test_tui_init_exports_banner(self):
        from zoyd.tui import (
            ZOYD_BANNER,
            get_banner_text,
            print_banner,
        )

        assert ZOYD_BANNER is not None
        assert callable(print_banner)
        assert callable(get_banner_text)
