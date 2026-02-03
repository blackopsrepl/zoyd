"""Panel components for the Zoyd TUI.

This package provides reusable panel components for displaying status, output, 
errors, and other UI elements in the terminal interface.

Panels are organized by functionality:
- core: Basic content and status panels
- alerts: Warning and error panels  
- data_display: Table-based data panels
- specialized: Complex specialized panels
- factories: Factory functions for creating panels
"""

from .core import ClaudeOutputPanel, OutputPanel, StatusBar
from .alerts import ErrorPanel, WarningPanel
from .data_display import GitCommitLogPanel, IterationHistoryPanel
from .specialized import BlockedTaskPanel

# Import factory functions to make them available at package level
from .factories import (
    create_blocked_task_panel,
    create_claude_output_panel,
    create_error_panel,
    create_git_commit_log_panel,
    create_iteration_history_panel,
    create_output_panel,
    create_status_bar,
    create_warning_panel,
)

__all__ = [
    # Core panels
    "StatusBar",
    "OutputPanel", 
    "ClaudeOutputPanel",
    # Alert panels
    "WarningPanel",
    "ErrorPanel",
    # Data display panels
    "IterationHistoryPanel",
    "GitCommitLogPanel",
    # Specialized panels
    "BlockedTaskPanel",
    # Factory functions
    "create_status_bar",
    "create_output_panel",
    "create_claude_output_panel",
    "create_warning_panel",
    "create_error_panel",
    "create_iteration_history_panel",
    "create_git_commit_log_panel",
    "create_blocked_task_panel",
]