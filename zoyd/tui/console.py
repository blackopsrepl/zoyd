"""Zoyd TUI console singleton with themed output.

Provides a pre-configured Rich Console with the zoyd theme applied.
The singleton pattern ensures consistent styling across all TUI components.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

from rich.console import Console

from zoyd.tui.theme import ZOYD_THEME

if TYPE_CHECKING:
    from rich.theme import Theme

# Module-level singleton instance
_console: Console | None = None


def get_console(
    *,
    file: TextIO | None = None,
    force_terminal: bool | None = None,
    force_interactive: bool | None = None,
    width: int | None = None,
    theme: Theme | None = None,
    _reset: bool = False,
) -> Console:
    """Get or create the themed Console singleton.

    On first call, creates a Console with the zoyd theme applied.
    Subsequent calls return the same instance unless _reset=True.

    Args:
        file: File to write output to. Defaults to sys.stdout.
        force_terminal: Force terminal mode even if not a TTY.
        force_interactive: Force interactive mode.
        width: Override detected terminal width.
        theme: Custom theme to use instead of ZOYD_THEME.
        _reset: If True, create a new Console instance (for testing).

    Returns:
        The themed Console instance.
    """
    global _console

    if _console is None or _reset:
        _console = Console(
            file=file or sys.stdout,
            force_terminal=force_terminal,
            force_interactive=force_interactive,
            width=width,
            theme=theme or ZOYD_THEME,
            highlight=True,
            markup=True,
            emoji=False,  # Disable emojis as per project preferences
        )

    return _console


def reset_console() -> None:
    """Reset the console singleton.

    This is primarily useful for testing to ensure a fresh console
    is created between tests.
    """
    global _console
    _console = None


def create_console(
    *,
    file: TextIO | None = None,
    force_terminal: bool | None = None,
    force_interactive: bool | None = None,
    width: int | None = None,
    theme: Theme | None = None,
    record: bool = False,
) -> Console:
    """Create a new Console instance (not the singleton).

    Use this when you need a separate console, e.g., for recording
    output or writing to a different file.

    Args:
        file: File to write output to. Defaults to sys.stdout.
        force_terminal: Force terminal mode even if not a TTY.
        force_interactive: Force interactive mode.
        width: Override detected terminal width.
        theme: Custom theme to use instead of ZOYD_THEME.
        record: Enable recording for export (see Console.export_* methods).

    Returns:
        A new Console instance with the zoyd theme.
    """
    return Console(
        file=file or sys.stdout,
        force_terminal=force_terminal,
        force_interactive=force_interactive,
        width=width,
        theme=theme or ZOYD_THEME,
        highlight=True,
        markup=True,
        emoji=False,
        record=record,
    )


# Pre-create the singleton for convenient import
# Use get_console() if you need to customize options
console = get_console()
