"""Tests for TUI panels module."""

import pytest

# Skip all tests if rich is not installed
rich = pytest.importorskip("rich")

from io import StringIO
from rich.console import Console
from rich.text import Text


class TestStatusBar:
    def test_creates_status_bar(self):
        from zoyd.tui.panels import StatusBar

        bar = StatusBar()
        assert bar is not None
        assert bar.title == "Status"

    def test_custom_title(self):
        from zoyd.tui.panels import StatusBar

        bar = StatusBar(title="My Status")
        assert bar.title == "My Status"

    def test_add_item(self):
        from zoyd.tui.panels import StatusBar

        bar = StatusBar()
        result = bar.add_item("PRD", "test.md")
        assert result is bar  # Returns self for chaining
        assert len(bar._items) == 1
        assert bar._items[0] == ("PRD", "test.md", None)

    def test_add_item_with_style(self):
        from zoyd.tui.panels import StatusBar

        bar = StatusBar()
        bar.add_item("Cost", "$1.00", "success")
        assert bar._items[0] == ("Cost", "$1.00", "success")

    def test_method_chaining(self):
        from zoyd.tui.panels import StatusBar

        bar = StatusBar()
        bar.add_item("A", "1").add_item("B", "2").add_item("C", "3")
        assert len(bar._items) == 3

    def test_clear(self):
        from zoyd.tui.panels import StatusBar

        bar = StatusBar()
        bar.add_item("A", "1").add_item("B", "2")
        result = bar.clear()
        assert result is bar
        assert len(bar._items) == 0

    def test_render_returns_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import StatusBar

        bar = StatusBar()
        bar.add_item("Test", "Value")
        rendered = bar.render()
        assert isinstance(rendered, Panel)

    def test_render_contains_items(self):
        from zoyd.tui.panels import StatusBar

        bar = StatusBar()
        bar.add_item("PRD", "test.md")
        bar.add_item("Model", "opus")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(bar.render())
        rendered = output.getvalue()

        assert "PRD" in rendered
        assert "test.md" in rendered
        assert "Model" in rendered
        assert "opus" in rendered

    def test_render_empty_bar(self):
        from rich.panel import Panel

        from zoyd.tui.panels import StatusBar

        bar = StatusBar()
        rendered = bar.render()
        assert isinstance(rendered, Panel)

    def test_print_method(self):
        from zoyd.tui.panels import StatusBar

        bar = StatusBar()
        bar.add_item("Test", "Value")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        bar.print(console)
        rendered = output.getvalue()

        assert "Test" in rendered
        assert "Value" in rendered


class TestOutputPanel:
    def test_creates_output_panel(self):
        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel()
        assert panel is not None
        assert panel.title == "Output"

    def test_custom_title(self):
        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel(title="Claude Output")
        assert panel.title == "Claude Output"

    def test_subtitle(self):
        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel(subtitle="Iteration 5")
        assert panel.subtitle == "Iteration 5"

    def test_set_content(self):
        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel()
        result = panel.set_content("Test content")
        assert result is panel
        assert panel._content == "Test content"

    def test_set_content_with_text(self):
        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel()
        text = Text("Styled content", style="bold")
        panel.set_content(text)
        assert panel._content is text

    def test_clear(self):
        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel()
        panel.set_content("Content")
        result = panel.clear()
        assert result is panel
        assert panel._content is None

    def test_render_returns_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel()
        panel.set_content("Test")
        rendered = panel.render()
        assert isinstance(rendered, Panel)

    def test_render_contains_content(self):
        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel()
        panel.set_content("Test content here")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Test content here" in rendered

    def test_render_empty_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel()
        rendered = panel.render()
        assert isinstance(rendered, Panel)

    def test_render_with_subtitle(self):
        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel(title="Output", subtitle="Step 1")
        panel.set_content("Content")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Step 1" in rendered

    def test_print_method(self):
        from zoyd.tui.panels import OutputPanel

        panel = OutputPanel()
        panel.set_content("Test output")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        panel.print(console)
        rendered = output.getvalue()

        assert "Test output" in rendered


