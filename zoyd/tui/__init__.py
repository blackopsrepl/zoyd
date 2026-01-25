"""Zoyd TUI components using Rich library.

This module provides a themed terminal interface for zoyd with:
- Funereal purple/violet color palette
- Mind flayer ASCII art banners
- Task tree visualization
- Status panels and progress indicators
- Live dashboard for real-time updates
"""

# Re-export theme components
from zoyd.tui.theme import ZOYD_THEME, COLORS

# Re-export console singleton
from zoyd.tui.console import console, get_console

# Re-export banner components
from zoyd.tui.banner import print_banner, MIND_FLAYER_FULL, MIND_FLAYER_COMPACT

# Re-export task tree visualization
from zoyd.tui.task_tree import render_task_tree

# Re-export panel components
from zoyd.tui.panels import (
    StatusBar,
    OutputPanel,
    ClaudeOutputPanel,
    ErrorPanel,
    WarningPanel,
    create_status_bar,
    create_output_panel,
    create_claude_output_panel,
    create_error_panel,
    create_warning_panel,
)

# Re-export status rendering
from zoyd.tui.status import render_status, print_status, get_status_summary

# Re-export progress components
from zoyd.tui.progress import (
    ProgressPanel,
    CostGauge,
    create_progress_panel,
    create_cost_gauge,
)

# Re-export spinner components
from zoyd.tui.spinners import (
    MindFlayerSpinner,
    SPINNER_DEFS,
    DEFAULT_SPINNER,
    create_spinner,
    get_spinner_names,
    get_spinner_frames,
    get_spinner_interval,
)

# Re-export live display components
from zoyd.tui.live import LiveDisplay, create_live_display

# Re-export event system
from zoyd.tui.events import (
    EventType,
    EventEmitter,
    Event,
    EventHandler,
    create_event_emitter,
)

# Dashboard components
from zoyd.tui.dashboard import Dashboard, DashboardState, create_dashboard

__all__ = [
    # Theme
    "ZOYD_THEME",
    "COLORS",
    # Console
    "console",
    "get_console",
    # Banner
    "print_banner",
    "MIND_FLAYER_FULL",
    "MIND_FLAYER_COMPACT",
    # Task tree
    "render_task_tree",
    # Panels
    "StatusBar",
    "OutputPanel",
    "ClaudeOutputPanel",
    "ErrorPanel",
    "WarningPanel",
    "create_status_bar",
    "create_output_panel",
    "create_claude_output_panel",
    "create_error_panel",
    "create_warning_panel",
    # Status rendering
    "render_status",
    "print_status",
    "get_status_summary",
    # Progress components
    "ProgressPanel",
    "CostGauge",
    "create_progress_panel",
    "create_cost_gauge",
    # Live display
    "LiveDisplay",
    "create_live_display",
    # Spinner components
    "MindFlayerSpinner",
    "SPINNER_DEFS",
    "DEFAULT_SPINNER",
    "create_spinner",
    "get_spinner_names",
    "get_spinner_frames",
    "get_spinner_interval",
    # Event system
    "EventType",
    "EventEmitter",
    "Event",
    "EventHandler",
    "create_event_emitter",
    # Dashboard
    "Dashboard",
    "DashboardState",
    "create_dashboard",
]
