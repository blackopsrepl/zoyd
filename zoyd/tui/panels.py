"""Panel components for the Zoyd TUI.

Provides reusable panel components for displaying status, output, and errors
in the terminal interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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


class WarningPanel:
    """A panel for displaying warnings with yellow/amber styling.

    Used for validation warnings, deprecation notices, and non-critical issues.
    """

    def __init__(
        self,
        title: str = "Warning",
        *,
        show_icon: bool = True,
    ) -> None:
        """Initialize the warning panel.

        Args:
            title: Title for the panel.
            show_icon: Whether to show a warning icon in the title.
        """
        self.title = title
        self.show_icon = show_icon
        self._items: list[tuple[str, str | None]] = []

    def add_item(self, message: str, detail: str | None = None) -> WarningPanel:
        """Add a warning item.

        Args:
            message: The warning message.
            detail: Optional detail/context for the warning.

        Returns:
            Self for method chaining.
        """
        self._items.append((message, detail))
        return self

    def clear(self) -> WarningPanel:
        """Clear all warning items.

        Returns:
            Self for method chaining.
        """
        self._items = []
        return self

    def render(self) -> Panel:
        """Render the warning panel.

        Returns:
            A Rich Panel with warning styling.
        """
        parts = []

        for message, detail in self._items:
            parts.append(Text(f"  {message}", style="bold"))
            if detail:
                parts.append(Text(f"    {detail}", style="dim"))

        content = Text("\n").join(parts) if parts else Text("Warning")

        title = self.title
        if self.show_icon:
            title = f"[warning]![/] {title}"

        return Panel(
            content,
            title=f"[warning]{title}[/]",
            border_style=COLORS["warning"],
            padding=(0, 1),
        )

    def print(self, console: Console) -> None:
        """Print the warning panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


class ErrorPanel:
    """A panel for displaying errors with prominent red styling.

    Used for displaying failures, exceptions, and critical issues.
    """

    def __init__(
        self,
        title: str = "Error",
        *,
        show_icon: bool = True,
    ) -> None:
        """Initialize the error panel.

        Args:
            title: Title for the panel.
            show_icon: Whether to show an error icon in the title.
        """
        self.title = title
        self.show_icon = show_icon
        self._message: str | None = None
        self._details: str | None = None
        self._suggestion: str | None = None

    def set_message(self, message: str) -> ErrorPanel:
        """Set the main error message.

        Args:
            message: The primary error message to display.

        Returns:
            Self for method chaining.
        """
        self._message = message
        return self

    def set_details(self, details: str) -> ErrorPanel:
        """Set additional error details.

        Args:
            details: Additional details like stack traces or context.

        Returns:
            Self for method chaining.
        """
        self._details = details
        return self

    def set_suggestion(self, suggestion: str) -> ErrorPanel:
        """Set a suggested action or fix.

        Args:
            suggestion: A suggestion for how to resolve the error.

        Returns:
            Self for method chaining.
        """
        self._suggestion = suggestion
        return self

    def clear(self) -> ErrorPanel:
        """Clear all error content.

        Returns:
            Self for method chaining.
        """
        self._message = None
        self._details = None
        self._suggestion = None
        return self

    def render(self) -> Panel:
        """Render the error panel.

        Returns:
            A Rich Panel with error styling.
        """
        parts = []

        if self._message:
            parts.append(Text(self._message, style="bold"))

        if self._details:
            if parts:
                parts.append(Text())  # Empty line
            parts.append(Text(self._details, style="dim"))

        if self._suggestion:
            if parts:
                parts.append(Text())  # Empty line
            parts.append(
                Text.assemble(
                    ("Suggestion: ", "bold"),
                    (self._suggestion, ""),
                )
            )

        content = Text("\n").join(parts) if parts else Text("An error occurred")

        title = self.title
        if self.show_icon:
            title = f"[error]X[/] {title}"

        return Panel(
            content,
            title=f"[error]{title}[/]",
            border_style=COLORS["error"],
            padding=(1, 2),
        )

    def print(self, console: Console) -> None:
        """Print the error panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


def create_status_bar(
    *,
    prd: str | None = None,
    progress: str | None = None,
    iteration: int | None = None,
    max_iterations: int | None = None,
    model: str | None = None,
    cost: float | None = None,
    max_cost: float | None = None,
) -> StatusBar:
    """Create a status bar with common loop runner information.

    Args:
        prd: Path to the PRD file.
        progress: Path to the progress file.
        iteration: Current iteration number.
        max_iterations: Maximum iterations allowed.
        model: Claude model being used.
        cost: Current cost in USD.
        max_cost: Maximum cost limit in USD.

    Returns:
        A configured StatusBar instance.
    """
    bar = StatusBar(title="Status")

    if prd:
        bar.add_item("PRD", prd)

    if progress:
        bar.add_item("Progress", progress)

    if iteration is not None:
        if max_iterations is not None:
            bar.add_item("Iteration", f"{iteration}/{max_iterations}")
        else:
            bar.add_item("Iteration", str(iteration))

    if model:
        bar.add_item("Model", model)

    if cost is not None:
        cost_str = f"${cost:.4f}"
        if max_cost is not None:
            cost_str = f"${cost:.4f}/${max_cost:.2f}"
            # Color based on budget usage
            ratio = cost / max_cost if max_cost > 0 else 0
            if ratio < 0.5:
                style = "success"
            elif ratio < 0.8:
                style = "warning"
            else:
                style = "error"
            bar.add_item("Cost", cost_str, style)
        else:
            bar.add_item("Cost", cost_str)
    elif max_cost is not None:
        # Show cost limit even when current cost is unknown
        bar.add_item("Cost Limit", f"${max_cost:.2f}")

    return bar


def create_output_panel(
    content: RenderableType,
    *,
    title: str = "Output",
    subtitle: str | None = None,
) -> OutputPanel:
    """Create an output panel with content.

    Args:
        content: The content to display.
        title: Title for the panel.
        subtitle: Optional subtitle.

    Returns:
        A configured OutputPanel instance.
    """
    return OutputPanel(title=title, subtitle=subtitle).set_content(content)


def create_error_panel(
    message: str,
    *,
    title: str = "Error",
    details: str | None = None,
    suggestion: str | None = None,
) -> ErrorPanel:
    """Create an error panel with a message.

    Args:
        message: The main error message.
        title: Title for the panel.
        details: Optional additional details.
        suggestion: Optional suggestion for resolution.

    Returns:
        A configured ErrorPanel instance.
    """
    panel = ErrorPanel(title=title).set_message(message)
    if details:
        panel.set_details(details)
    if suggestion:
        panel.set_suggestion(suggestion)
    return panel


def create_warning_panel(
    items: list[tuple[str, str | None]],
    *,
    title: str = "Warning",
) -> WarningPanel:
    """Create a warning panel with items.

    Args:
        items: List of (message, detail) tuples. Detail can be None.
        title: Title for the panel.

    Returns:
        A configured WarningPanel instance.
    """
    panel = WarningPanel(title=title)
    for message, detail in items:
        panel.add_item(message, detail)
    return panel
