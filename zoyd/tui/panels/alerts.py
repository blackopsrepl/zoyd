"""Alert panel components for Zoyd TUI.

Provides reusable panel components for displaying warnings and errors
in terminal interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.text import Text

from zoyd.tui.theme import COLORS

if TYPE_CHECKING:
    from rich.console import Console


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
        """Initialize warning panel.

        Args:
            title: Title for panel.
            show_icon: Whether to show a warning icon in title.
        """
        self.title = title
        self.show_icon = show_icon
        self._items: list[tuple[str, str | None]] = []

    def add_item(self, message: str, detail: str | None = None) -> WarningPanel:
        """Add a warning item.

        Args:
            message: The warning message.
            detail: Optional detail/context for warning.

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
        """Render warning panel.

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
        """Print warning panel to console.

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
        """Initialize error panel.

        Args:
            title: Title for panel.
            show_icon: Whether to show an error icon in title.
        """
        self.title = title
        self.show_icon = show_icon
        self._message: str | None = None
        self._details: str | None = None
        self._suggestion: str | None = None

    def set_message(self, message: str) -> ErrorPanel:
        """Set main error message.

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
        """Render error panel.

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
        """Print error panel to console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())