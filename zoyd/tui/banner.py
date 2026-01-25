"""Zoyd TUI banner with mind flayer ASCII art.

Provides full and compact ASCII art banners for the zoyd startup display.
The mind flayer theme evokes an eldritch, psionic presence befitting
an autonomous AI that consumes PRDs and outputs completed tasks.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from zoyd.tui.theme import COLORS

# Full mind flayer ASCII art for terminals >= 80 columns
# Features: tentacled face, psionic aura, "ZOYD" title
MIND_FLAYER_FULL = r"""
          ████████████████████████
        ██░░░░░░░░░░░░░░░░░░░░░░░░██
      ██░░██████████████████████░░░░██
    ██░░██                      ██░░░░██
    ██░░██   ██████  ██████     ██░░░░██
    ██░░██   ██  ██  ██  ██     ██░░░░██
    ██░░██   ██████  ██████     ██░░░░██
    ██░░██                      ██░░░░██
    ██░░████████████████████████░░░░░░██
      ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
        ██████░░██░░██░░██░░██████
              ██░░██░░██░░██
              ██░░██░░██░░██
              ██░░██░░██░░██
               ▀▀  ▀▀  ▀▀

    ███████╗ ██████╗ ██╗   ██╗██████╗
    ╚══███╔╝██╔═══██╗╚██╗ ██╔╝██╔══██╗
      ███╔╝ ██║   ██║ ╚████╔╝ ██║  ██║
     ███╔╝  ██║   ██║  ╚██╔╝  ██║  ██║
    ███████╗╚██████╔╝   ██║   ██████╔╝
    ╚══════╝ ╚═════╝    ╚═╝   ╚═════╝

      A U T O N O M O U S   L O O P
"""

# Compact mind flayer ASCII art for narrow terminals (< 60 columns)
MIND_FLAYER_COMPACT = r"""
      ▄▄████████▄▄
    ▄█░░░░░░░░░░░░█▄
   █░░██████████░░░░█
   █░░██  ▄▄  ██░░░░█
   █░░██████████░░░░█
    █░░░░░░░░░░░░░░█
     ██░░██░░██░░██
       ▀▀  ▀▀  ▀▀

  ╔═══════════════╗
  ║    Z O Y D    ║
  ╚═══════════════╝
"""


def print_banner(
    console: Console | None = None,
    compact: bool = False,
    title: str | None = None,
    subtitle: str | None = None,
) -> None:
    """Print the zoyd banner with optional title and subtitle.

    Args:
        console: Rich Console to use for output. If None, creates a new one.
        compact: Use compact banner for narrow terminals.
        title: Optional title to display below the banner.
        subtitle: Optional subtitle to display below the title.
    """
    if console is None:
        from zoyd.tui.console import get_console

        console = get_console()

    # Select appropriate banner based on compact flag or terminal width
    if compact or (console.width is not None and console.width < 60):
        art = MIND_FLAYER_COMPACT
    else:
        art = MIND_FLAYER_FULL

    # Build the banner text with styling
    banner_text = Text()

    # Add the ASCII art with psionic purple coloring
    for line in art.strip().split("\n"):
        banner_text.append(line + "\n", style=f"bold {COLORS['psionic']}")

    # Add title if provided
    if title:
        banner_text.append("\n")
        banner_text.append(f"  {title}\n", style=f"bold {COLORS['lavender']}")

    # Add subtitle if provided
    if subtitle:
        banner_text.append(f"  {subtitle}\n", style=f"{COLORS['orchid']}")

    # Create a panel with themed border
    panel = Panel(
        banner_text,
        border_style=COLORS["twilight"],
        padding=(0, 2),
    )

    console.print(panel)


def get_banner_text(compact: bool = False) -> str:
    """Get the raw banner ASCII art as a string.

    Args:
        compact: Return compact version if True.

    Returns:
        The ASCII art string.
    """
    return MIND_FLAYER_COMPACT if compact else MIND_FLAYER_FULL
