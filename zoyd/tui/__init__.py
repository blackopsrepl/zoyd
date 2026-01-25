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
from zoyd.tui.panels import StatusBar, OutputPanel, ErrorPanel

# Re-export status rendering
from zoyd.tui.status import render_status

# Re-export progress components
from zoyd.tui.progress import ProgressPanel, CostGauge

# Re-export event system
from zoyd.tui.events import EventType, EventEmitter

# Re-export dashboard
from zoyd.tui.dashboard import Dashboard

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
    "ErrorPanel",
    # Status
    "render_status",
    # Progress
    "ProgressPanel",
    "CostGauge",
    # Events
    "EventType",
    "EventEmitter",
    # Dashboard
    "Dashboard",
]
