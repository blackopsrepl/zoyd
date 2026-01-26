"""Panel components for the Zoyd TUI.

Provides reusable panel components for displaying status, output, and errors
in the terminal interface.
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
    task: str | None = None,
    completed: int = 0,
    total: int = 0,
    iteration: int | None = None,
    max_iterations: int | None = None,
    model: str | None = None,
    cost: float | None = None,
    max_cost: float | None = None,
) -> StatusBar:
    """Create a status bar with common loop runner information.

    Args:
        task: Current task description.
        completed: Number of completed tasks.
        total: Total number of tasks.
        iteration: Current iteration number.
        max_iterations: Maximum iterations allowed.
        model: Claude model being used.
        cost: Current cost in USD.
        max_cost: Maximum cost limit in USD.

    Returns:
        A configured StatusBar instance.
    """
    bar = StatusBar(title="Status")

    if task:
        bar.add_item("Task", task)

    if total > 0:
        bar.add_item("Completed", f"{completed}/{total}")

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


def create_claude_output_panel(
    content: str = "",
    *,
    title: str = "Claude Output",
    subtitle: str | None = None,
    use_markdown: bool = True,
    code_theme: str = "dracula",
) -> ClaudeOutputPanel:
    """Create a Claude output panel with markdown content.

    Args:
        content: Markdown text from Claude's output.
        title: Title for the panel.
        subtitle: Optional subtitle (e.g., iteration number).
        use_markdown: Whether to render content as markdown.
        code_theme: Pygments theme for syntax highlighting (default: dracula).

    Returns:
        A configured ClaudeOutputPanel instance.
    """
    panel = ClaudeOutputPanel(title=title, subtitle=subtitle, code_theme=code_theme)
    panel.set_content(content)
    panel.set_markdown(use_markdown)
    return panel


class IterationHistoryPanel:
    """A panel for displaying recent iteration history.

    Shows a table of recent iterations with their status, cost, and duration.
    Useful for tracking progress and identifying patterns in the loop execution.
    """

    # Status icons
    STATUS_ICONS = {
        "success": "[success]✓[/]",
        "failed": "[error]✗[/]",
        "running": "[active]◉[/]",
        "pending": "[dim]○[/]",
    }

    def __init__(
        self,
        title: str = "History",
        *,
        max_items: int = 10,
    ) -> None:
        """Initialize the iteration history panel.

        Args:
            title: Title for the panel.
            max_items: Maximum number of iterations to display.
        """
        self.title = title
        self.max_items = max_items
        self._items: list[dict] = []

    def add_iteration(
        self,
        iteration: int,
        *,
        status: str = "pending",
        cost: float | None = None,
        duration: float | None = None,
        task: str | None = None,
    ) -> "IterationHistoryPanel":
        """Add an iteration to the history.

        Args:
            iteration: Iteration number.
            status: Status string - "success", "failed", "running", or "pending".
            cost: Cost in USD for this iteration.
            duration: Duration in seconds.
            task: Task description that was worked on.

        Returns:
            Self for method chaining.
        """
        item = {
            "iteration": iteration,
            "status": status,
            "cost": cost,
            "duration": duration,
            "task": task,
        }
        self._items.append(item)

        # Trim to max items
        if len(self._items) > self.max_items:
            self._items = self._items[-self.max_items :]

        return self

    def update_iteration(
        self,
        iteration: int,
        *,
        status: str | None = None,
        cost: float | None = None,
        duration: float | None = None,
        task: str | None = None,
    ) -> "IterationHistoryPanel":
        """Update an existing iteration in the history.

        Args:
            iteration: Iteration number to update.
            status: New status string (if provided).
            cost: New cost value (if provided).
            duration: New duration value (if provided).
            task: New task description (if provided).

        Returns:
            Self for method chaining.
        """
        for item in self._items:
            if item["iteration"] == iteration:
                if status is not None:
                    item["status"] = status
                if cost is not None:
                    item["cost"] = cost
                if duration is not None:
                    item["duration"] = duration
                if task is not None:
                    item["task"] = task
                break
        return self

    def clear(self) -> "IterationHistoryPanel":
        """Clear all iteration history.

        Returns:
            Self for method chaining.
        """
        self._items = []
        return self

    def _format_duration(self, seconds: float | None) -> str:
        """Format duration in seconds to a readable string.

        Args:
            seconds: Duration in seconds, or None.

        Returns:
            Formatted duration string.
        """
        if seconds is None:
            return "-"
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"

    def _format_cost(self, cost: float | None) -> str:
        """Format cost in USD to a readable string.

        Args:
            cost: Cost in USD, or None.

        Returns:
            Formatted cost string.
        """
        if cost is None:
            return "-"
        return f"${cost:.4f}"

    def _truncate_task(self, task: str | None, max_len: int = 30) -> str:
        """Truncate task text to fit in the display.

        Args:
            task: Task description, or None.
            max_len: Maximum length before truncation.

        Returns:
            Truncated task string.
        """
        if task is None:
            return "-"
        if len(task) <= max_len:
            return task
        return task[: max_len - 3] + "..."

    def render(self) -> Panel:
        """Render the iteration history panel.

        Returns:
            A Rich Panel containing the iteration history table.
        """
        table = Table(
            show_header=True,
            show_edge=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )

        # Define columns
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Status", width=7, justify="center")
        table.add_column("Cost", width=10, justify="right")
        table.add_column("Duration", width=10, justify="right")
        table.add_column("Task", ratio=1)

        # Add rows
        if not self._items:
            # Show placeholder when empty
            return Panel(
                Text("No iterations yet", style="dim"),
                title=f"[panel.title]{self.title}[/]",
                border_style=COLORS["twilight"],
                padding=(0, 1),
            )

        for item in self._items:
            status_icon = self.STATUS_ICONS.get(item["status"], "[dim]?[/]")
            table.add_row(
                str(item["iteration"]),
                status_icon,
                self._format_cost(item["cost"]),
                self._format_duration(item["duration"]),
                self._truncate_task(item["task"]),
            )

        return Panel(
            table,
            title=f"[panel.title]{self.title}[/]",
            border_style=COLORS["twilight"],
            padding=(0, 1),
        )

    def print(self, console: Console) -> None:
        """Print the iteration history panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


