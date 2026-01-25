"""Zoyd TUI theme with funereal purple/violet color palette.

Provides a Rich Theme and color constants for consistent styling
across all TUI components.
"""

from rich.style import Style
from rich.theme import Theme

# Funereal purple/violet color palette
# These colors evoke a dark, eldritch atmosphere befitting a mind flayer
COLORS = {
    # Primary palette - deep purples and violets
    "void": "#1a0a2e",  # Deepest background, the abyss
    "shadow": "#2d1b4e",  # Secondary background
    "twilight": "#4a2c7a",  # Borders and separators
    "amethyst": "#7b4fa0",  # Accented elements
    "orchid": "#9b6fc0",  # Interactive elements
    "lavender": "#c9a0dc",  # Highlights and focus
    "mist": "#e8d5f0",  # Text and foreground
    # Accent colors
    "psionic": "#b967ff",  # Bright purple for emphasis
    "tentacle": "#8b5cf6",  # Violet for active states
    "elder": "#6d28d9",  # Deep purple for headers
    # Status colors - muted to fit the theme
    "success": "#7c9a6e",  # Muted green - completed tasks
    "warning": "#c9a227",  # Amber - warnings
    "error": "#a34040",  # Muted red - errors
    "info": "#5b7fa8",  # Muted blue - information
    # Progress states
    "pending": "#6b6b6b",  # Gray - pending tasks
    "active": "#b967ff",  # Psionic purple - in progress
    "complete": "#7c9a6e",  # Success green - done
    "blocked": "#8b4513",  # Brown - blocked tasks
}

# Rich Style objects for common uses
STYLES = {
    # Text styles
    "text": Style(color=COLORS["mist"]),
    "text.dim": Style(color=COLORS["orchid"]),
    "text.bright": Style(color=COLORS["lavender"], bold=True),
    # Headings
    "heading": Style(color=COLORS["psionic"], bold=True),
    "subheading": Style(color=COLORS["tentacle"]),
    # Borders and panels
    "border": Style(color=COLORS["twilight"]),
    "border.focus": Style(color=COLORS["amethyst"]),
    "panel.title": Style(color=COLORS["lavender"], bold=True),
    # Status indicators
    "status.success": Style(color=COLORS["success"], bold=True),
    "status.warning": Style(color=COLORS["warning"]),
    "status.error": Style(color=COLORS["error"], bold=True),
    "status.info": Style(color=COLORS["info"]),
    # Task states
    "task.pending": Style(color=COLORS["pending"]),
    "task.active": Style(color=COLORS["active"], bold=True),
    "task.complete": Style(color=COLORS["complete"]),
    "task.blocked": Style(color=COLORS["blocked"]),
    # Progress
    "progress.bar": Style(color=COLORS["psionic"]),
    "progress.complete": Style(color=COLORS["success"]),
    "progress.remaining": Style(color=COLORS["shadow"]),
    # Cost gauge thresholds
    "cost.low": Style(color=COLORS["success"]),  # Green - under budget
    "cost.medium": Style(color=COLORS["warning"]),  # Yellow - approaching limit
    "cost.high": Style(color=COLORS["error"]),  # Red - near/over budget
    # Code and output
    "code": Style(color=COLORS["lavender"]),
    "output": Style(color=COLORS["mist"]),
    "output.dim": Style(color=COLORS["orchid"], dim=True),
}

# Rich Theme for Console
ZOYD_THEME = Theme(
    {
        # Override Rich defaults with our palette
        "default": COLORS["mist"],
        "dim": f"dim {COLORS['orchid']}",
        "bold": f"bold {COLORS['lavender']}",
        # Standard semantic styles
        "info": COLORS["info"],
        "warning": COLORS["warning"],
        "error": f"bold {COLORS['error']}",
        "success": COLORS["success"],
        # Panel styles
        "panel.border": COLORS["twilight"],
        "panel.title": f"bold {COLORS['lavender']}",
        # Tree styles for task visualization
        "tree": COLORS["twilight"],
        "tree.line": COLORS["twilight"],
        # Progress bar styles
        "bar.back": COLORS["shadow"],
        "bar.complete": COLORS["psionic"],
        "bar.finished": COLORS["success"],
        "bar.pulse": COLORS["tentacle"],
        # Markdown styles
        "markdown.h1": f"bold {COLORS['psionic']}",
        "markdown.h2": f"bold {COLORS['tentacle']}",
        "markdown.h3": f"bold {COLORS['amethyst']}",
        "markdown.code": COLORS["lavender"],
        "markdown.code_block": COLORS["mist"],
        "markdown.link": f"underline {COLORS['orchid']}",
        # Table styles
        "table.header": f"bold {COLORS['lavender']}",
        "table.border": COLORS["twilight"],
        # Custom zoyd styles
        "zoyd.banner": f"bold {COLORS['psionic']}",
        "zoyd.iteration": COLORS["tentacle"],
        "zoyd.task.pending": COLORS["pending"],
        "zoyd.task.active": f"bold {COLORS['active']}",
        "zoyd.task.complete": COLORS["complete"],
        "zoyd.task.blocked": COLORS["blocked"],
        "zoyd.cost.low": COLORS["success"],
        "zoyd.cost.medium": COLORS["warning"],
        "zoyd.cost.high": COLORS["error"],
        "zoyd.spinner": COLORS["psionic"],
    }
)


def get_cost_style(current: float, max_cost: float) -> str:
    """Return the appropriate style name for cost display based on usage.

    Args:
        current: Current cost in USD
        max_cost: Maximum cost limit in USD

    Returns:
        Style name: 'zoyd.cost.low', 'zoyd.cost.medium', or 'zoyd.cost.high'
    """
    if max_cost <= 0:
        return "zoyd.cost.low"

    ratio = current / max_cost
    if ratio < 0.5:
        return "zoyd.cost.low"
    elif ratio < 0.8:
        return "zoyd.cost.medium"
    else:
        return "zoyd.cost.high"


def get_task_style(complete: bool, active: bool = False, blocked: bool = False) -> str:
    """Return the appropriate style name for a task based on its state.

    Args:
        complete: Whether the task is complete
        active: Whether the task is currently being worked on
        blocked: Whether the task is blocked

    Returns:
        Style name for the task state
    """
    if blocked:
        return "zoyd.task.blocked"
    if complete:
        return "zoyd.task.complete"
    if active:
        return "zoyd.task.active"
    return "zoyd.task.pending"
