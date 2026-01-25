"""Zoyd TUI Rich traceback handler for better exception display.

Provides themed exception tracebacks using Rich's traceback handler.
The handler renders exceptions with syntax highlighting and local variables
in the zoyd color palette.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.traceback import install as rich_install

from zoyd.tui.console import get_console
from zoyd.tui.theme import COLORS

if TYPE_CHECKING:
    from rich.console import Console


# Default configuration for traceback display
DEFAULT_SHOW_LOCALS = False  # Don't show locals by default (can be verbose)
DEFAULT_SUPPRESS = []  # Modules to suppress from tracebacks
DEFAULT_MAX_FRAMES = 20  # Maximum number of frames to show
DEFAULT_WIDTH = None  # Use terminal width
DEFAULT_EXTRA_LINES = 3  # Lines of code context around the error
DEFAULT_WORD_WRAP = False  # Don't wrap long lines


def install_traceback_handler(
    *,
    console: Console | None = None,
    show_locals: bool = DEFAULT_SHOW_LOCALS,
    suppress: list[str] | None = None,
    max_frames: int = DEFAULT_MAX_FRAMES,
    width: int | None = DEFAULT_WIDTH,
    extra_lines: int = DEFAULT_EXTRA_LINES,
    word_wrap: bool = DEFAULT_WORD_WRAP,
    theme: str | None = None,
) -> None:
    """Install Rich traceback handler for better exception display.

    This replaces Python's default traceback display with Rich's themed
    version, using the zoyd color palette for consistent styling.

    Args:
        console: Console to use for output. Defaults to zoyd themed console.
        show_locals: Show local variables in tracebacks. Defaults to False.
        suppress: List of module names to suppress from tracebacks.
        max_frames: Maximum number of frames to display. Defaults to 20.
        width: Width of the traceback display. Defaults to terminal width.
        extra_lines: Lines of code context around the error. Defaults to 3.
        word_wrap: Whether to wrap long lines. Defaults to False.
        theme: Syntax highlighting theme. Defaults to "dracula" (matches output panel).

    Example:
        >>> from zoyd.tui.traceback import install_traceback_handler
        >>> install_traceback_handler()  # Install with defaults
        >>> install_traceback_handler(show_locals=True)  # Show local variables
    """
    if console is None:
        console = get_console()

    if suppress is None:
        suppress = DEFAULT_SUPPRESS.copy()

    # Use dracula theme to match the code highlighting in output panel
    if theme is None:
        theme = "dracula"

    rich_install(
        console=console,
        show_locals=show_locals,
        suppress=suppress,
        max_frames=max_frames,
        width=width,
        extra_lines=extra_lines,
        word_wrap=word_wrap,
        theme=theme,
    )


def get_traceback_console() -> Console:
    """Get a Console configured for traceback display.

    Returns a Console with settings optimized for traceback rendering,
    using the zoyd theme.

    Returns:
        Console configured for tracebacks.
    """
    return get_console()


# Keep track of whether we've installed the handler
_installed = False


def is_traceback_installed() -> bool:
    """Check if the Rich traceback handler has been installed.

    Returns:
        True if install_traceback_handler() has been called.
    """
    return _installed


def ensure_traceback_installed(
    **kwargs,
) -> None:
    """Install traceback handler if not already installed.

    This is safe to call multiple times - it will only install once.
    All keyword arguments are passed to install_traceback_handler().

    Example:
        >>> from zoyd.tui.traceback import ensure_traceback_installed
        >>> ensure_traceback_installed()  # First call installs
        >>> ensure_traceback_installed()  # Second call is a no-op
    """
    global _installed
    if not _installed:
        install_traceback_handler(**kwargs)
        _installed = True


def reset_traceback_installed() -> None:
    """Reset the installation flag (for testing purposes)."""
    global _installed
    _installed = False
