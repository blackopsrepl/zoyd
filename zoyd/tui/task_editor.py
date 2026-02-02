"""Vim-like modal task editor for PRD files.

Provides a state machine-based editor with vim key bindings for editing
task lists in PRD files. Supports normal, insert, command, and search modes
with full undo/redo functionality.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable

from rich.console import Console, ConsoleOptions, RenderResult
from rich.layout import Layout
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from zoyd.prd import Task, add_task, delete_task, edit_task, move_task, parse_tasks, toggle_task
from zoyd.tui.theme import COLORS, STYLES


class EditorMode(Enum):
    """Editor mode states."""

    NORMAL = auto()
    INSERT = auto()
    COMMAND = auto()
    SEARCH = auto()


class EditorAction(Enum):
    """Actions returned by handle_key()."""

    CONTINUE = auto()
    QUIT = auto()
    QUIT_FORCE = auto()
    SAVE = auto()
    SAVE_AND_QUIT = auto()


@dataclass
class EditAction:
    """A single edit action for undo/redo tracking."""

    action_type: str  # 'edit', 'add', 'delete', 'move', 'toggle'
    task_index: int
    old_task: Task | None = None
    new_task: Task | None = None
    old_text: str = ""
    new_text: str = ""


@dataclass
class EditorState:
    """Internal state snapshot for undo."""

    tasks: list[Task] = field(default_factory=list)
    cursor: int = 0
    modified: bool = False


class TaskEditor:
    """Vim-like modal editor for PRD task lists.

    Provides a state machine with normal, insert, command, and search modes.
    Supports vim key bindings, undo/redo (5 levels), and rich rendering.

    Example:
        editor = TaskEditor(Path("PRD.md"))
        action = editor.handle_key("j")  # Move down
        editor.render(console)
    """

    MAX_UNDO_LEVELS = 5

    def __init__(self, prd_path: Path, console: Console | None = None) -> None:
        """Initialize the task editor.

        Args:
            prd_path: Path to the PRD file to edit.
            console: Optional Rich console for rendering.
        """
        self.prd_path = prd_path
        self.console = console or Console()

        # Load tasks from PRD
        self._original_content = prd_path.read_text()
        self.tasks = parse_tasks(self._original_content)

        # Editor state
        self.mode = EditorMode.NORMAL
        self.cursor = 0 if self.tasks else -1
        self.modified = False

        # Command/search buffers
        self.command_buffer = ""
        self.search_buffer = ""
        self.search_pattern: re.Pattern | None = None
        self.search_results: list[int] = []
        self.search_index = -1

        # Insert mode state
        self.insert_buffer = ""
        self.insert_cursor = 0
        self.insert_task_index = -1

        # Undo stack (circular buffer for 5 levels)
        self._undo_stack: list[EditorState] = []
        self._undo_index = -1

        # Message display
        self.message = ""
        self.message_timeout = 0

        # Multi-key sequences
        self._pending_key = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_key(self, key: str) -> EditorAction:
        """Handle a key press based on current mode.

        Args:
            key: The key pressed (single character or special name).

        Returns:
            EditorAction indicating what the caller should do.
        """
        if self.mode == EditorMode.NORMAL:
            return self._handle_normal_key(key)
        elif self.mode == EditorMode.INSERT:
            return self._handle_insert_key(key)
        elif self.mode == EditorMode.COMMAND:
            return self._handle_command_key(key)
        elif self.mode == EditorMode.SEARCH:
            return self._handle_search_key(key)
        return EditorAction.CONTINUE

    def render(self) -> Panel:
        """Render the editor state as a Rich Panel.

        Returns:
            Rich Panel containing the rendered editor.
        """
        layout = Layout()

        # Main task list
        task_layout = self._render_task_list()
        layout.split_column(
            Layout(task_layout, name="tasks"),
            Layout(self._render_status_line(), name="status", size=1),
        )

        # Add command/search line if active
        if self.mode in (EditorMode.COMMAND, EditorMode.SEARCH):
            layout.split_row(
                Layout(task_layout, name="tasks"),
            )
            layout["tasks"].update(self._render_task_list())

            if self.mode == EditorMode.COMMAND:
                layout["status"].update(self._render_command_line())
            else:
                layout["status"].update(self._render_search_line())

        return Panel(
            layout,
            title=self._render_title(),
            border_style=COLORS["twilight"],
            padding=(0, 0),
        )

    def save(self) -> bool:
        """Save the current state to the PRD file.

        Returns:
            True if save was successful, False otherwise.
        """
        try:
            # Reconstruct the PRD content with current tasks
            lines = self._original_content.splitlines()
            task_line_map = {}

            # Map original task lines
            for i, task in enumerate(parse_tasks(self._original_content)):
                task_line_map[task.line_number - 1] = i

            # Build new content
            new_lines = []
            task_idx = 0

            for i, line in enumerate(lines):
                if i in task_line_map:
                    # This is a task line - replace with current task
                    if task_idx < len(self.tasks):
                        task = self.tasks[task_idx]
                        checkbox = "x" if task.complete else " "
                        new_lines.append(f"- [{checkbox}] {task.text}")
                        task_idx += 1
                else:
                    new_lines.append(line)

            # Add any remaining tasks at the end
            while task_idx < len(self.tasks):
                task = self.tasks[task_idx]
                checkbox = "x" if task.complete else " "
                new_lines.append(f"- [{checkbox}] {task.text}")
                task_idx += 1

            # Write back
            new_content = "\n".join(new_lines) + ("\n" if self._original_content.endswith("\n") else "")
            self.prd_path.write_text(new_content)

            # Update original content and reset modified flag
            self._original_content = new_content
            self.modified = False
            self._set_message("Saved")
            return True

        except Exception as e:
            self._set_message(f"Error: {e}")
            return False

    def quit(self, force: bool = False) -> EditorAction:
        """Quit the editor.

        Args:
            force: If True, quit without saving even if modified.

        Returns:
            EditorAction.QUIT or EditorAction.QUIT_FORCE.
        """
        if self.modified and not force:
            self._set_message("No write since last change (add ! to override)")
            return EditorAction.CONTINUE
        return EditorAction.QUIT_FORCE if force else EditorAction.QUIT

    def is_modified(self) -> bool:
        """Check if the editor has unsaved changes."""
        return self.modified

    def get_current_task(self) -> Task | None:
        """Get the task at the current cursor position."""
        if 0 <= self.cursor < len(self.tasks):
            return self.tasks[self.cursor]
        return None

    # ------------------------------------------------------------------
    # Mode Handlers
    # ------------------------------------------------------------------

    def _handle_normal_key(self, key: str) -> EditorAction:
        """Handle key in normal mode."""
        # Multi-key sequences
        if self._pending_key:
            return self._handle_pending_key(key)

        # Movement
        if key == "j" or key == "down":
            self._move_cursor(1)
        elif key == "k" or key == "up":
            self._move_cursor(-1)
        elif key == "g":
            self._pending_key = "g"  # Wait for second 'g'
        elif key == "G":
            self._move_cursor_to(len(self.tasks) - 1)

        # Mode switching
        elif key == "i":
            self._enter_insert_mode(before_cursor=True)
        elif key == "a":
            self._enter_insert_mode(before_cursor=False)
        elif key == "o":
            self._add_task_and_insert(after=True)
        elif key == "O":
            self._add_task_and_insert(after=False)
        elif key == ":":
            self._enter_command_mode()
        elif key == "/":
            self._enter_search_mode()

        # Editing
        elif key == "x":
            self._toggle_task()
        elif key == "d":
            self._pending_key = "d"  # Wait for second 'd'
        elif key == "J":
            self._move_task_down()
        elif key == "K":
            self._move_task_up()

        # Undo
        elif key == "u":
            self._undo()

        # Search navigation
        elif key == "n":
            self._next_search_result()
        elif key == "N":
            self._prev_search_result()

        return EditorAction.CONTINUE

    def _handle_pending_key(self, key: str) -> EditorAction:
        """Handle second key of multi-key sequences."""
        pending = self._pending_key
        self._pending_key = ""

        if pending == "g" and key == "g":
            self._move_cursor_to(0)
        elif pending == "d" and key == "d":
            self._delete_task()

        return EditorAction.CONTINUE

    def _handle_insert_key(self, key: str) -> EditorAction:
        """Handle key in insert mode."""
        if key == "escape" or key == "\x1b":
            self._exit_insert_mode(save=True)
        elif key == "\r" or key == "\n":
            self._exit_insert_mode(save=True)
        elif key == "backspace" or key == "\x7f":
            if self.insert_cursor > 0:
                self.insert_buffer = (
                    self.insert_buffer[: self.insert_cursor - 1] + self.insert_buffer[self.insert_cursor :]
                )
                self.insert_cursor -= 1
        elif key == "left":
            self.insert_cursor = max(0, self.insert_cursor - 1)
        elif key == "right":
            self.insert_cursor = min(len(self.insert_buffer), self.insert_cursor + 1)
        elif key == "home":
            self.insert_cursor = 0
        elif key == "end":
            self.insert_cursor = len(self.insert_buffer)
        elif len(key) == 1 and key.isprintable():
            self.insert_buffer = (
                self.insert_buffer[: self.insert_cursor] + key + self.insert_buffer[self.insert_cursor :]
            )
            self.insert_cursor += 1

        return EditorAction.CONTINUE

    def _handle_command_key(self, key: str) -> EditorAction:
        """Handle key in command mode."""
        if key == "escape" or key == "\x1b":
            self._exit_command_mode()
            return EditorAction.CONTINUE
        elif key == "\r" or key == "\n":
            return self._execute_command()
        elif key == "backspace" or key == "\x7f":
            if self.command_buffer:
                self.command_buffer = self.command_buffer[:-1]
        elif key == "\t":
            # Tab completion could go here
            pass
        elif len(key) == 1 and key.isprintable():
            self.command_buffer += key

        return EditorAction.CONTINUE

    def _handle_search_key(self, key: str) -> EditorAction:
        """Handle key in search mode."""
        if key == "escape" or key == "\x1b":
            self._exit_search_mode()
            return EditorAction.CONTINUE
        elif key == "\r" or key == "\n":
            self._execute_search()
            self._exit_search_mode()
            return EditorAction.CONTINUE
        elif key == "backspace" or key == "\x7f":
            if self.search_buffer:
                self.search_buffer = self.search_buffer[:-1]
        elif len(key) == 1 and key.isprintable():
            self.search_buffer += key

        return EditorAction.CONTINUE

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _push_undo(self) -> None:
        """Save current state to undo stack."""
        state = EditorState(
            tasks=deepcopy(self.tasks),
            cursor=self.cursor,
            modified=self.modified,
        )

        # Manage circular buffer
        if len(self._undo_stack) < self.MAX_UNDO_LEVELS:
            self._undo_stack.append(state)
            self._undo_index = len(self._undo_stack) - 1
        else:
            # Shift and wrap
            self._undo_stack.pop(0)
            self._undo_stack.append(state)
            self._undo_index = self.MAX_UNDO_LEVELS - 1

    def _undo(self) -> None:
        """Undo last action."""
        if self._undo_index >= 0:
            state = self._undo_stack[self._undo_index]
            self.tasks = deepcopy(state.tasks)
            self.cursor = state.cursor
            self.modified = state.modified
            self._undo_index -= 1
            self._set_message("Undone")
        else:
            self._set_message("Already at oldest change")

    def _move_cursor(self, delta: int) -> None:
        """Move cursor by delta positions."""
        if not self.tasks:
            return
        self.cursor = max(0, min(len(self.tasks) - 1, self.cursor + delta))

    def _move_cursor_to(self, pos: int) -> None:
        """Move cursor to absolute position."""
        if not self.tasks:
            return
        self.cursor = max(0, min(len(self.tasks) - 1, pos))

    def _toggle_task(self) -> None:
        """Toggle completion state of current task."""
        if not self.tasks or not (0 <= self.cursor < len(self.tasks)):
            return

        self._push_undo()
        task = self.tasks[self.cursor]
        task.complete = not task.complete
        self.modified = True
        self._set_message(f"Task {'completed' if task.complete else 'reopened'}")

    def _delete_task(self) -> None:
        """Delete current task."""
        if not self.tasks or not (0 <= self.cursor < len(self.tasks)):
            return

        self._push_undo()
        self.tasks.pop(self.cursor)
        self.modified = True

        # Adjust cursor
        if self.cursor >= len(self.tasks) and self.tasks:
            self.cursor = len(self.tasks) - 1
        elif not self.tasks:
            self.cursor = -1

        self._set_message("Task deleted")

    def _move_task_up(self) -> None:
        """Move current task up (swap with previous)."""
        if not self.tasks or self.cursor <= 0:
            return

        self._push_undo()
        self.tasks[self.cursor], self.tasks[self.cursor - 1] = (
            self.tasks[self.cursor - 1],
            self.tasks[self.cursor],
        )
        self.cursor -= 1
        self.modified = True

    def _move_task_down(self) -> None:
        """Move current task down (swap with next)."""
        if not self.tasks or self.cursor >= len(self.tasks) - 1:
            return

        self._push_undo()
        self.tasks[self.cursor], self.tasks[self.cursor + 1] = (
            self.tasks[self.cursor + 1],
            self.tasks[self.cursor],
        )
        self.cursor += 1
        self.modified = True

    def _enter_insert_mode(self, before_cursor: bool = True) -> None:
        """Enter insert mode for current task."""
        if not self.tasks or not (0 <= self.cursor < len(self.tasks)):
            return

        self._push_undo()
        self.mode = EditorMode.INSERT
        self.insert_task_index = self.cursor
        task = self.tasks[self.cursor]
        self.insert_buffer = task.text
        self.insert_cursor = 0 if before_cursor else len(task.text)

    def _exit_insert_mode(self, save: bool = True) -> None:
        """Exit insert mode."""
        if save and 0 <= self.insert_task_index < len(self.tasks):
            self.tasks[self.insert_task_index].text = self.insert_buffer
            self.modified = True

        self.mode = EditorMode.NORMAL
        self.insert_buffer = ""
        self.insert_cursor = 0
        self.insert_task_index = -1

    def _add_task_and_insert(self, after: bool = True) -> None:
        """Add a new task and enter insert mode."""
        self._push_undo()

        if not self.tasks:
            # First task
            new_task = Task(text="", complete=False, line_number=1)
            self.tasks.append(new_task)
            self.cursor = 0
        else:
            insert_pos = self.cursor + (1 if after else 0)
            new_task = Task(text="", complete=False, line_number=insert_pos + 1)
            self.tasks.insert(insert_pos, new_task)
            self.cursor = insert_pos

        self.modified = True
        self._enter_insert_mode(before_cursor=True)

    def _enter_command_mode(self) -> None:
        """Enter command mode."""
        self.mode = EditorMode.COMMAND
        self.command_buffer = ""

    def _exit_command_mode(self) -> None:
        """Exit command mode."""
        self.mode = EditorMode.NORMAL
        self.command_buffer = ""

    def _execute_command(self) -> EditorAction:
        """Execute the current command."""
        cmd = self.command_buffer.strip()
        self._exit_command_mode()

        if not cmd:
            return EditorAction.CONTINUE

        # Save commands
        if cmd in ("w", "write"):
            self.save()
            return EditorAction.CONTINUE
        elif cmd == "wq":
            if self.save():
                return EditorAction.SAVE_AND_QUIT
            return EditorAction.CONTINUE

        # Quit commands
        elif cmd in ("q", "quit"):
            return self.quit(force=False)
        elif cmd == "q!":
            return self.quit(force=True)

        # Go to line
        elif cmd.startswith("e "):
            try:
                line_num = int(cmd[2:].strip()) - 1  # Convert to 0-based
                self._move_cursor_to(line_num)
            except ValueError:
                self._set_message("Invalid line number")

        # Substitute
        elif cmd.startswith("s/"):
            self._execute_substitute(cmd)

        else:
            self._set_message(f"Unknown command: {cmd}")

        return EditorAction.CONTINUE

    def _execute_substitute(self, cmd: str) -> None:
        """Execute substitute command (s/old/new/)."""
        # Parse s/old/new/ pattern
        match = re.match(r"s/([^/]+)/([^/]*)/?", cmd)
        if not match:
            self._set_message("Invalid substitute pattern")
            return

        if not self.tasks or not (0 <= self.cursor < len(self.tasks)):
            return

        old_str, new_str = match.groups()
        task = self.tasks[self.cursor]

        if old_str in task.text:
            self._push_undo()
            task.text = task.text.replace(old_str, new_str, 1)
            self.modified = True
            self._set_message(f"Substituted '{old_str}' with '{new_str}'")
        else:
            self._set_message(f"Pattern not found: {old_str}")

    def _enter_search_mode(self) -> None:
        """Enter search mode."""
        self.mode = EditorMode.SEARCH
        self.search_buffer = ""
        self.search_results = []
        self.search_index = -1

    def _exit_search_mode(self) -> None:
        """Exit search mode."""
        self.mode = EditorMode.NORMAL

    def _execute_search(self) -> None:
        """Execute the search."""
        pattern = self.search_buffer
        if not pattern:
            return

        try:
            self.search_pattern = re.compile(pattern, re.IGNORECASE)
            self.search_results = []

            for i, task in enumerate(self.tasks):
                if self.search_pattern.search(task.text):
                    self.search_results.append(i)

            if self.search_results:
                # Find first result at or after cursor
                for idx in self.search_results:
                    if idx >= self.cursor:
                        self.cursor = idx
                        self.search_index = self.search_results.index(idx)
                        self._set_message(f"Search: {len(self.search_results)} matches")
                        return

                # Wrap to first result
                self.cursor = self.search_results[0]
                self.search_index = 0
                self._set_message(f"Search: {len(self.search_results)} matches (wrapped)")
            else:
                self._set_message("Pattern not found")

        except re.error as e:
            self._set_message(f"Invalid pattern: {e}")

    def _next_search_result(self) -> None:
        """Go to next search result."""
        if not self.search_results:
            return

        self.search_index = (self.search_index + 1) % len(self.search_results)
        self.cursor = self.search_results[self.search_index]

    def _prev_search_result(self) -> None:
        """Go to previous search result."""
        if not self.search_results:
            return

        self.search_index = (self.search_index - 1) % len(self.search_results)
        self.cursor = self.search_results[self.search_index]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_title(self) -> str:
        """Render the panel title."""
        mode_str = {
            EditorMode.NORMAL: "NORMAL",
            EditorMode.INSERT: "INSERT",
            EditorMode.COMMAND: "COMMAND",
            EditorMode.SEARCH: "SEARCH",
        }[self.mode]

        modified_flag = "[+]" if self.modified else ""
        return f"Task Editor - {mode_str} {modified_flag}"

    def _render_task_list(self) -> Text:
        """Render the task list."""
        text = Text()

        if not self.tasks:
            text.append("No tasks in PRD", style=COLORS["pending"])
            return text

        for i, task in enumerate(self.tasks):
            # Line number
            line_num = f"{i + 1:3d} "

            # Checkbox
            checkbox = "[x]" if task.complete else "[ ]"

            # Task text (with cursor in insert mode)
            if self.mode == EditorMode.INSERT and i == self.insert_task_index:
                # Show cursor position
                before_cursor = task.text[: self.insert_cursor]
                at_cursor = task.insert_buffer[self.insert_cursor : self.insert_cursor + 1] if hasattr(task, 'insert_buffer') else " "
                after_cursor = task.text[self.insert_cursor + 1 :]
                
                # Use insert_buffer if active
                display_text = self.insert_buffer
                before = display_text[: self.insert_cursor]
                cursor_char = display_text[self.insert_cursor] if self.insert_cursor < len(display_text) else " "
                after = display_text[self.insert_cursor + 1 :]

                task_display = f"{line_num}{checkbox} {before}[reverse]{cursor_char}[/reverse]{after}"
            else:
                task_display = f"{line_num}{checkbox} {task.text}"

            # Apply styles
            is_cursor = i == self.cursor
            is_complete = task.complete
            is_search_match = i in self.search_results

            if is_cursor:
                if self.mode == EditorMode.NORMAL:
                    # Highlight cursor line
                    style = f"bold {COLORS['active']}"
                else:
                    style = f"{COLORS['active']}"
            elif is_search_match:
                style = f"{COLORS['warning']}"
            elif is_complete:
                style = f"{COLORS['success']}"
            else:
                style = f"{COLORS['mist']}"

            # Add line
            prefix = "> " if is_cursor and self.mode == EditorMode.NORMAL else "  "
            text.append(f"{prefix}{task_display}\n", style=style)

        return text

    def _render_status_line(self) -> Text:
        """Render the status line."""
        text = Text()

        # Mode indicator
        mode_colors = {
            EditorMode.NORMAL: COLORS["success"],
            EditorMode.INSERT: COLORS["active"],
            EditorMode.COMMAND: COLORS["warning"],
            EditorMode.SEARCH: COLORS["info"],
        }
        mode_names = {
            EditorMode.NORMAL: "NORMAL",
            EditorMode.INSERT: "INSERT",
            EditorMode.COMMAND: "COMMAND",
            EditorMode.SEARCH: "SEARCH",
        }

        mode_style = f"bold {mode_colors[self.mode]}"
        text.append(f" {mode_names[self.mode]} ", style=mode_style)

        # Position info
        if self.tasks:
            pos_info = f" {self.cursor + 1}/{len(self.tasks)} "
            text.append(pos_info, style=COLORS["twilight"])

        # Message (centered-ish)
        if self.message:
            text.append(f"  {self.message}", style=COLORS["warning"])

        # Filename and modified flag
        filename = self.prd_path.name
        modified_flag = " [+]" if self.modified else ""
        text.append(f"  {filename}{modified_flag}", style=COLORS["orchid"])

        return text

    def _render_command_line(self) -> Text:
        """Render command line."""
        text = Text()
        text.append(":", style=f"bold {COLORS['warning']}")
        text.append(self.command_buffer, style=COLORS["mist"])
        text.append("█", style=COLORS["active"])  # Cursor
        return text

    def _render_search_line(self) -> Text:
        """Render search line."""
        text = Text()
        text.append("/", style=f"bold {COLORS['info']}")
        text.append(self.search_buffer, style=COLORS["mist"])
        text.append("█", style=COLORS["active"])  # Cursor
        return text

    def _set_message(self, msg: str) -> None:
        """Set a message to display."""
        self.message = msg


# ------------------------------------------------------------------
# Convenience functions
# ------------------------------------------------------------------


def create_task_editor(prd_path: Path, console: Console | None = None) -> TaskEditor:
    """Create a new TaskEditor instance.

    Args:
        prd_path: Path to the PRD file to edit.
        console: Optional Rich console for rendering.

    Returns:
        Configured TaskEditor instance.
    """
    return TaskEditor(prd_path, console)
