"""Keyboard listener for terminal input.

Provides a background daemon thread that reads stdin in cbreak mode,
decodes escape sequences for special keys (arrows, PgUp/PgDn, Home/End),
and dispatches key events to a callback function.

Uses tty.setcbreak() (not setraw) so Ctrl+C still generates SIGINT.
"""

from __future__ import annotations

import select
import sys
import termios
import threading
import tty
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Union


class Key(Enum):
    """Known key constants."""

    UP = "up"
    DOWN = "down"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"
    HOME = "home"
    END = "end"


class CharEvent:
    """A character input event."""

    def __init__(self, char: str) -> None:
        self.char = char

    def __repr__(self) -> str:
        return f"CharEvent(char={self.char!r})"


@dataclass(frozen=True)
class KeyEvent:
    """A keyboard event."""

    key: Key


# Escape sequence lookup table.
# After reading ESC ([0x1b]), we read '[' and then the trailing bytes.
_ESCAPE_SEQUENCES: dict[str, Key] = {
    "A": Key.UP,       # ESC [ A
    "B": Key.DOWN,     # ESC [ B
    "5~": Key.PAGE_UP,   # ESC [ 5 ~
    "6~": Key.PAGE_DOWN, # ESC [ 6 ~
    "H": Key.HOME,     # ESC [ H
    "F": Key.END,      # ESC [ F
    "1~": Key.HOME,    # ESC [ 1 ~ (alternate)
    "4~": Key.END,     # ESC [ 4 ~ (alternate)
    "7~": Key.HOME,    # ESC [ 7 ~ (rxvt)
    "8~": Key.END,     # ESC [ 8 ~ (rxvt)
}


class KeyboardListener:
    """Background daemon thread that reads terminal key events.

    Uses ``tty.setcbreak()`` to put the terminal into cbreak mode so
    individual keystrokes are available without waiting for Enter, while
    still allowing Ctrl+C to generate SIGINT.

    The listener runs a daemon thread that polls stdin with
    ``select.select()`` using a 100 ms timeout.  When a key press is
    detected it decodes escape sequences for arrow keys, PgUp/PgDn,
    Home, and End, then calls *callback* with a :class:`KeyEvent`.

    Terminal settings are saved before entering cbreak mode and restored
    when the listener is stopped, even if an exception occurs.

    Parameters
    ----------
    callback:
        Function called with a :class:`KeyEvent` for each recognised key.
    """

    def __init__(self, callback: Callable[[Union[KeyEvent, CharEvent]], None]) -> None:
        self.callback = callback
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._old_settings: list | None = None
        self._stdin_fd: int | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start listening for key events in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        # Only set cbreak if stdin is a real terminal.
        if not sys.stdin.isatty():
            return

        self._stdin_fd = sys.stdin.fileno()
        self._old_settings = termios.tcgetattr(self._stdin_fd)

        try:
            tty.setcbreak(self._stdin_fd)
        except termios.error:
            self._old_settings = None
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="keyboard-listener",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the listener and restore terminal settings."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._restore_terminal()

    @property
    def is_running(self) -> bool:
        """Return True if the listener thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _restore_terminal(self) -> None:
        """Restore the original terminal settings."""
        if self._old_settings is not None and self._stdin_fd is not None:
            try:
                termios.tcsetattr(
                    self._stdin_fd, termios.TCSADRAIN, self._old_settings
                )
            except termios.error:
                pass
            self._old_settings = None

    def _run(self) -> None:
        """Main loop executed in the background thread."""
        try:
            while not self._stop_event.is_set():
                self._poll_once()
        finally:
            # Belt-and-suspenders: restore terminal even if callback raises.
            self._restore_terminal()

    def _poll_once(self) -> None:
        """Poll stdin once with a 100 ms timeout."""
        try:
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        except (ValueError, OSError):
            # stdin closed or not selectable.
            self._stop_event.set()
            return

        if not ready:
            return

        try:
            ch = sys.stdin.read(1)
        except (OSError, ValueError):
            self._stop_event.set()
            return

        if not ch:
            # EOF on stdin.
            self._stop_event.set()
            return

        if ch == "\x1b":
            self._read_escape_sequence()
        elif ch.isprintable():
            # Dispatch printable characters
            try:
                self.callback(CharEvent(char=ch))
            except Exception:
                pass  # Never crash the listener thread.

    def _read_escape_sequence(self) -> None:
        """Try to read and decode an escape sequence after ESC."""
        # Wait briefly for the next character — sequences arrive quickly.
        try:
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        except (ValueError, OSError):
            return

        if not ready:
            return  # Bare ESC — ignore.

        try:
            ch = sys.stdin.read(1)
        except (OSError, ValueError):
            return

        if ch != "[":
            return  # Not a CSI sequence — ignore.

        # Read the remaining bytes of the sequence (up to 4 chars).
        seq = ""
        for _ in range(4):
            try:
                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            except (ValueError, OSError):
                break
            if not ready:
                break
            try:
                c = sys.stdin.read(1)
            except (OSError, ValueError):
                break
            seq += c
            # Terminal sequences end with an alpha char or '~'.
            if c.isalpha() or c == "~":
                break

        key = _ESCAPE_SEQUENCES.get(seq)
        if key is not None:
            try:
                self.callback(KeyEvent(key=key))
            except Exception:
                pass  # Never crash the listener thread.
