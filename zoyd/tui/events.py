"""Event system for the Zoyd TUI dashboard.

Provides an EventType enum defining all events emitted during the loop,
and an EventEmitter class for subscribing to and emitting events.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from typing import Any


class EventType(Enum):
    """Types of events emitted during the Zoyd loop.

    Events are organized by phase:
    - Loop lifecycle: LOOP_START, LOOP_END
    - Iteration lifecycle: ITERATION_START, ITERATION_END
    - Claude invocation: CLAUDE_INVOKE, CLAUDE_RESPONSE, CLAUDE_ERROR
    - Task progress: TASK_START, TASK_COMPLETE, TASK_BLOCKED
    - Cost tracking: COST_UPDATE, COST_LIMIT_EXCEEDED
    - Git operations: COMMIT_START, COMMIT_SUCCESS, COMMIT_FAILED
    - Logging: LOG_MESSAGE
    """

    # Loop lifecycle
    LOOP_START = auto()
    LOOP_END = auto()

    # Iteration lifecycle
    ITERATION_START = auto()
    ITERATION_END = auto()

    # Claude invocation
    CLAUDE_INVOKE = auto()
    CLAUDE_RESPONSE = auto()
    CLAUDE_ERROR = auto()

    # Task progress
    TASK_START = auto()
    TASK_COMPLETE = auto()
    TASK_BLOCKED = auto()

    # Cost tracking
    COST_UPDATE = auto()
    COST_LIMIT_EXCEEDED = auto()

    # Git operations
    COMMIT_START = auto()
    COMMIT_SUCCESS = auto()
    COMMIT_FAILED = auto()

    # Logging
    LOG_MESSAGE = auto()


# Type alias for event handlers
EventHandler = Callable[["Event"], None]


class Event:
    """An event emitted during the Zoyd loop.

    Attributes:
        type: The type of event.
        data: Optional data associated with the event.
    """

    __slots__ = ("type", "data")

    def __init__(self, event_type: EventType, data: dict[str, Any] | None = None) -> None:
        """Initialize an event.

        Args:
            event_type: The type of event.
            data: Optional data dictionary with event-specific payload.
        """
        self.type = event_type
        self.data = data or {}

    def __repr__(self) -> str:
        """Return string representation of the event."""
        return f"Event({self.type.name}, {self.data})"

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the event data.

        Args:
            key: The key to look up.
            default: Default value if key not found.

        Returns:
            The value from data, or default.
        """
        return self.data.get(key, default)


class EventEmitter:
    """Event emitter for the Zoyd loop.

    Allows registering handlers for specific event types and emitting events.
    Supports:
    - Registering handlers for specific event types
    - Registering handlers for all events (wildcard)
    - One-time handlers that auto-unregister after first call
    - Unregistering handlers
    """

    def __init__(self) -> None:
        """Initialize the event emitter."""
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._wildcard_handlers: list[EventHandler] = []
        self._once_handlers: set[EventHandler] = set()

    def on(self, event_type: EventType, handler: EventHandler) -> EventEmitter:
        """Register a handler for a specific event type.

        Args:
            event_type: The event type to listen for.
            handler: Function to call when event is emitted.

        Returns:
            Self for method chaining.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        return self

    def on_any(self, handler: EventHandler) -> EventEmitter:
        """Register a handler for all events (wildcard).

        Args:
            handler: Function to call for any event.

        Returns:
            Self for method chaining.
        """
        self._wildcard_handlers.append(handler)
        return self

    def once(self, event_type: EventType, handler: EventHandler) -> EventEmitter:
        """Register a one-time handler that auto-unregisters after first call.

        Args:
            event_type: The event type to listen for.
            handler: Function to call when event is emitted (only once).

        Returns:
            Self for method chaining.
        """
        self._once_handlers.add(handler)
        return self.on(event_type, handler)

    def off(self, event_type: EventType, handler: EventHandler) -> EventEmitter:
        """Unregister a handler for a specific event type.

        Args:
            event_type: The event type.
            handler: The handler to remove.

        Returns:
            Self for method chaining.
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            self._once_handlers.discard(handler)
        return self

    def off_any(self, handler: EventHandler) -> EventEmitter:
        """Unregister a wildcard handler.

        Args:
            handler: The handler to remove.

        Returns:
            Self for method chaining.
        """
        if handler in self._wildcard_handlers:
            self._wildcard_handlers.remove(handler)
        return self

    def off_all(self, event_type: EventType | None = None) -> EventEmitter:
        """Remove all handlers for an event type, or all handlers if no type given.

        Args:
            event_type: The event type to clear, or None to clear all.

        Returns:
            Self for method chaining.
        """
        if event_type is None:
            self._handlers.clear()
            self._wildcard_handlers.clear()
            self._once_handlers.clear()
        elif event_type in self._handlers:
            # Remove from once_handlers too
            for handler in self._handlers[event_type]:
                self._once_handlers.discard(handler)
            del self._handlers[event_type]
        return self

    def emit(self, event_type: EventType, data: dict[str, Any] | None = None) -> Event:
        """Emit an event to all registered handlers.

        Args:
            event_type: The type of event to emit.
            data: Optional data dictionary for the event.

        Returns:
            The emitted Event object.
        """
        event = Event(event_type, data)

        # Call type-specific handlers
        handlers_to_remove = []
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(event)
                if handler in self._once_handlers:
                    handlers_to_remove.append((event_type, handler))

        # Call wildcard handlers
        for handler in self._wildcard_handlers:
            handler(event)

        # Remove once handlers after iteration
        for et, h in handlers_to_remove:
            self.off(et, h)

        return event

    def has_handlers(self, event_type: EventType | None = None) -> bool:
        """Check if there are any handlers registered.

        Args:
            event_type: Check for specific type, or None to check all.

        Returns:
            True if handlers exist.
        """
        if event_type is None:
            return bool(self._handlers) or bool(self._wildcard_handlers)
        return bool(self._handlers.get(event_type)) or bool(self._wildcard_handlers)

    def handler_count(self, event_type: EventType | None = None) -> int:
        """Get the number of handlers registered.

        Args:
            event_type: Count for specific type, or None for total.

        Returns:
            Number of handlers.
        """
        if event_type is None:
            total = len(self._wildcard_handlers)
            for handlers in self._handlers.values():
                total += len(handlers)
            return total
        return len(self._handlers.get(event_type, [])) + len(self._wildcard_handlers)


def create_event_emitter() -> EventEmitter:
    """Create a new event emitter.

    Factory function for creating EventEmitter instances.

    Returns:
        A new EventEmitter instance.
    """
    return EventEmitter()
