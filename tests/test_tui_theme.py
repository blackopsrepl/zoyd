"""Tests for TUI theme module."""

import pytest

# Skip all tests if rich is not installed
rich = pytest.importorskip("rich")


class TestColors:
    def test_colors_dict_exists(self):
        from zoyd.tui.theme import COLORS

        assert isinstance(COLORS, dict)

    def test_colors_has_primary_palette(self):
        from zoyd.tui.theme import COLORS

        primary_colors = ["void", "shadow", "twilight", "amethyst", "orchid", "lavender", "mist"]
        for color in primary_colors:
            assert color in COLORS, f"Missing primary color: {color}"
            assert COLORS[color].startswith("#"), f"Color {color} should be hex"

    def test_colors_has_accent_colors(self):
        from zoyd.tui.theme import COLORS

        accent_colors = ["psionic", "tentacle", "elder"]
        for color in accent_colors:
            assert color in COLORS, f"Missing accent color: {color}"

    def test_colors_has_status_colors(self):
        from zoyd.tui.theme import COLORS

        status_colors = ["success", "warning", "error", "info"]
        for color in status_colors:
            assert color in COLORS, f"Missing status color: {color}"

    def test_colors_has_progress_states(self):
        from zoyd.tui.theme import COLORS

        progress_states = ["pending", "active", "complete", "blocked"]
        for state in progress_states:
            assert state in COLORS, f"Missing progress state: {state}"


class TestStyles:
    def test_styles_dict_exists(self):
        from zoyd.tui.theme import STYLES

        assert isinstance(STYLES, dict)

    def test_styles_are_rich_style_objects(self):
        from rich.style import Style

        from zoyd.tui.theme import STYLES

        for name, style in STYLES.items():
            assert isinstance(style, Style), f"STYLES['{name}'] should be a Style"

    def test_styles_has_text_styles(self):
        from zoyd.tui.theme import STYLES

        text_styles = ["text", "text.dim", "text.bright"]
        for style in text_styles:
            assert style in STYLES, f"Missing text style: {style}"

    def test_styles_has_status_styles(self):
        from zoyd.tui.theme import STYLES

        status_styles = ["status.success", "status.warning", "status.error", "status.info"]
        for style in status_styles:
            assert style in STYLES, f"Missing status style: {style}"

    def test_styles_has_task_styles(self):
        from zoyd.tui.theme import STYLES

        task_styles = ["task.pending", "task.active", "task.complete", "task.blocked"]
        for style in task_styles:
            assert style in STYLES, f"Missing task style: {style}"


class TestZoydTheme:
    def test_theme_exists(self):
        from rich.theme import Theme

        from zoyd.tui.theme import ZOYD_THEME

        assert isinstance(ZOYD_THEME, Theme)

    def test_theme_has_zoyd_styles(self):
        from zoyd.tui.theme import ZOYD_THEME

        zoyd_styles = [
            "zoyd.banner",
            "zoyd.iteration",
            "zoyd.task.pending",
            "zoyd.task.active",
            "zoyd.task.complete",
            "zoyd.task.blocked",
            "zoyd.cost.low",
            "zoyd.cost.medium",
            "zoyd.cost.high",
        ]
        for style in zoyd_styles:
            assert style in ZOYD_THEME.styles, f"Missing theme style: {style}"

    def test_theme_has_markdown_styles(self):
        from zoyd.tui.theme import ZOYD_THEME

        md_styles = ["markdown.h1", "markdown.h2", "markdown.h3", "markdown.code"]
        for style in md_styles:
            assert style in ZOYD_THEME.styles, f"Missing markdown style: {style}"

    def test_theme_has_progress_styles(self):
        from zoyd.tui.theme import ZOYD_THEME

        progress_styles = ["bar.back", "bar.complete", "bar.finished", "bar.pulse"]
        for style in progress_styles:
            assert style in ZOYD_THEME.styles, f"Missing progress style: {style}"


class TestGetCostStyle:
    def test_cost_low_when_under_half(self):
        from zoyd.tui.theme import get_cost_style

        assert get_cost_style(0.0, 1.0) == "zoyd.cost.low"
        assert get_cost_style(0.3, 1.0) == "zoyd.cost.low"
        assert get_cost_style(0.49, 1.0) == "zoyd.cost.low"

    def test_cost_medium_when_half_to_eighty(self):
        from zoyd.tui.theme import get_cost_style

        assert get_cost_style(0.5, 1.0) == "zoyd.cost.medium"
        assert get_cost_style(0.7, 1.0) == "zoyd.cost.medium"
        assert get_cost_style(0.79, 1.0) == "zoyd.cost.medium"

    def test_cost_high_when_over_eighty(self):
        from zoyd.tui.theme import get_cost_style

        assert get_cost_style(0.8, 1.0) == "zoyd.cost.high"
        assert get_cost_style(0.9, 1.0) == "zoyd.cost.high"
        assert get_cost_style(1.0, 1.0) == "zoyd.cost.high"
        assert get_cost_style(1.5, 1.0) == "zoyd.cost.high"

    def test_cost_low_when_max_zero(self):
        from zoyd.tui.theme import get_cost_style

        assert get_cost_style(0.5, 0.0) == "zoyd.cost.low"
        assert get_cost_style(1.0, 0.0) == "zoyd.cost.low"

    def test_cost_low_when_max_negative(self):
        from zoyd.tui.theme import get_cost_style

        assert get_cost_style(0.5, -1.0) == "zoyd.cost.low"


class TestGetTaskStyle:
    def test_complete_task(self):
        from zoyd.tui.theme import get_task_style

        assert get_task_style(complete=True) == "zoyd.task.complete"

    def test_pending_task(self):
        from zoyd.tui.theme import get_task_style

        assert get_task_style(complete=False) == "zoyd.task.pending"

    def test_active_task(self):
        from zoyd.tui.theme import get_task_style

        assert get_task_style(complete=False, active=True) == "zoyd.task.active"

    def test_blocked_task(self):
        from zoyd.tui.theme import get_task_style

        assert get_task_style(complete=False, blocked=True) == "zoyd.task.blocked"

    def test_blocked_takes_precedence(self):
        from zoyd.tui.theme import get_task_style

        # Blocked should show even if marked complete or active
        assert get_task_style(complete=True, blocked=True) == "zoyd.task.blocked"
        assert get_task_style(complete=False, active=True, blocked=True) == "zoyd.task.blocked"

    def test_complete_takes_precedence_over_active(self):
        from zoyd.tui.theme import get_task_style

        # If complete, should show complete even if active
        assert get_task_style(complete=True, active=True) == "zoyd.task.complete"