class TestErrorPanel:
    def test_creates_error_panel(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        assert panel is not None
        assert panel.title == "Error"

    def test_custom_title(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel(title="Critical Error")
        assert panel.title == "Critical Error"

    def test_show_icon_default(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        assert panel.show_icon is True

    def test_show_icon_disabled(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel(show_icon=False)
        assert panel.show_icon is False

    def test_set_message(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        result = panel.set_message("Something went wrong")
        assert result is panel
        assert panel._message == "Something went wrong"

    def test_set_details(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        result = panel.set_details("Stack trace here")
        assert result is panel
        assert panel._details == "Stack trace here"

    def test_set_suggestion(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        result = panel.set_suggestion("Try again")
        assert result is panel
        assert panel._suggestion == "Try again"

    def test_method_chaining(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        panel.set_message("Error").set_details("Details").set_suggestion("Fix it")
        assert panel._message == "Error"
        assert panel._details == "Details"
        assert panel._suggestion == "Fix it"

    def test_clear(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        panel.set_message("Error").set_details("Details").set_suggestion("Fix")
        result = panel.clear()
        assert result is panel
        assert panel._message is None
        assert panel._details is None
        assert panel._suggestion is None

    def test_render_returns_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        panel.set_message("Error")
        rendered = panel.render()
        assert isinstance(rendered, Panel)

    def test_render_contains_message(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        panel.set_message("Task failed")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Task failed" in rendered

    def test_render_contains_details(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        panel.set_message("Error").set_details("Detailed info here")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Detailed info here" in rendered

    def test_render_contains_suggestion(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        panel.set_message("Error").set_suggestion("Check your config")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Suggestion" in rendered
        assert "Check your config" in rendered

    def test_render_empty_panel(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        # Should show default message
        assert "error occurred" in rendered.lower()

    def test_print_method(self):
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        panel.set_message("Test error")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        panel.print(console)
        rendered = output.getvalue()

        assert "Test error" in rendered


class TestCreateStatusBar:
    def test_creates_bar(self):
        from zoyd.tui.panels import create_status_bar

        bar = create_status_bar()
        assert bar is not None

    def test_with_prd(self):
        from zoyd.tui.panels import create_status_bar

        bar = create_status_bar(prd="test.md")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(bar.render())
        rendered = output.getvalue()

        assert "PRD" in rendered
        assert "test.md" in rendered

    def test_with_iteration(self):
        from zoyd.tui.panels import create_status_bar

        bar = create_status_bar(iteration=5)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(bar.render())
        rendered = output.getvalue()

        assert "Iteration" in rendered
        assert "5" in rendered

    def test_with_iteration_and_max(self):
        from zoyd.tui.panels import create_status_bar

        bar = create_status_bar(iteration=5, max_iterations=10)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(bar.render())
        rendered = output.getvalue()

        assert "5/10" in rendered

    def test_with_model(self):
        from zoyd.tui.panels import create_status_bar

        bar = create_status_bar(model="opus")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(bar.render())
        rendered = output.getvalue()

        assert "Model" in rendered
        assert "opus" in rendered

    def test_with_cost(self):
        from zoyd.tui.panels import create_status_bar

        bar = create_status_bar(cost=1.5)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(bar.render())
        rendered = output.getvalue()

        assert "Cost" in rendered
        assert "$1.5" in rendered

    def test_with_cost_and_max(self):
        from zoyd.tui.panels import create_status_bar

        bar = create_status_bar(cost=1.0, max_cost=5.0)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(bar.render())
        rendered = output.getvalue()

        assert "$1.0" in rendered
        assert "/$5.00" in rendered

    def test_all_options(self):
        from zoyd.tui.panels import create_status_bar

        bar = create_status_bar(
            prd="my.md",
            iteration=3,
            max_iterations=10,
            model="sonnet",
            cost=0.5,
            max_cost=2.0,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(bar.render())
        rendered = output.getvalue()

        assert "my.md" in rendered
        assert "3/10" in rendered
        assert "sonnet" in rendered
        assert "$0.5" in rendered


class TestCreateOutputPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import create_output_panel

        panel = create_output_panel("Test content")
        assert panel is not None
        assert panel._content == "Test content"

    def test_custom_title(self):
        from zoyd.tui.panels import create_output_panel

        panel = create_output_panel("Content", title="Custom")
        assert panel.title == "Custom"

    def test_with_subtitle(self):
        from zoyd.tui.panels import create_output_panel

        panel = create_output_panel("Content", subtitle="Sub")
        assert panel.subtitle == "Sub"


class TestCreateErrorPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import create_error_panel

        panel = create_error_panel("Error message")
        assert panel is not None
        assert panel._message == "Error message"

    def test_custom_title(self):
        from zoyd.tui.panels import create_error_panel

        panel = create_error_panel("Error", title="Critical")
        assert panel.title == "Critical"

    def test_with_details(self):
        from zoyd.tui.panels import create_error_panel

        panel = create_error_panel("Error", details="Details here")
        assert panel._details == "Details here"

    def test_with_suggestion(self):
        from zoyd.tui.panels import create_error_panel

        panel = create_error_panel("Error", suggestion="Try again")
        assert panel._suggestion == "Try again"

    def test_all_options(self):
        from zoyd.tui.panels import create_error_panel

        panel = create_error_panel(
            "Main error",
            title="Fatal",
            details="Stack trace",
            suggestion="Fix it",
        )
        assert panel.title == "Fatal"
        assert panel._message == "Main error"
        assert panel._details == "Stack trace"
        assert panel._suggestion == "Fix it"


class TestModuleExports:
    def test_status_bar_importable(self):
        from zoyd.tui.panels import StatusBar

        assert StatusBar is not None

    def test_output_panel_importable(self):
        from zoyd.tui.panels import OutputPanel

        assert OutputPanel is not None

    def test_error_panel_importable(self):
        from zoyd.tui.panels import ErrorPanel

        assert ErrorPanel is not None

    def test_create_status_bar_importable(self):
        from zoyd.tui.panels import create_status_bar

        assert callable(create_status_bar)

    def test_create_output_panel_importable(self):
        from zoyd.tui.panels import create_output_panel

        assert callable(create_output_panel)

    def test_create_error_panel_importable(self):
        from zoyd.tui.panels import create_error_panel

        assert callable(create_error_panel)

    def test_exports_from_tui_init(self):
        from zoyd.tui import (
            StatusBar,
            OutputPanel,
            ErrorPanel,
            create_status_bar,
            create_output_panel,
            create_error_panel,
        )

        assert StatusBar is not None
        assert OutputPanel is not None
        assert ErrorPanel is not None
        assert callable(create_status_bar)
        assert callable(create_output_panel)
        assert callable(create_error_panel)