def create_iteration_history_panel(
    *,
    title: str = "History",
    max_items: int = 10,
) -> IterationHistoryPanel:
    """Create an iteration history panel.

    Factory function for creating IterationHistoryPanel.

    Args:
        title: Title for the panel.
        max_items: Maximum number of iterations to display.

    Returns:
        A configured IterationHistoryPanel instance.
    """
    return IterationHistoryPanel(title=title, max_items=max_items)


class GitCommitLogPanel:
    """A panel for displaying recent git commits from the session.

    Shows a table of commits made during the zoyd session with their
    iteration number, shortened hash, and commit message.
    """

    def __init__(
        self,
        title: str = "Git Commits",
        *,
        max_items: int = 10,
    ) -> None:
        """Initialize the git commit log panel.

        Args:
            title: Title for the panel.
            max_items: Maximum number of commits to display.
        """
        self.title = title
        self.max_items = max_items
        self._commits: list[dict] = []

    def add_commit(
        self,
        *,
        iteration: int,
        message: str,
        commit_hash: str | None = None,
    ) -> "GitCommitLogPanel":
        """Add a commit to the log.

        Args:
            iteration: Iteration number when commit was made.
            message: Commit message (first line).
            commit_hash: Short commit hash (optional).

        Returns:
            Self for method chaining.
        """
        commit = {
            "iteration": iteration,
            "message": message,
            "hash": commit_hash,
        }
        self._commits.append(commit)

        # Trim to max items
        if len(self._commits) > self.max_items:
            self._commits = self._commits[-self.max_items :]

        return self

    def clear(self) -> "GitCommitLogPanel":
        """Clear all commits from the log.

        Returns:
            Self for method chaining.
        """
        self._commits = []
        return self

    def _truncate_message(self, message: str, max_len: int = 50) -> str:
        """Truncate commit message to fit in the display.

        Args:
            message: Commit message.
            max_len: Maximum length before truncation.

        Returns:
            Truncated message string.
        """
        if len(message) <= max_len:
            return message
        return message[: max_len - 3] + "..."

    def render(self) -> Panel:
        """Render the git commit log panel.

        Returns:
            A Rich Panel containing the commit log table.
        """
        if not self._commits:
            return Panel(
                Text("No commits yet", style="dim"),
                title=f"[panel.title]{self.title}[/]",
                border_style=COLORS["twilight"],
                padding=(0, 1),
            )

        table = Table(
            show_header=True,
            show_edge=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )

        # Define columns
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Hash", style=COLORS["amethyst"], width=8)
        table.add_column("Message", ratio=1)

        # Add rows
        for commit in self._commits:
            hash_display = commit["hash"][:7] if commit["hash"] else "-"
            table.add_row(
                str(commit["iteration"]),
                hash_display,
                self._truncate_message(commit["message"]),
            )

        return Panel(
            table,
            title=f"[panel.title]{self.title}[/]",
            border_style=COLORS["twilight"],
            padding=(0, 1),
        )

    def print(self, console: Console) -> None:
        """Print the git commit log panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


def create_git_commit_log_panel(
    *,
    title: str = "Git Commits",
    max_items: int = 10,
) -> GitCommitLogPanel:
    """Create a git commit log panel.

    Factory function for creating GitCommitLogPanel.

    Args:
        title: Title for the panel.
        max_items: Maximum number of commits to display.

    Returns:
        A configured GitCommitLogPanel instance.
    """
    return GitCommitLogPanel(title=title, max_items=max_items)


class BlockedTaskPanel:
    """A panel for displaying blocked tasks with warning styling and suggestions.

    Used when a task cannot be completed due to missing dependencies,
    unclear requirements, or other blockers. Provides context about what's
    blocking the task and suggestions for how to proceed.
    """

    def __init__(
        self,
        title: str = "Task Blocked",
        *,
        show_icon: bool = True,
    ) -> None:
        """Initialize the blocked task panel.

        Args:
            title: Title for the panel.
            show_icon: Whether to show a blocked/stop icon in the title.
        """
        self.title = title
        self.show_icon = show_icon
        self._task: str | None = None
        self._reason: str | None = None
        self._blockers: list[str] = []
        self._suggestions: list[str] = []

    def set_task(self, task: str) -> "BlockedTaskPanel":
        """Set the blocked task description.

        Args:
            task: The task that is blocked.

        Returns:
            Self for method chaining.
        """
        self._task = task
        return self

    def set_reason(self, reason: str) -> "BlockedTaskPanel":
        """Set the reason why the task is blocked.

        Args:
            reason: Why the task cannot be completed.

        Returns:
            Self for method chaining.
        """
        self._reason = reason
        return self

    def add_blocker(self, blocker: str) -> "BlockedTaskPanel":
        """Add a specific blocker preventing task completion.

        Args:
            blocker: A specific issue blocking the task.

        Returns:
            Self for method chaining.
        """
        self._blockers.append(blocker)
        return self

    def add_suggestion(self, suggestion: str) -> "BlockedTaskPanel":
        """Add a suggestion for how to resolve the blocker.

        Args:
            suggestion: A suggested action to unblock the task.

        Returns:
            Self for method chaining.
        """
        self._suggestions.append(suggestion)
        return self

    def clear(self) -> "BlockedTaskPanel":
        """Clear all content from the panel.

        Returns:
            Self for method chaining.
        """
        self._task = None
        self._reason = None
        self._blockers = []
        self._suggestions = []
        return self

    def render(self) -> Panel:
        """Render the blocked task panel.

        Returns:
            A Rich Panel with blocked/warning styling.
        """
        parts = []

        # Task description
        if self._task:
            parts.append(
                Text.assemble(
                    ("Task: ", "bold"),
                    (self._task, COLORS["mist"]),
                )
            )

        # Reason for blocking
        if self._reason:
            if parts:
                parts.append(Text())  # Empty line
            parts.append(
                Text.assemble(
                    ("Reason: ", "bold"),
                    (self._reason, COLORS["warning"]),
                )
            )

        # List of blockers
        if self._blockers:
            if parts:
                parts.append(Text())  # Empty line
            parts.append(Text("Blockers:", style="bold"))
            for blocker in self._blockers:
                parts.append(Text(f"  • {blocker}", style="dim"))

        # List of suggestions
        if self._suggestions:
            if parts:
                parts.append(Text())  # Empty line
            parts.append(Text("Suggestions:", style="bold"))
            for suggestion in self._suggestions:
                parts.append(
                    Text.assemble(
                        ("  → ", COLORS["success"]),
                        (suggestion, ""),
                    )
                )

        content = Text("\n").join(parts) if parts else Text("Task is blocked")

        title = self.title
        if self.show_icon:
            title = f"[{COLORS['blocked']}]⊘[/] {title}"

        return Panel(
            content,
            title=f"[{COLORS['blocked']}]{title}[/]",
            border_style=COLORS["blocked"],
            padding=(1, 2),
        )

    def print(self, console: Console) -> None:
        """Print the blocked task panel to the console.

        Args:
            console: Rich Console to print to.
        """
        console.print(self.render())


def create_blocked_task_panel(
    task: str,
    *,
    reason: str | None = None,
    blockers: list[str] | None = None,
    suggestions: list[str] | None = None,
    title: str = "Task Blocked",
) -> BlockedTaskPanel:
    """Create a blocked task panel with content.

    Factory function for creating BlockedTaskPanel with pre-populated content.

    Args:
        task: The task that is blocked.
        reason: Why the task is blocked (optional).
        blockers: List of specific blockers (optional).
        suggestions: List of suggested actions (optional).
        title: Title for the panel.

    Returns:
        A configured BlockedTaskPanel instance.
    """
    panel = BlockedTaskPanel(title=title).set_task(task)

    if reason:
        panel.set_reason(reason)

    if blockers:
        for blocker in blockers:
            panel.add_blocker(blocker)

    if suggestions:
        for suggestion in suggestions:
            panel.add_suggestion(suggestion)

    return panel
