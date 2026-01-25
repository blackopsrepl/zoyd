"""Custom mind flayer spinners for the Zoyd TUI.

Provides themed spinner animations for Claude invocation:
- tentacles: Writhing tentacles animation
- psionic: Psionic energy pulsing
- void: Void/portal swirling effect
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.spinner import Spinner

from zoyd.tui.theme import COLORS

if TYPE_CHECKING:
    from rich.console import Console, RenderableType

# Custom spinner definitions
# Each spinner is a tuple of (frames, interval_ms)
SPINNER_DEFS = {
    # Tentacles - writhing tentacle animation
    "tentacles": (
        [
            "⁍⁌⁍⁌",
            "⁌⁍⁌⁍",
            "⁍⁍⁌⁌",
            "⁌⁌⁍⁍",
            "⁍⁌⁌⁍",
            "⁌⁍⁍⁌",
        ],
        120,
    ),
    # Psionic - psionic energy pulsing
    "psionic": (
        [
            "◇ ◇ ◇",
            "◆ ◇ ◇",
            "◆ ◆ ◇",
            "◆ ◆ ◆",
            "◇ ◆ ◆",
            "◇ ◇ ◆",
        ],
        100,
    ),
    # Void - swirling void portal
    "void": (
        [
            "○ ○ ○",
            "◐ ○ ○",
            "● ◐ ○",
            "◑ ● ◐",
            "○ ◑ ●",
            "○ ○ ◑",
        ],
        140,
    ),
    # Mind - mind control waves
    "mind": (
        [
            "∿∿∿",
            "≈∿∿",
            "∿≈∿",
            "∿∿≈",
            "≈≈∿",
            "∿≈≈",
            "≈≈≈",
            "∿≈≈",
            "≈∿≈",
            "≈≈∿",
        ],
        90,
    ),
    # Elder - elder sign rotation
    "elder": (
        [
            "⍟",
            "✧",
            "✦",
            "✧",
            "⍟",
            "✦",
        ],
        150,
    ),
}

# Default spinner for Claude invocation
DEFAULT_SPINNER = "psionic"


class MindFlayerSpinner:
    """A themed spinner for showing loading states.

    Wraps Rich's Spinner with custom mind flayer animations
    and zoyd theme styling.
    """

    def __init__(
        self,
        name: str = DEFAULT_SPINNER,
        text: str = "",
        *,
        style: str | None = None,
    ) -> None:
        """Initialize the spinner.

        Args:
            name: Name of the spinner animation (tentacles, psionic, void, mind, elder).
            text: Text to display next to the spinner.
            style: Rich style for the spinner (defaults to zoyd.spinner from theme).
        """
        self.name = name if name in SPINNER_DEFS else DEFAULT_SPINNER
        self.text = text
        self.style = style or "zoyd.spinner"

        # Get spinner definition
        frames, interval = SPINNER_DEFS[self.name]
        self._spinner = Spinner(
            name="dots",  # We'll override frames below
            text=text,
            style=self.style,
        )
        # Override with our custom frames
        self._spinner.spinner_frames = frames
        self._spinner.interval = interval / 1000  # Convert ms to seconds

    def __rich__(self) -> RenderableType:
        """Return the Rich renderable for this spinner.

        Returns:
            The underlying Spinner renderable.
        """
        return self._spinner

    @property
    def spinner(self) -> Spinner:
        """Get the underlying Rich Spinner.

        Returns:
            The Rich Spinner instance.
        """
        return self._spinner

    def update(self, text: str) -> MindFlayerSpinner:
        """Update the spinner text.

        Args:
            text: New text to display.

        Returns:
            Self for method chaining.
        """
        self.text = text
        self._spinner.update(text=text)
        return self


def create_spinner(
    name: str = DEFAULT_SPINNER,
    text: str = "",
    *,
    style: str | None = None,
) -> MindFlayerSpinner:
    """Create a mind flayer spinner.

    Factory function for creating themed spinners.

    Args:
        name: Name of the spinner animation.
        text: Text to display next to the spinner.
        style: Rich style override.

    Returns:
        A configured MindFlayerSpinner instance.
    """
    return MindFlayerSpinner(name=name, text=text, style=style)


def get_spinner_names() -> list[str]:
    """Get the list of available spinner names.

    Returns:
        List of spinner animation names.
    """
    return list(SPINNER_DEFS.keys())


def get_spinner_frames(name: str) -> list[str]:
    """Get the frames for a specific spinner.

    Args:
        name: Name of the spinner.

    Returns:
        List of frame strings, or empty list if not found.
    """
    if name not in SPINNER_DEFS:
        return []
    return SPINNER_DEFS[name][0]


def get_spinner_interval(name: str) -> int:
    """Get the interval for a specific spinner in milliseconds.

    Args:
        name: Name of the spinner.

    Returns:
        Interval in milliseconds, or 0 if not found.
    """
    if name not in SPINNER_DEFS:
        return 0
    return SPINNER_DEFS[name][1]
