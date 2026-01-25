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

    def test_render_has_red_border_style(self):
        """Verify error panel uses red border color."""
        from zoyd.tui.panels import ErrorPanel
        from zoyd.tui.theme import COLORS

        panel = ErrorPanel()
        panel.set_message("Error")
        rendered = panel.render()

        # Verify border_style is the error color
        assert rendered.border_style == COLORS["error"]

    def test_render_title_has_error_styling(self):
        """Verify error panel title uses error styling."""
        from zoyd.tui.panels import ErrorPanel

        panel = ErrorPanel()
        panel.set_message("Error")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        # The title should contain the X icon and Error text
        assert "Error" in rendered


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
            ClaudeOutputPanel,
            ErrorPanel,
            WarningPanel,
            BlockedTaskPanel,
            IterationHistoryPanel,
            GitCommitLogPanel,
            create_status_bar,
            create_output_panel,
            create_claude_output_panel,
            create_error_panel,
            create_warning_panel,
            create_blocked_task_panel,
            create_iteration_history_panel,
            create_git_commit_log_panel,
        )

        assert StatusBar is not None
        assert OutputPanel is not None
        assert ClaudeOutputPanel is not None
        assert ErrorPanel is not None
        assert WarningPanel is not None
        assert BlockedTaskPanel is not None
        assert IterationHistoryPanel is not None
        assert GitCommitLogPanel is not None
        assert callable(create_status_bar)
        assert callable(create_output_panel)
        assert callable(create_claude_output_panel)
        assert callable(create_error_panel)
        assert callable(create_warning_panel)
        assert callable(create_blocked_task_panel)
        assert callable(create_iteration_history_panel)
        assert callable(create_git_commit_log_panel)

    def test_iteration_history_panel_importable(self):
        from zoyd.tui.panels import IterationHistoryPanel

        assert IterationHistoryPanel is not None

    def test_create_iteration_history_panel_importable(self):
        from zoyd.tui.panels import create_iteration_history_panel

        assert callable(create_iteration_history_panel)

    def test_claude_output_panel_importable(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        assert ClaudeOutputPanel is not None

    def test_create_claude_output_panel_importable(self):
        from zoyd.tui.panels import create_claude_output_panel

        assert callable(create_claude_output_panel)

    def test_git_commit_log_panel_importable(self):
        from zoyd.tui.panels import GitCommitLogPanel

        assert GitCommitLogPanel is not None

    def test_create_git_commit_log_panel_importable(self):
        from zoyd.tui.panels import create_git_commit_log_panel

        assert callable(create_git_commit_log_panel)

    def test_blocked_task_panel_importable(self):
        from zoyd.tui.panels import BlockedTaskPanel

        assert BlockedTaskPanel is not None

    def test_create_blocked_task_panel_importable(self):
        from zoyd.tui.panels import create_blocked_task_panel

        assert callable(create_blocked_task_panel)


class TestWarningPanel:
    def test_creates_warning_panel(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        assert panel is not None
        assert panel.title == "Warning"

    def test_custom_title(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel(title="PRD Validation")
        assert panel.title == "PRD Validation"

    def test_show_icon_default(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        assert panel.show_icon is True

    def test_show_icon_disabled(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel(show_icon=False)
        assert panel.show_icon is False

    def test_add_item(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        result = panel.add_item("Line 5: Empty task")
        assert result is panel  # Returns self for chaining
        assert len(panel._items) == 1
        assert panel._items[0] == ("Line 5: Empty task", None)

    def test_add_item_with_detail(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        panel.add_item("Line 5: Empty task", "- [ ]")
        assert panel._items[0] == ("Line 5: Empty task", "- [ ]")

    def test_method_chaining(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        panel.add_item("Warning 1").add_item("Warning 2").add_item("Warning 3")
        assert len(panel._items) == 3

    def test_clear(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        panel.add_item("Warning 1").add_item("Warning 2")
        result = panel.clear()
        assert result is panel
        assert len(panel._items) == 0

    def test_render_returns_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        panel.add_item("Test warning")
        rendered = panel.render()
        assert isinstance(rendered, Panel)

    def test_render_contains_items(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        panel.add_item("Line 5: Missing space", "- []task")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Line 5: Missing space" in rendered
        assert "- []task" in rendered

    def test_render_multiple_items(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        panel.add_item("Warning 1", "detail 1")
        panel.add_item("Warning 2", "detail 2")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Warning 1" in rendered
        assert "Warning 2" in rendered
        assert "detail 1" in rendered
        assert "detail 2" in rendered

    def test_render_empty_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        rendered = panel.render()
        assert isinstance(rendered, Panel)

    def test_print_method(self):
        from zoyd.tui.panels import WarningPanel

        panel = WarningPanel()
        panel.add_item("Test warning")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        panel.print(console)
        rendered = output.getvalue()

        assert "Test warning" in rendered


class TestClaudeOutputPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        assert panel is not None
        assert panel.title == "Claude Output"

    def test_custom_title(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel(title="AI Response")
        assert panel.title == "AI Response"

    def test_subtitle(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel(subtitle="Iteration 5")
        assert panel.subtitle == "Iteration 5"

    def test_set_content(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        result = panel.set_content("# Hello World")
        assert result is panel
        assert panel._content == "# Hello World"

    def test_set_markdown_enabled_by_default(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        assert panel._use_markdown is True

    def test_set_markdown_disable(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        result = panel.set_markdown(False)
        assert result is panel
        assert panel._use_markdown is False

    def test_clear(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        panel.set_content("Some content")
        result = panel.clear()
        assert result is panel
        assert panel._content == ""

    def test_render_returns_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        panel.set_content("# Test")
        rendered = panel.render()
        assert isinstance(rendered, Panel)

    def test_render_empty_shows_placeholder(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Awaiting Claude output" in rendered

    def test_render_markdown_content(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        panel.set_content("# Heading\n\nSome **bold** text")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        # The heading and text should be present
        assert "Heading" in rendered
        assert "bold" in rendered

    def test_render_plain_text_when_markdown_disabled(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        panel.set_content("# Not a heading")
        panel.set_markdown(False)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        # Should contain the raw markdown syntax
        assert "# Not a heading" in rendered

    def test_render_code_blocks(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        content = "```python\ndef hello():\n    print('Hello')\n```"
        panel = ClaudeOutputPanel()
        panel.set_content(content)

        output = StringIO()
        # Use no_color to avoid ANSI escape sequences breaking assertions
        console = Console(file=output, force_terminal=True, width=80, no_color=True)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "def hello" in rendered
        assert "print" in rendered

    def test_render_with_subtitle(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel(subtitle="Iteration 3")
        panel.set_content("Test output")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Iteration 3" in rendered

    def test_print_method(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        panel.set_content("# Test Output")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        panel.print(console)
        rendered = output.getvalue()

        assert "Test Output" in rendered

    def test_method_chaining(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        panel.set_content("Content").set_markdown(True)
        assert panel._content == "Content"
        assert panel._use_markdown is True

    def test_default_code_theme_is_dracula(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        assert panel._code_theme == "dracula"
        assert ClaudeOutputPanel.DEFAULT_CODE_THEME == "dracula"

    def test_custom_code_theme_in_constructor(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel(code_theme="monokai")
        assert panel._code_theme == "monokai"

    def test_set_code_theme(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        result = panel.set_code_theme("github-dark")
        assert result is panel  # Returns self for chaining
        assert panel._code_theme == "github-dark"

    def test_code_theme_method_chaining(self):
        from zoyd.tui.panels import ClaudeOutputPanel

        panel = ClaudeOutputPanel()
        panel.set_content("```python\nprint('test')\n```").set_code_theme("monokai")
        assert panel._code_theme == "monokai"
        assert panel._content == "```python\nprint('test')\n```"

    def test_render_code_blocks_with_syntax_highlighting(self):
        import re

        from zoyd.tui.panels import ClaudeOutputPanel

        content = "```python\ndef greet(name):\n    return f'Hello, {name}!'\n```"
        panel = ClaudeOutputPanel()
        panel.set_content(content)

        output = StringIO()
        # Use force_terminal to enable color/syntax highlighting
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        # With syntax highlighting, there should be ANSI escape codes
        assert "\x1b[" in rendered  # ANSI escape sequence

        # Strip ANSI codes to check content
        ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
        plain = ansi_escape.sub("", rendered)

        # Code should be present in plain text
        assert "def greet" in plain
        assert "name" in plain

    def test_render_multiple_languages(self):
        import re

        from zoyd.tui.panels import ClaudeOutputPanel

        content = """
```python
def hello():
    pass
```

```javascript
function hello() {}
```
"""
        panel = ClaudeOutputPanel()
        panel.set_content(content)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        # Strip ANSI codes to check content
        ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
        plain = ansi_escape.sub("", rendered)

        assert "def hello" in plain
        assert "function hello" in plain


class TestCreateClaudeOutputPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import create_claude_output_panel

        panel = create_claude_output_panel("# Test")
        assert panel is not None
        assert panel._content == "# Test"

    def test_custom_title(self):
        from zoyd.tui.panels import create_claude_output_panel

        panel = create_claude_output_panel("Test", title="AI Output")
        assert panel.title == "AI Output"

    def test_with_subtitle(self):
        from zoyd.tui.panels import create_claude_output_panel

        panel = create_claude_output_panel("Test", subtitle="Iteration 1")
        assert panel.subtitle == "Iteration 1"

    def test_markdown_enabled_by_default(self):
        from zoyd.tui.panels import create_claude_output_panel

        panel = create_claude_output_panel("# Test")
        assert panel._use_markdown is True

    def test_markdown_can_be_disabled(self):
        from zoyd.tui.panels import create_claude_output_panel

        panel = create_claude_output_panel("# Test", use_markdown=False)
        assert panel._use_markdown is False

    def test_empty_content(self):
        from zoyd.tui.panels import create_claude_output_panel

        panel = create_claude_output_panel()
        assert panel._content == ""

    def test_default_code_theme_is_dracula(self):
        from zoyd.tui.panels import create_claude_output_panel

        panel = create_claude_output_panel("# Test")
        assert panel._code_theme == "dracula"

    def test_custom_code_theme(self):
        from zoyd.tui.panels import create_claude_output_panel

        panel = create_claude_output_panel("# Test", code_theme="monokai")
        assert panel._code_theme == "monokai"


class TestIterationHistoryPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        assert panel is not None
        assert panel.title == "History"

    def test_custom_title(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel(title="Iteration History")
        assert panel.title == "Iteration History"

    def test_custom_max_items(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel(max_items=5)
        assert panel.max_items == 5

    def test_add_iteration(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        result = panel.add_iteration(1, status="success", cost=0.05, duration=10.5)
        assert result is panel  # Returns self for chaining
        assert len(panel._items) == 1
        assert panel._items[0]["iteration"] == 1
        assert panel._items[0]["status"] == "success"
        assert panel._items[0]["cost"] == 0.05
        assert panel._items[0]["duration"] == 10.5

    def test_add_iteration_with_task(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="running", task="Add new feature")
        assert panel._items[0]["task"] == "Add new feature"

    def test_method_chaining(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1).add_iteration(2).add_iteration(3)
        assert len(panel._items) == 3

    def test_max_items_limit(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel(max_items=3)
        for i in range(5):
            panel.add_iteration(i + 1)
        assert len(panel._items) == 3
        # Should keep the most recent 3
        assert panel._items[0]["iteration"] == 3
        assert panel._items[1]["iteration"] == 4
        assert panel._items[2]["iteration"] == 5

    def test_update_iteration(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="running")
        result = panel.update_iteration(1, status="success", duration=15.0)
        assert result is panel  # Returns self for chaining
        assert panel._items[0]["status"] == "success"
        assert panel._items[0]["duration"] == 15.0

    def test_update_iteration_partial(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="running", cost=0.01)
        panel.update_iteration(1, status="success")
        # Cost should remain unchanged
        assert panel._items[0]["cost"] == 0.01
        assert panel._items[0]["status"] == "success"

    def test_update_nonexistent_iteration(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="running")
        # Should not raise, just do nothing
        panel.update_iteration(999, status="success")
        assert panel._items[0]["status"] == "running"

    def test_clear(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1).add_iteration(2)
        result = panel.clear()
        assert result is panel
        assert len(panel._items) == 0

    def test_render_returns_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="success")
        rendered = panel.render()
        assert isinstance(rendered, Panel)

    def test_render_empty_shows_placeholder(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "No iterations yet" in rendered

    def test_render_contains_iteration_number(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(5, status="success")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "5" in rendered

    def test_render_contains_cost(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="success", cost=0.1234)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "$0.1234" in rendered

    def test_render_contains_duration_seconds(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="success", duration=45.5)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "45.5s" in rendered

    def test_render_contains_duration_minutes(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="success", duration=125.0)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "2m 5s" in rendered

    def test_render_contains_task(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="running", task="Add feature")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Add feature" in rendered

    def test_render_truncates_long_task(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        long_task = "This is a very long task description that should be truncated"
        panel.add_iteration(1, status="running", task=long_task)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "..." in rendered

    def test_render_multiple_iterations(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="success", cost=0.05, duration=10.0)
        panel.add_iteration(2, status="failed", cost=0.03, duration=5.0)
        panel.add_iteration(3, status="running")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "1" in rendered
        assert "2" in rendered
        assert "3" in rendered

    def test_print_method(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        panel.add_iteration(1, status="success")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        panel.print(console)
        rendered = output.getvalue()

        assert "1" in rendered

    def test_format_duration_none(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        assert panel._format_duration(None) == "-"

    def test_format_cost_none(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        assert panel._format_cost(None) == "-"

    def test_truncate_task_none(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        assert panel._truncate_task(None) == "-"

    def test_truncate_task_short(self):
        from zoyd.tui.panels import IterationHistoryPanel

        panel = IterationHistoryPanel()
        assert panel._truncate_task("Short task") == "Short task"


class TestCreateIterationHistoryPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import create_iteration_history_panel

        panel = create_iteration_history_panel()
        assert panel is not None

    def test_custom_title(self):
        from zoyd.tui.panels import create_iteration_history_panel

        panel = create_iteration_history_panel(title="Loop History")
        assert panel.title == "Loop History"

    def test_custom_max_items(self):
        from zoyd.tui.panels import create_iteration_history_panel

        panel = create_iteration_history_panel(max_items=20)
        assert panel.max_items == 20


class TestCreateWarningPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import create_warning_panel

        panel = create_warning_panel([("Warning 1", None)])
        assert panel is not None
        assert len(panel._items) == 1

    def test_custom_title(self):
        from zoyd.tui.panels import create_warning_panel

        panel = create_warning_panel([("Warning", None)], title="PRD Validation")
        assert panel.title == "PRD Validation"

    def test_multiple_items(self):
        from zoyd.tui.panels import create_warning_panel

        items = [
            ("Line 5: Empty task", "- [ ]"),
            ("Line 10: Malformed", "- []text"),
        ]
        panel = create_warning_panel(items)
        assert len(panel._items) == 2

    def test_empty_items(self):
        from zoyd.tui.panels import create_warning_panel

        panel = create_warning_panel([])
        assert len(panel._items) == 0

    def test_render_output(self):
        from zoyd.tui.panels import create_warning_panel

        items = [
            ("Line 5: Empty task text", "- [ ]"),
        ]
        panel = create_warning_panel(items, title="PRD Validation")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        panel.print(console)
        rendered = output.getvalue()

        assert "PRD Validation" in rendered
        assert "Line 5: Empty task text" in rendered
        assert "- [ ]" in rendered


class TestGitCommitLogPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        assert panel is not None
        assert panel.title == "Git Commits"

    def test_custom_title(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel(title="Session Commits")
        assert panel.title == "Session Commits"

    def test_custom_max_items(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel(max_items=5)
        assert panel.max_items == 5

    def test_add_commit(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        result = panel.add_commit(iteration=1, message="Initial commit")
        assert result is panel  # Returns self for chaining
        assert len(panel._commits) == 1
        assert panel._commits[0]["iteration"] == 1
        assert panel._commits[0]["message"] == "Initial commit"

    def test_add_commit_with_hash(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        panel.add_commit(iteration=1, message="Test", commit_hash="abc123def")
        assert panel._commits[0]["hash"] == "abc123def"

    def test_method_chaining(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        panel.add_commit(iteration=1, message="A").add_commit(
            iteration=2, message="B"
        ).add_commit(iteration=3, message="C")
        assert len(panel._commits) == 3

    def test_max_items_trims_old(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel(max_items=3)
        for i in range(5):
            panel.add_commit(iteration=i + 1, message=f"Commit {i + 1}")

        assert len(panel._commits) == 3
        # Should have kept the last 3
        assert panel._commits[0]["iteration"] == 3
        assert panel._commits[1]["iteration"] == 4
        assert panel._commits[2]["iteration"] == 5

    def test_clear(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        panel.add_commit(iteration=1, message="A")
        panel.add_commit(iteration=2, message="B")
        result = panel.clear()
        assert result is panel
        assert len(panel._commits) == 0

    def test_render_returns_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        panel.add_commit(iteration=1, message="Test commit")
        result = panel.render()
        assert isinstance(result, Panel)

    def test_render_empty_shows_placeholder(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "No commits yet" in rendered

    def test_render_contains_iteration(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        panel.add_commit(iteration=42, message="Test")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "42" in rendered

    def test_render_contains_hash(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        panel.add_commit(iteration=1, message="Test", commit_hash="abc123def456")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        # Hash is truncated to first 7 chars
        assert "abc123d" in rendered

    def test_render_contains_message(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        panel.add_commit(iteration=1, message="feat: add new feature")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "feat: add new feature" in rendered

    def test_render_truncates_long_message(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        long_msg = "This is a very long commit message that definitely exceeds the limit"
        panel.add_commit(iteration=1, message=long_msg)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "..." in rendered

    def test_render_multiple_commits(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        panel.add_commit(iteration=1, message="First commit", commit_hash="aaa1111")
        panel.add_commit(iteration=2, message="Second commit", commit_hash="bbb2222")
        panel.add_commit(iteration=3, message="Third commit", commit_hash="ccc3333")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "1" in rendered
        assert "2" in rendered
        assert "3" in rendered

    def test_render_no_hash_shows_dash(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        panel.add_commit(iteration=1, message="Test")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        # When no hash provided, should show dash
        assert "-" in rendered

    def test_print_method(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        panel.add_commit(iteration=1, message="Test commit")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        panel.print(console)
        rendered = output.getvalue()

        assert "Test commit" in rendered

    def test_truncate_message_short(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        assert panel._truncate_message("Short") == "Short"

    def test_truncate_message_exact_limit(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        msg = "x" * 50
        assert panel._truncate_message(msg, max_len=50) == msg

    def test_truncate_message_over_limit(self):
        from zoyd.tui.panels import GitCommitLogPanel

        panel = GitCommitLogPanel()
        msg = "x" * 60
        result = panel._truncate_message(msg, max_len=50)
        assert len(result) == 50
        assert result.endswith("...")


class TestCreateGitCommitLogPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import create_git_commit_log_panel

        panel = create_git_commit_log_panel()
        assert panel is not None

    def test_custom_title(self):
        from zoyd.tui.panels import create_git_commit_log_panel

        panel = create_git_commit_log_panel(title="Recent Commits")
        assert panel.title == "Recent Commits"

    def test_custom_max_items(self):
        from zoyd.tui.panels import create_git_commit_log_panel

        panel = create_git_commit_log_panel(max_items=20)
        assert panel.max_items == 20

    def test_returns_git_commit_log_panel_instance(self):
        from zoyd.tui.panels import GitCommitLogPanel, create_git_commit_log_panel

        panel = create_git_commit_log_panel()
        assert isinstance(panel, GitCommitLogPanel)


class TestBlockedTaskPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        assert panel is not None
        assert panel.title == "Task Blocked"

    def test_custom_title(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel(title="Cannot Proceed")
        assert panel.title == "Cannot Proceed"

    def test_show_icon_default(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        assert panel.show_icon is True

    def test_show_icon_disabled(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel(show_icon=False)
        assert panel.show_icon is False

    def test_set_task(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        result = panel.set_task("Add authentication")
        assert result is panel  # Returns self for chaining
        assert panel._task == "Add authentication"

    def test_set_reason(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        result = panel.set_reason("Missing dependencies")
        assert result is panel
        assert panel._reason == "Missing dependencies"

    def test_add_blocker(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        result = panel.add_blocker("Database not configured")
        assert result is panel
        assert len(panel._blockers) == 1
        assert panel._blockers[0] == "Database not configured"

    def test_add_multiple_blockers(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.add_blocker("Blocker 1").add_blocker("Blocker 2").add_blocker("Blocker 3")
        assert len(panel._blockers) == 3

    def test_add_suggestion(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        result = panel.add_suggestion("Install required packages")
        assert result is panel
        assert len(panel._suggestions) == 1
        assert panel._suggestions[0] == "Install required packages"

    def test_add_multiple_suggestions(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.add_suggestion("Suggestion 1").add_suggestion("Suggestion 2")
        assert len(panel._suggestions) == 2

    def test_method_chaining(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.set_task("Task").set_reason("Reason").add_blocker("Blocker").add_suggestion(
            "Suggestion"
        )
        assert panel._task == "Task"
        assert panel._reason == "Reason"
        assert len(panel._blockers) == 1
        assert len(panel._suggestions) == 1

    def test_clear(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.set_task("Task").set_reason("Reason").add_blocker("Blocker").add_suggestion(
            "Suggestion"
        )
        result = panel.clear()
        assert result is panel
        assert panel._task is None
        assert panel._reason is None
        assert len(panel._blockers) == 0
        assert len(panel._suggestions) == 0

    def test_render_returns_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.set_task("Blocked task")
        rendered = panel.render()
        assert isinstance(rendered, Panel)

    def test_render_contains_task(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.set_task("Add user authentication")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Task" in rendered
        assert "Add user authentication" in rendered

    def test_render_contains_reason(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.set_task("Task").set_reason("Missing API keys")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Reason" in rendered
        assert "Missing API keys" in rendered

    def test_render_contains_blockers(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.set_task("Task").add_blocker("Database unavailable").add_blocker(
            "Config missing"
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Blockers" in rendered
        assert "Database unavailable" in rendered
        assert "Config missing" in rendered

    def test_render_contains_suggestions(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.set_task("Task").add_suggestion("Run setup script").add_suggestion(
            "Check documentation"
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Suggestions" in rendered
        assert "Run setup script" in rendered
        assert "Check documentation" in rendered

    def test_render_empty_panel(self):
        from rich.panel import Panel

        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        rendered = panel.render()
        assert isinstance(rendered, Panel)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(rendered)
        text = output.getvalue()

        # Should show default message
        assert "blocked" in text.lower()

    def test_render_full_content(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.set_task("Implement feature X")
        panel.set_reason("Dependency not available")
        panel.add_blocker("Package Y not installed")
        panel.add_blocker("API endpoint down")
        panel.add_suggestion("Install Y with pip")
        panel.add_suggestion("Check network connection")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Implement feature X" in rendered
        assert "Dependency not available" in rendered
        assert "Package Y not installed" in rendered
        assert "API endpoint down" in rendered
        assert "Install Y with pip" in rendered
        assert "Check network connection" in rendered

    def test_render_has_blocked_border_style(self):
        """Verify blocked task panel uses blocked color for border."""
        from zoyd.tui.panels import BlockedTaskPanel
        from zoyd.tui.theme import COLORS

        panel = BlockedTaskPanel()
        panel.set_task("Blocked task")
        rendered = panel.render()

        # Verify border_style is the blocked color
        assert rendered.border_style == COLORS["blocked"]

    def test_print_method(self):
        from zoyd.tui.panels import BlockedTaskPanel

        panel = BlockedTaskPanel()
        panel.set_task("Test blocked task")

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        panel.print(console)
        rendered = output.getvalue()

        assert "Test blocked task" in rendered


class TestCreateBlockedTaskPanel:
    def test_creates_panel(self):
        from zoyd.tui.panels import create_blocked_task_panel

        panel = create_blocked_task_panel("Blocked task")
        assert panel is not None
        assert panel._task == "Blocked task"

    def test_custom_title(self):
        from zoyd.tui.panels import create_blocked_task_panel

        panel = create_blocked_task_panel("Task", title="Cannot Complete")
        assert panel.title == "Cannot Complete"

    def test_with_reason(self):
        from zoyd.tui.panels import create_blocked_task_panel

        panel = create_blocked_task_panel("Task", reason="Missing config")
        assert panel._reason == "Missing config"

    def test_with_blockers(self):
        from zoyd.tui.panels import create_blocked_task_panel

        blockers = ["Blocker A", "Blocker B"]
        panel = create_blocked_task_panel("Task", blockers=blockers)
        assert len(panel._blockers) == 2
        assert panel._blockers[0] == "Blocker A"
        assert panel._blockers[1] == "Blocker B"

    def test_with_suggestions(self):
        from zoyd.tui.panels import create_blocked_task_panel

        suggestions = ["Suggestion 1", "Suggestion 2", "Suggestion 3"]
        panel = create_blocked_task_panel("Task", suggestions=suggestions)
        assert len(panel._suggestions) == 3

    def test_all_options(self):
        from zoyd.tui.panels import create_blocked_task_panel

        panel = create_blocked_task_panel(
            "Add feature X",
            reason="Dependencies missing",
            blockers=["Package A not installed", "Service B down"],
            suggestions=["Install A", "Check network"],
            title="Feature Blocked",
        )
        assert panel.title == "Feature Blocked"
        assert panel._task == "Add feature X"
        assert panel._reason == "Dependencies missing"
        assert len(panel._blockers) == 2
        assert len(panel._suggestions) == 2

    def test_returns_blocked_task_panel_instance(self):
        from zoyd.tui.panels import BlockedTaskPanel, create_blocked_task_panel

        panel = create_blocked_task_panel("Task")
        assert isinstance(panel, BlockedTaskPanel)

    def test_render_factory_created_panel(self):
        from zoyd.tui.panels import create_blocked_task_panel

        panel = create_blocked_task_panel(
            "Deploy to production",
            reason="Tests failing",
            blockers=["Unit tests: 3 failures", "Integration tests: 1 timeout"],
            suggestions=["Fix test_auth.py", "Increase timeout in config"],
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        panel.print(console)
        rendered = output.getvalue()

        assert "Deploy to production" in rendered
        assert "Tests failing" in rendered
        assert "Unit tests: 3 failures" in rendered
        assert "Fix test_auth.py" in rendered
