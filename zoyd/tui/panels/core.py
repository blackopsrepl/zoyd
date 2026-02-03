"""Core panel components for the Zoyd TUI.

Provides the fundamental panel components for displaying status, output, and
Claude-specific content in the terminal interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from zoyd.tui.theme import COLORS

if TYPE_CHECKING:
    from rich.console import Console, RenderableType


class StatusBar:
    """A horizontal status bar showing key-value pairs.

    Displays information like PRD path, iteration count, model, and cost
    in a compact horizontal format.
    """

    def __init__(self, title: str = "Status") -> None:
        """Initialize the status bar.

        Args:
            title: Title for the status bar panel.
        """
        self.title = title
        self._items: list[tuple[str, str, str | None]] = []

    def add_item(self, label: str, value: str, style: str | None = None) -> StatusBar:
        """Add an item to the status bar.

        Args:
            label: The label for the item.
            value: The value to display.
            style: Optional Rich style to apply to the value.

        Returns:
            Self for method chaining.
        """
        self._items.append((label, value, style))
        return self

    def clear(self) -> StatusBar:
        """Clear all items from the status bar.

        Returns:
            Self for method chaining.
        """
        self._items = []
        return self

    def render(self) -> Panel:
        """Render the status bar as a Rich Panel.

        Returns:
            A Rich Panel containing the status bar.
        """
        table = Table(
            show_header=False,
            show_edge=False,
            box=None,
            padding=(0, 2),
            expand=True,
        )

        # Add columns for each item
        for _ in self._items:
            table.add_column(ratio=1)

        # Add a single row with all items
        cells = []
        for label, value, style in self._items:
            if style:
                cell = Text.assemble(
                    (f"{label}: ", "dim"),
                    (value, style),
                )
            else:
                cell = Text.assemble(
                    (f"{label}: ", "dim"),
                    (value, ""),
                )
            cells.append(cell)

        if cells:
            table.add_row(*cells)

        return Panel(
            table,
            title=f"[panel.title]{self.title}[/]",
            border_style=COLORS["twilight"],
            padding=(0, 1),
        )

    def print(self, console: Console) -> None:
        """Print the status bar to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


class OutputPanel:
    """A panel for displaying Claude output or other content.

    Supports plain text, markdown, and other Rich renderables.
    """

    def __init__(
        self,
        title: str = "Output",
        *,
        subtitle: str | None = None,
        max_height: int | None = None,
    ) -> None:
        """Initialize the output panel.

        Args:
            title: Title for the panel.
            subtitle: Optional subtitle shown in the panel border.
            max_height: Maximum height in lines (not yet enforced).
        """
        self.title = title
        self.subtitle = subtitle
        self.max_height = max_height
        self._content: RenderableType | None = None

    def set_content(self, content: RenderableType) -> OutputPanel:
        """Set the content to display in the panel.

        Args:
            content: Any Rich renderable (text, markdown, table, etc.).

        Returns:
            Self for method chaining.
        """
        self._content = content
        return self

    def clear(self) -> OutputPanel:
        """Clear the panel content.

        Returns:
            Self for method chaining.
        """
        self._content = None
        return self

    def render(self) -> Panel:
        """Render the output panel.

        Returns:
            A Rich Panel containing the content.
        """
        content = self._content if self._content is not None else ""
        return Panel(
            content,
            title=f"[panel.title]{self.title}[/]",
            subtitle=f"[dim]{self.subtitle}[/]" if self.subtitle else None,
            border_style=COLORS["twilight"],
            padding=(1, 2),
        )

    def print(self, console: Console) -> None:
        """Print the output panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


class ClaudeOutputPanel:
    """A panel for displaying Claude output with Markdown rendering.

    Renders Claude's markdown output with proper styling for headers,
    code blocks, lists, and other markdown elements.

    Code blocks are syntax highlighted using the dracula theme by default.
    """

    # Default code theme for syntax highlighting
    DEFAULT_CODE_THEME = "dracula"

    def __init__(
        self,
        title: str = "Claude Output",
        *,
        subtitle: str | None = None,
        max_height: int | None = None,
        code_theme: str = "dracula",
    ) -> None:
        """Initialize the Claude output panel.

        Args:
            title: Title for the panel.
            subtitle: Optional subtitle shown in the panel border.
            max_height: Maximum height in lines (not yet enforced).
            code_theme: Pygments theme for syntax highlighting (default: dracula).
        """
        self.title = title
        self.subtitle = subtitle
        self.max_height = max_height
        self._content: str = ""
        self._use_markdown: bool = True
        self._code_theme: str = code_theme

    def set_content(self, content: str) -> ClaudeOutputPanel:
        """Set the content to display in the panel.

        Args:
            content: Markdown text from Claude's output.

        Returns:
            Self for method chaining.
        """
        self._content = content
        return self

    def set_markdown(self, use_markdown: bool) -> ClaudeOutputPanel:
        """Enable or disable markdown rendering.

        Args:
            use_markdown: Whether to render content as markdown.

        Returns:
            Self for method chaining.
        """
        self._use_markdown = use_markdown
        return self

    def set_code_theme(self, theme: str) -> ClaudeOutputPanel:
        """Set the syntax highlighting theme for code blocks.

        Args:
            theme: Pygments theme name (e.g., 'dracula', 'monokai', 'github-dark').

        Returns:
            Self for method chaining.
        """
        self._code_theme = theme
        return self

    def clear(self) -> ClaudeOutputPanel:
        """Clear the panel content.

        Returns:
            Self for method chaining.
        """
        self._content = ""
        return self

    def render(self) -> Panel:
        """Render the Claude output panel with Markdown.

        Code blocks are syntax highlighted using the configured code theme
        (dracula by default).

        Returns:
            A Rich Panel containing the rendered markdown content.
        """
        if self._content:
            if self._use_markdown:
                content: RenderableType = Markdown(
                    self._content,
                    code_theme=self._code_theme,
                )
            else:
                content = Text(self._content)
        else:
            content = Text("Awaiting Claude output...", style="dim")

        return Panel(
            content,
            title=f"[panel.title]{self.title}[/]",
            subtitle=f"[dim]{self.subtitle}[/]" if self.subtitle else None,
            border_style=COLORS["twilight"],
            padding=(1, 2),
        )

    def print(self, console: Console) -> None:
        """Print the Claude output panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())