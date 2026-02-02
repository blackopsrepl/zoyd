"""Chat queue system for user interaction during Zoyd runs.

Provides a file-based message queue that allows users to send messages
to influence the Zoyd loop in real-time. Messages can be sent either
through the TUI or by writing directly to the chat file.

Example:
    chat = ChatQueue(Path(".zoyd/chat.txt"))
    chat.enqueue("Fix the login bug", "chat")
    messages = chat.dequeue_all()
    for msg in messages:
        print(f"[{msg.timestamp}] {msg.text}")
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


@dataclass(frozen=True)
class ChatMessage:
    """A single chat message.

    Attributes:
        text: The message content.
        type: Message type - "chat", "bash", "file", "task", "question".
        timestamp: When the message was created.
        source: Origin of message - "user" or "system".
        metadata: Additional data depending on message type.
    """

    text: str
    type: str = "chat"
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "user"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatMessage:
        """Create message from dictionary."""
        return cls(
            text=data["text"],
            type=data.get("type", "chat"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source", "user"),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return f"ChatMessage({self.type}: {self.text[:50]!r})"


def parse_command(text: str) -> tuple[str, str, dict[str, Any]]:
    """Parse special command prefixes from message text.

    Detects and extracts commands like !bash, @file, >task, ?question.
    Returns the message type, cleaned text, and metadata.

    Supported prefixes:
        !bash <command>  -> type="bash", executes command, includes output
        @<filepath>      -> type="file", reads file content
        >task <text>     -> type="task", adds new task to PRD
        ?<question>      -> type="question", side chat without iteration
        #urgent          -> type="chat", marks as high priority
        !important       -> type="chat", marks as high priority

    Args:
        text: Raw message text that may contain command prefix.

    Returns:
        Tuple of (msg_type, cleaned_text, metadata).
        If no command detected, returns ("chat", text, {}).

    Examples:
        >>> parse_command("!bash ls -la")
        ("bash", "ls -la", {})
        >>> parse_command("@src/main.py")
        ("file", "src/main.py", {})
        >>> parse_command(">task Add tests")
        ("task", "Add tests", {})
        >>> parse_command("?How does this work?")
        ("question", "How does this work?", {})
        >>> parse_command("Normal message")
        ("chat", "Normal message", {})
    """
    stripped = text.strip()

    if not stripped:
        return "chat", text, {}

    # Check for urgent/important markers anywhere in the text
    metadata: dict[str, Any] = {}
    if "#urgent" in stripped or "!important" in stripped:
        metadata["priority"] = "high"
        # Remove markers from text
        cleaned = stripped.replace("#urgent", "").replace("!important", "").strip()
        if cleaned != stripped:
            stripped = cleaned

    # Check for command prefixes
    if stripped.startswith("!bash "):
        command = stripped[6:].strip()
        return "bash", command, metadata

    if stripped.startswith("@"):
        filepath = stripped[1:].strip()
        return "file", filepath, metadata

    if stripped.startswith(">task "):
        task_text = stripped[6:].strip()
        return "task", task_text, metadata

    if stripped.startswith("?"):
        question = stripped[1:].strip()
        return "question", question, metadata

    return "chat", stripped, metadata


def format_messages_for_prompt(messages: list[ChatMessage]) -> str:
    """Format chat messages for inclusion in Claude prompt.

    Creates a formatted string suitable for the "User Messages" section
    of the prompt. Handles special message types appropriately.

    Args:
        messages: List of chat messages to format.

    Returns:
        Formatted string for prompt, or empty string if no messages.
    """
    if not messages:
        return ""

    lines = ["## User Messages"]
    for msg in messages:
        timestamp = msg.timestamp.strftime("%H:%M")
        priority_marker = " [URGENT]" if msg.metadata.get("priority") == "high" else ""

        if msg.type == "chat":
            lines.append(f"- [{timestamp}]{priority_marker} {msg.text}")
        elif msg.type == "bash":
            lines.append(f"- [{timestamp}] Bash command: `{msg.text}`")
        elif msg.type == "file":
            lines.append(f"- [{timestamp}] File reference: `{msg.text}`")
        elif msg.type == "task":
            lines.append(f"- [{timestamp}] New task suggestion: {msg.text}")
        elif msg.type == "question":
            lines.append(f"- [{timestamp}] Question: {msg.text}")

    return "\n".join(lines)


class ChatQueue:
    """File-based message queue for chat system.

    Stores messages in JSONL format for easy parsing and durability.
    Uses file locking for thread-safe operations.

    The queue is designed to be written by external processes (users)
    and read by the Zoyd loop. Messages are persisted until explicitly
deleted.

    Attributes:
        path: Path to the chat file (typically .zoyd/chat.txt).
        _lock: Thread lock for concurrent access.
    """

    def __init__(self, path: Path) -> None:
        """Initialize chat queue.

        Args:
            path: Path to the chat file. Parent directory will be created
                if it doesn't exist.
        """
        self.path = path
        self._lock = threading.Lock()

        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def enqueue(self, text: str, msg_type: str = "chat", **metadata: Any) -> None:
        """Add a message to the queue.

        Args:
            text: Message content.
            msg_type: Type of message ("chat", "bash", "file", etc.).
            **metadata: Additional data for the message.
        """
        message = ChatMessage(
            text=text,
            type=msg_type,
            source="user",
            metadata=metadata,
        )

        with self._lock:
            # Append to file in JSONL format
            with open(self.path, "a", encoding="utf-8") as f:
                json.dump(message.to_dict(), f)
                f.write("\n")

    def dequeue_all(self) -> list[ChatMessage]:
        """Read and remove all pending messages.

        Returns:
            List of messages in order received. Returns empty list if
            no messages or file doesn't exist.
        """
        with self._lock:
            if not self.path.exists():
                return []

            # Read all messages
            messages = self._read_all()

            # Clear the file (truncate)
            if messages:
                self.path.write_text("")

            return messages

    def peek(self) -> list[ChatMessage]:
        """Read all messages without removing them.

        Returns:
            List of messages in order received. Returns empty list if
            no messages or file doesn't exist.
        """
        with self._lock:
            return self._read_all()

    def clear(self) -> None:
        """Clear all messages from the queue."""
        with self._lock:
            if self.path.exists():
                self.path.write_text("")

    @property
    def has_messages(self) -> bool:
        """Check if there are pending messages.

        Returns:
            True if queue has at least one message.
        """
        with self._lock:
            if not self.path.exists():
                return False

            # Check if file has content
            try:
                stat = self.path.stat()
                return stat.st_size > 0
            except (OSError, IOError):
                return False

    def _read_all(self) -> list[ChatMessage]:
        """Read all messages from file.

        Internal method - caller must hold lock.

        Returns:
            List of messages, or empty list on error.
        """
        if not self.path.exists():
            return []

        messages = []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        messages.append(ChatMessage.from_dict(data))
                    except (json.JSONDecodeError, KeyError):
                        # Skip malformed lines
                        continue
        except (OSError, IOError):
            return []

        return messages

    def __len__(self) -> int:
        """Return number of pending messages."""
        return len(self.peek())

    def __repr__(self) -> str:
        return f"ChatQueue({self.path}, {len(self)} messages)"
