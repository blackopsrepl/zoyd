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
 │  Loop until complete.         │     ⣿⣿⣿⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⣿⣿⣿
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


def get_versioned_banner(version: str) -> str:
    """Create a banner with version string after the second box.

    Inserts ``v{version}`` on the line after the second box's closing
    border (``└───...┘``), left-aligned under the boxes.

    Args:
        version: Version string, e.g. ``"0.3.1"``.

    Returns:
        The banner string with the version line inserted.
    """
    lines = ZOYD_BANNER.split("\n")
    # The second box uses └───...┘ (the first box uses ╚═══...╝).
    # Find the └ line and insert version after it.
    insert_index = None
    for i, line in enumerate(lines):
        if "└" in line:
            insert_index = i + 1
            break
    if insert_index is None:
        # Fallback: append version at the end
        return ZOYD_BANNER.rstrip("\n") + f"\n v{version}\n"
    version_line = f" v{version}"
    lines.insert(insert_index, version_line)
    return "\n".join(lines)


def get_banner_text() -> str:
    """Get the raw banner ASCII art as a string.

    Returns:
        The ASCII art string.
    """
    return ZOYD_BANNER


def render_banner_styled(version: str, rabid: bool = False) -> Text:
    """Render the banner with per-character styling.

    When ``rabid=False``, applies uniform purple styling (current behavior).
    When ``rabid=True``, transforms the mind flayer's eye into a fiery
    "Eye of Sauron" appearance with gradient coloring.

    The eye region spans columns 44-57 on lines 4-8 (0-indexed) of the
    banner art. Gradient coloring is applied based on distance from the
    eye center (column 50, line 6).

    Args:
        version: Version string, e.g. ``"0.3.1"``.
        rabid: If True, apply Sauron eye coloring; otherwise purple.

    Returns:
        Rich Text object with per-character styling applied.
    """
    versioned = get_versioned_banner(version)
    lines = versioned.strip().split("\n")
    banner_text = Text()

    if not rabid:
        # Standard purple styling
        for i, line in enumerate(lines):
            suffix = "\n" if i < len(lines) - 1 else ""
            banner_text.append(line + suffix, style=f"bold {COLORS['psionic']}")
        return banner_text

    # Rabid mode: Eye of Sauron gradient
    # Eye socket opening: columns 44-57, lines 4-8 (0-indexed)
    # Eye center: column 50, line 6 (center of the pupil slit)
    # Pupil slit (⣿ characters): line 7, cols 47-53
    eye_col_start = 44
    eye_col_end = 57
    eye_line_start = 4
    eye_line_end = 8
    eye_center_col = 50
    eye_center_line = 6

    # Color palette for the gradient (inner to outer)
    sauron_colors = [
        COLORS["sauron_core"],   # Yellow - hot center (pupil)
        COLORS["sauron_inner"],  # Bright orange - inner fire (iris)
        COLORS["sauron_mid"],    # Orange-red - middle ring
        COLORS["sauron_outer"],  # Dark red - outer glow
    ]

    for line_idx, line in enumerate(lines):
        suffix = "\n" if line_idx < len(lines) - 1 else ""

        # Check if this line is in the eye region
        if eye_line_start <= line_idx <= eye_line_end:
            # Process character by character
            for col_idx, char in enumerate(line):
                # Check if this column is in the eye region
                if eye_col_start <= col_idx <= eye_col_end:
                    # Calculate distance from eye center
                    col_dist = abs(col_idx - eye_center_col)
                    line_dist = abs(line_idx - eye_center_line)
                    # Weighted distance (horizontal eye shape - cols matter more)
                    distance = (col_dist * 0.7) + (line_dist * 1.8)

                    # Map distance to color index
                    # Thresholds tuned for the eye geometry:
                    # - 0-2: core (yellow) - the very center
                    # - 2-4: inner (bright orange) - iris center
                    # - 4-6: mid (orange-red) - iris edge
                    # - 6+: outer (dark red) - socket edge
                    if distance < 2:
                        color = sauron_colors[0]  # core (yellow)
                    elif distance < 4:
                        color = sauron_colors[1]  # inner (bright orange)
                    elif distance < 6:
                        color = sauron_colors[2]  # mid (orange-red)
                    else:
                        color = sauron_colors[3]  # outer (dark red)

                    banner_text.append(char, style=f"bold {color}")
                else:
                    # Outside eye region: use purple
                    banner_text.append(char, style=f"bold {COLORS['psionic']}")
            banner_text.append(suffix, style=f"bold {COLORS['psionic']}")
        else:
            # Line outside eye region: all purple
            banner_text.append(line + suffix, style=f"bold {COLORS['psionic']}")

    return banner_text
