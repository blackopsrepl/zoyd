"""Tests for TUI progress module."""

import pytest

# Skip all tests if rich is not installed
rich = pytest.importorskip("rich")

from io import StringIO
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.text import Text


class TestProgressPanel:
    def test_creates_progress_panel(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        assert panel is not None
        assert panel.title == "Progress"

    def test_custom_title(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel(title="My Progress")
        assert panel.title == "My Progress"

    def test_set_tasks(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        result = panel.set_tasks(5, 10)
        assert result is panel  # Returns self for chaining
        assert panel._task_completed == 5
        assert panel._task_total == 10

    def test_set_iteration(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        result = panel.set_iteration(3, 10)
        assert result is panel
        assert panel._iteration_current == 3
        assert panel._iteration_max == 10

    def test_set_iteration_no_max(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_iteration(5)
        assert panel._iteration_current == 5
        assert panel._iteration_max is None

    def test_set_cost(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        result = panel.set_cost(1.5, 10.0)
        assert result is panel
        assert panel._cost_current == 1.5
        assert panel._cost_max == 10.0

    def test_set_cost_no_max(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_cost(2.0)
        assert panel._cost_current == 2.0
        assert panel._cost_max is None

    def test_method_chaining(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        result = (
            panel.set_tasks(5, 10)
            .set_iteration(3, 10)
            .set_cost(1.5, 10.0)
        )
        assert result is panel
        assert panel._task_completed == 5
        assert panel._iteration_current == 3
        assert panel._cost_current == 1.5

    def test_create_task_progress_no_tasks(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_tasks(0, 0)
        result = panel._create_task_progress()
        assert isinstance(result, Text)
        assert "No tasks" in result.plain

    def test_create_task_progress_with_tasks(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_tasks(5, 10)
        result = panel._create_task_progress()
        assert isinstance(result, Progress)

    def test_create_iteration_progress_no_max(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_iteration(5)
        result = panel._create_iteration_progress()
        assert isinstance(result, Text)
        assert "5" in result.plain

    def test_create_iteration_progress_with_max(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_iteration(3, 10)
        result = panel._create_iteration_progress()
        assert isinstance(result, Progress)

    def test_create_cost_gauge_disabled(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        # Neither cost_current nor cost_max set
        result = panel._create_cost_gauge()
        assert isinstance(result, Text)
        assert "disabled" in result.plain

    def test_create_cost_gauge_no_limit(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_cost(1.5)
        result = panel._create_cost_gauge()
        assert isinstance(result, Text)
        assert "$1.5" in result.plain

    def test_create_cost_gauge_with_limit(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_cost(1.5, 10.0)
        result = panel._create_cost_gauge()
        assert isinstance(result, Progress)

    def test_render_returns_panel(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_tasks(5, 10)
        rendered = panel.render()
        assert isinstance(rendered, Panel)

    def test_render_contains_task_info(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_tasks(5, 10)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Tasks" in rendered
        assert "5/10" in rendered

    def test_render_contains_iteration_info(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_tasks(0, 0)
        panel.set_iteration(3, 10)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "3/10" in rendered

    def test_render_contains_cost_info(self):
        from zoyd.tui.console import create_console
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_tasks(0, 0)
        panel.set_cost(1.5, 10.0)

        output = StringIO()
        console = create_console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        assert "Cost" in rendered
        assert "$1.5" in rendered

    def test_render_hides_cost_when_disabled(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_tasks(5, 10)
        panel.set_iteration(3, 10)
        # Don't set cost

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        console.print(panel.render())
        rendered = output.getvalue()

        # Should not show cost section when disabled
        assert "Cost tracking: disabled" not in rendered

    def test_print_method(self):
        from zoyd.tui.progress import ProgressPanel

        panel = ProgressPanel()
        panel.set_tasks(5, 10)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        panel.print(console)
        rendered = output.getvalue()

        assert "Tasks" in rendered


class TestCostGauge:
    def test_creates_cost_gauge(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge()
        assert gauge is not None
        assert gauge.current == 0.0
        assert gauge.max_cost is None

    def test_with_values(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=1.5, max_cost=10.0)
        assert gauge.current == 1.5
        assert gauge.max_cost == 10.0

    def test_show_percentage_default(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge()
        assert gauge.show_percentage is True

    def test_show_percentage_disabled(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(show_percentage=False)
        assert gauge.show_percentage is False

    def test_show_values_default(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge()
        assert gauge.show_values is True

    def test_show_values_disabled(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(show_values=False)
        assert gauge.show_values is False

    def test_bar_width_default(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge()
        assert gauge.bar_width == 30

    def test_bar_width_custom(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(bar_width=50)
        assert gauge.bar_width == 50

    def test_update(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge()
        result = gauge.update(2.5, 10.0)
        assert result is gauge
        assert gauge.current == 2.5
        assert gauge.max_cost == 10.0

    def test_update_current_only(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(max_cost=10.0)
        gauge.update(2.5)
        assert gauge.current == 2.5
        assert gauge.max_cost == 10.0  # Unchanged

    def test_get_style_low(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=1.0, max_cost=10.0)  # 10%
        assert gauge.get_style() == "zoyd.cost.low"

    def test_get_style_medium(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=6.0, max_cost=10.0)  # 60%
        assert gauge.get_style() == "zoyd.cost.medium"

    def test_get_style_high(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=9.0, max_cost=10.0)  # 90%
        assert gauge.get_style() == "zoyd.cost.high"

    def test_get_style_no_max(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=1.0)
        assert gauge.get_style() == "zoyd.cost.low"

    def test_get_style_zero_max(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=1.0, max_cost=0)
        assert gauge.get_style() == "zoyd.cost.low"

    def test_render_no_max(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=1.5)
        result = gauge.render()
        assert isinstance(result, Text)
        assert "$1.5" in result.plain

    def test_render_with_max(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=1.5, max_cost=10.0)
        result = gauge.render()
        assert isinstance(result, Progress)

    def test_render_compact_no_max(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=1.5)
        result = gauge.render_compact()
        assert isinstance(result, Text)
        assert "$1.5" in result.plain

    def test_render_compact_with_max(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=5.0, max_cost=10.0)
        result = gauge.render_compact()
        assert isinstance(result, Text)
        assert "$5.0" in result.plain
        assert "$10.00" in result.plain
        assert "50%" in result.plain

    def test_render_compact_over_budget(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=15.0, max_cost=10.0)
        result = gauge.render_compact()
        # Should cap at 100%
        assert "100%" in result.plain

    def test_print_method(self):
        from zoyd.tui.progress import CostGauge

        gauge = CostGauge(current=1.5)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        gauge.print(console)
        rendered = output.getvalue()

        assert "$1.5" in rendered


class TestCreateProgressPanel:
    def test_creates_panel(self):
        from zoyd.tui.progress import create_progress_panel

        panel = create_progress_panel()
        assert panel is not None

    def test_with_tasks(self):
        from zoyd.tui.progress import create_progress_panel

        panel = create_progress_panel(task_completed=5, task_total=10)
        assert panel._task_completed == 5
        assert panel._task_total == 10

    def test_with_iteration(self):
        from zoyd.tui.progress import create_progress_panel

        panel = create_progress_panel(iteration=3, max_iterations=10)
        assert panel._iteration_current == 3
        assert panel._iteration_max == 10

    def test_with_cost(self):
        from zoyd.tui.progress import create_progress_panel

        panel = create_progress_panel(cost=1.5, max_cost=10.0)
        assert panel._cost_current == 1.5
        assert panel._cost_max == 10.0

    def test_custom_title(self):
        from zoyd.tui.progress import create_progress_panel

        panel = create_progress_panel(title="Custom Progress")
        assert panel.title == "Custom Progress"

    def test_all_options(self):
        from zoyd.tui.progress import create_progress_panel

        panel = create_progress_panel(
            task_completed=5,
            task_total=10,
            iteration=3,
            max_iterations=10,
            cost=1.5,
            max_cost=10.0,
            title="My Progress",
        )
        assert panel._task_completed == 5
        assert panel._task_total == 10
        assert panel._iteration_current == 3
        assert panel._iteration_max == 10
        assert panel._cost_current == 1.5
        assert panel._cost_max == 10.0
        assert panel.title == "My Progress"


class TestCreateCostGauge:
    def test_creates_gauge(self):
        from zoyd.tui.progress import create_cost_gauge

        gauge = create_cost_gauge()
        assert gauge is not None

    def test_with_values(self):
        from zoyd.tui.progress import create_cost_gauge

        gauge = create_cost_gauge(current=1.5, max_cost=10.0)
        assert gauge.current == 1.5
        assert gauge.max_cost == 10.0

    def test_with_options(self):
        from zoyd.tui.progress import create_cost_gauge

        gauge = create_cost_gauge(
            current=1.5,
            max_cost=10.0,
            show_percentage=False,
            show_values=False,
            bar_width=40,
        )
        assert gauge.show_percentage is False
        assert gauge.show_values is False
        assert gauge.bar_width == 40


class TestModuleExports:
    def test_progress_panel_importable(self):
        from zoyd.tui.progress import ProgressPanel

        assert ProgressPanel is not None

    def test_cost_gauge_importable(self):
        from zoyd.tui.progress import CostGauge

        assert CostGauge is not None

    def test_create_progress_panel_importable(self):
        from zoyd.tui.progress import create_progress_panel

        assert callable(create_progress_panel)

    def test_create_cost_gauge_importable(self):
        from zoyd.tui.progress import create_cost_gauge

        assert callable(create_cost_gauge)

    def test_exports_from_tui_init(self):
        from zoyd.tui import (
            ProgressPanel,
            CostGauge,
            create_progress_panel,
            create_cost_gauge,
        )

        assert ProgressPanel is not None
        assert CostGauge is not None
        assert callable(create_progress_panel)
        assert callable(create_cost_gauge)
