"""Zoyd TUI banner with ZOYD logo and mind flayer braille art.

Provides a combined ASCII art banner for the zoyd startup display.
The banner shows ZOYD logo on the left and a mind flayer rendered
in braille characters on the right. The mind flayer theme evokes
an eldritch, psionic presence befitting an autonomous AI that
consumes PRDs and outputs completed tasks.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from zoyd.tui.theme import COLORS

# Combined banner with ZOYD logo on left and mind flayer braille art on right
# The mind flayer is rendered using Unicode braille characters (U+2800-U+28FF)
# This creates a high-resolution illithid/mind flayer appearance
ZOYD_BANNER = r"""
 ███████╗ ██████╗ ██╗   ██╗██████╗        ⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀
 ╚══███╔╝██╔═══██╗╚██╗ ██╔╝██╔══██╗     ⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦
   ███╔╝ ██║   ██║ ╚████╔╝ ██║  ██║    ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
  ███╔╝  ██║   ██║  ╚██╔╝  ██║  ██║   ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
 ███████╗╚██████╔╝   ██║   ██████╔╝   ⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠛⠛⠛⠛⠛⠛⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿
 ╚══════╝ ╚═════╝    ╚═╝   ╚═════╝    ⣿⣿⣿⣿⣿⣿⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿
                                      ⣿⣿⣿⣿⣿⣿⡏⠀⠀⢀⣤⣤⣤⣤⣤⣤⡀⠀⠀⢹⣿⣿⣿⣿⣿⣿⣿
 ╔═══════════════════════════════╗    ⣿⣿⣿⣿⣿⣿⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿
 ║   A L I E N  A I              ║    ⣿⣿⣿⣿⣿⣿⡀⠀⠀⠻⠿⠿⠿⠿⠿⠟⠀⠀⠀⣸⣿⣿⣿⣿⣿⣿⣿
 ║         M I N D  F L A Y E R  ║     ⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿
 ╚═══════════════════════════════╝      ⣿⣿⣿⣿⣿⣿⣿⣷⣶⣤⣤⣤⣤⣶⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿
                                        ⣿⣿⣿⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⣿⣿⣿
 ┌───────────────────────────────┐      ⣿⣿⣿⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⣿⣿⣿
 │  The autonomous loop agent.   │     ⣿⣿⣿⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⣿⣿⣿
 │  Guada KKKhu Bhebe!!!         │     ⣿⣿⣿⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⣿⣿⣿
 └───────────────────────────────┘      ⣿⣿⣿⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⣿⣿⣿
                                        ⣿⣿⣿⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⣿⣿⣿
                                        ⠹⠿⠃⠀⠀⠹⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠀⠀⠻⠿⠇
                                         ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                          ⠿⠿⠿⠿   ⠿⠿⠿⠿   ⠿⠿⠿⠿
"""


def print_banner(
    console: Console | None = None,
    title: str | None = None,
    subtitle: str | None = None,
) -> None:
    """Print the zoyd banner with optional title and subtitle.

    Args:
        console: Rich Console to use for output. If None, creates a new one.
        title: Optional title to display below the banner.
        subtitle: Optional subtitle to display below the title.
    """
    if console is None:
        from zoyd.tui.console import get_console

        console = get_console()

    # Build the banner text with styling
    banner_text = Text()

    # Add the ASCII art with psionic purple coloring
    for line in ZOYD_BANNER.strip().split("\n"):
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


def get_banner_text() -> str:
    """Get the raw banner ASCII art as a string.

    Returns:
        The ASCII art string.
    """
    return ZOYD_BANNER
