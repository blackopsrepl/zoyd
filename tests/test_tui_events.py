"""Tests for zoyd.tui.events module."""

import pytest

rich = pytest.importorskip("rich")

from zoyd.tui.events import (
    Event,
    EventEmitter,
    EventHandler,
    EventType,
    create_event_emitter,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_loop_lifecycle_events_exist(self) -> None:
        """Verify loop lifecycle events exist."""
        assert EventType.LOOP_START
        assert EventType.LOOP_END

    def test_iteration_lifecycle_events_exist(self) -> None:
        """Verify iteration lifecycle events exist."""
        assert EventType.ITERATION_START
        assert EventType.ITERATION_END

    def test_claude_events_exist(self) -> None:
        """Verify Claude-related events exist."""
        assert EventType.CLAUDE_INVOKE
        assert EventType.CLAUDE_RESPONSE
        assert EventType.CLAUDE_ERROR

    def test_task_events_exist(self) -> None:
        """Verify task-related events exist."""
        assert EventType.TASK_START
        assert EventType.TASK_COMPLETE
        assert EventType.TASK_BLOCKED

    def test_cost_events_exist(self) -> None:
        """Verify cost-related events exist."""
        assert EventType.COST_UPDATE
        assert EventType.COST_LIMIT_EXCEEDED

    def test_git_events_exist(self) -> None:
        """Verify git-related events exist."""
        assert EventType.COMMIT_START
        assert EventType.COMMIT_SUCCESS
        assert EventType.COMMIT_FAILED

    def test_log_events_exist(self) -> None:
        """Verify logging events exist."""
        assert EventType.LOG_MESSAGE

    def test_all_event_types_unique(self) -> None:
        """Verify all event types have unique values."""
        values = [e.value for e in EventType]
        assert len(values) == len(set(values))


class TestEvent:
    """Tests for Event class."""

    def test_event_creation_minimal(self) -> None:
        """Test creating an event with just type."""
        event = Event(EventType.LOOP_START)
        assert event.type == EventType.LOOP_START
        assert event.data == {}

    def test_event_creation_with_data(self) -> None:
        """Test creating an event with data."""
        data = {"iteration": 5, "task": "Build the thing"}
        event = Event(EventType.ITERATION_START, data)
        assert event.type == EventType.ITERATION_START
        assert event.data == data

    def test_event_get_existing_key(self) -> None:
        """Test getting an existing key from event data."""
        event = Event(EventType.COST_UPDATE, {"cost": 1.25, "total": 3.50})
        assert event.get("cost") == 1.25
        assert event.get("total") == 3.50

    def test_event_get_missing_key_default(self) -> None:
        """Test getting a missing key returns default."""
        event = Event(EventType.LOOP_START)
        assert event.get("nonexistent") is None
        assert event.get("nonexistent", "default") == "default"

    def test_event_repr(self) -> None:
        """Test event string representation."""
        event = Event(EventType.TASK_COMPLETE, {"task": "Test"})
        repr_str = repr(event)
        assert "TASK_COMPLETE" in repr_str
        assert "task" in repr_str


class TestEventEmitter:
    """Tests for EventEmitter class."""

    def test_emitter_creation(self) -> None:
        """Test creating an event emitter."""
        emitter = EventEmitter()
        assert emitter is not None
        assert emitter.handler_count() == 0

    def test_on_registers_handler(self) -> None:
        """Test registering a handler."""
        emitter = EventEmitter()
        calls = []

        def handler(event: Event) -> None:
            calls.append(event)

        emitter.on(EventType.LOOP_START, handler)
        assert emitter.has_handlers(EventType.LOOP_START)
        assert emitter.handler_count(EventType.LOOP_START) == 1

    def test_on_returns_self_for_chaining(self) -> None:
        """Test that on() returns self for method chaining."""
        emitter = EventEmitter()
        result = emitter.on(EventType.LOOP_START, lambda e: None)
        assert result is emitter

    def test_emit_calls_handler(self) -> None:
        """Test that emit calls registered handlers."""
        emitter = EventEmitter()
        calls = []

        def handler(event: Event) -> None:
            calls.append(event)

        emitter.on(EventType.ITERATION_START, handler)
        emitter.emit(EventType.ITERATION_START, {"iteration": 1})

        assert len(calls) == 1
        assert calls[0].type == EventType.ITERATION_START
        assert calls[0].get("iteration") == 1

    def test_emit_returns_event(self) -> None:
        """Test that emit returns the emitted event."""
        emitter = EventEmitter()
        event = emitter.emit(EventType.LOOP_END)
        assert isinstance(event, Event)
        assert event.type == EventType.LOOP_END

    def test_emit_multiple_handlers(self) -> None:
        """Test emitting to multiple handlers."""
        emitter = EventEmitter()
        calls1 = []
        calls2 = []

        emitter.on(EventType.COST_UPDATE, lambda e: calls1.append(e))
        emitter.on(EventType.COST_UPDATE, lambda e: calls2.append(e))

        emitter.emit(EventType.COST_UPDATE, {"cost": 0.50})

        assert len(calls1) == 1
        assert len(calls2) == 1

    def test_emit_does_not_call_other_handlers(self) -> None:
        """Test that emit only calls handlers for the right event type."""
        emitter = EventEmitter()
        calls = []

        emitter.on(EventType.LOOP_START, lambda e: calls.append(e))
        emitter.emit(EventType.LOOP_END)

        assert len(calls) == 0

    def test_on_any_registers_wildcard(self) -> None:
        """Test registering a wildcard handler."""
        emitter = EventEmitter()
        calls = []

        emitter.on_any(lambda e: calls.append(e))
        emitter.emit(EventType.LOOP_START)
        emitter.emit(EventType.ITERATION_START)
        emitter.emit(EventType.CLAUDE_INVOKE)

        assert len(calls) == 3

    def test_on_any_returns_self(self) -> None:
        """Test that on_any returns self for chaining."""
        emitter = EventEmitter()
        result = emitter.on_any(lambda e: None)
        assert result is emitter

    def test_once_handler_called_once(self) -> None:
        """Test that once handler is only called once."""
        emitter = EventEmitter()
        calls = []

        emitter.once(EventType.TASK_COMPLETE, lambda e: calls.append(e))
        emitter.emit(EventType.TASK_COMPLETE)
        emitter.emit(EventType.TASK_COMPLETE)

        assert len(calls) == 1

    def test_once_returns_self(self) -> None:
        """Test that once returns self for chaining."""
        emitter = EventEmitter()
        result = emitter.once(EventType.LOOP_START, lambda e: None)
        assert result is emitter

    def test_off_removes_handler(self) -> None:
        """Test removing a handler."""
        emitter = EventEmitter()
        calls = []

        def handler(event: Event) -> None:
            calls.append(event)

        emitter.on(EventType.LOOP_START, handler)
        emitter.off(EventType.LOOP_START, handler)
        emitter.emit(EventType.LOOP_START)

        assert len(calls) == 0
        assert not emitter.has_handlers(EventType.LOOP_START)

    def test_off_returns_self(self) -> None:
        """Test that off returns self for chaining."""
        emitter = EventEmitter()
        result = emitter.off(EventType.LOOP_START, lambda e: None)
        assert result is emitter

    def test_off_any_removes_wildcard(self) -> None:
        """Test removing a wildcard handler."""
        emitter = EventEmitter()
        calls = []
        handler = lambda e: calls.append(e)

        emitter.on_any(handler)
        emitter.off_any(handler)
        emitter.emit(EventType.LOOP_START)

        assert len(calls) == 0

    def test_off_any_returns_self(self) -> None:
        """Test that off_any returns self for chaining."""
        emitter = EventEmitter()
        result = emitter.off_any(lambda e: None)
        assert result is emitter

    def test_off_all_clears_specific_type(self) -> None:
        """Test clearing all handlers for a specific type."""
        emitter = EventEmitter()
        emitter.on(EventType.LOOP_START, lambda e: None)
        emitter.on(EventType.LOOP_START, lambda e: None)
        emitter.on(EventType.LOOP_END, lambda e: None)

        emitter.off_all(EventType.LOOP_START)

        assert not emitter.has_handlers(EventType.LOOP_START)
        assert emitter.has_handlers(EventType.LOOP_END)

    def test_off_all_clears_everything(self) -> None:
        """Test clearing all handlers."""
        emitter = EventEmitter()
        emitter.on(EventType.LOOP_START, lambda e: None)
        emitter.on(EventType.LOOP_END, lambda e: None)
        emitter.on_any(lambda e: None)

        emitter.off_all()

        assert emitter.handler_count() == 0

    def test_off_all_returns_self(self) -> None:
        """Test that off_all returns self for chaining."""
        emitter = EventEmitter()
        result = emitter.off_all()
        assert result is emitter

    def test_has_handlers_with_type(self) -> None:
        """Test has_handlers with specific type."""
        emitter = EventEmitter()
        assert not emitter.has_handlers(EventType.LOOP_START)

        emitter.on(EventType.LOOP_START, lambda e: None)
        assert emitter.has_handlers(EventType.LOOP_START)
        assert not emitter.has_handlers(EventType.LOOP_END)

    def test_has_handlers_includes_wildcards(self) -> None:
        """Test that has_handlers includes wildcard handlers."""
        emitter = EventEmitter()
        emitter.on_any(lambda e: None)

        # Wildcard counts for any specific type
        assert emitter.has_handlers(EventType.LOOP_START)
        assert emitter.has_handlers(EventType.TASK_COMPLETE)

    def test_has_handlers_any(self) -> None:
        """Test has_handlers without type checks all handlers."""
        emitter = EventEmitter()
        assert not emitter.has_handlers()

        emitter.on(EventType.LOOP_START, lambda e: None)
        assert emitter.has_handlers()

    def test_handler_count_with_type(self) -> None:
        """Test handler_count with specific type."""
        emitter = EventEmitter()
        emitter.on(EventType.LOOP_START, lambda e: None)
        emitter.on(EventType.LOOP_START, lambda e: None)
        emitter.on(EventType.LOOP_END, lambda e: None)

        assert emitter.handler_count(EventType.LOOP_START) == 2
        assert emitter.handler_count(EventType.LOOP_END) == 1

    def test_handler_count_includes_wildcards(self) -> None:
        """Test that handler_count includes wildcard handlers."""
        emitter = EventEmitter()
        emitter.on(EventType.LOOP_START, lambda e: None)
        emitter.on_any(lambda e: None)

        # 1 specific + 1 wildcard
        assert emitter.handler_count(EventType.LOOP_START) == 2

    def test_handler_count_total(self) -> None:
        """Test handler_count without type counts all handlers."""
        emitter = EventEmitter()
        emitter.on(EventType.LOOP_START, lambda e: None)
        emitter.on(EventType.LOOP_END, lambda e: None)
        emitter.on_any(lambda e: None)

        assert emitter.handler_count() == 3

    def test_method_chaining(self) -> None:
        """Test method chaining works as expected."""
        emitter = EventEmitter()
        calls = []

        (
            emitter
            .on(EventType.LOOP_START, lambda e: calls.append("start"))
            .on(EventType.LOOP_END, lambda e: calls.append("end"))
            .on_any(lambda e: calls.append("any"))
        )

        emitter.emit(EventType.LOOP_START)
        assert calls == ["start", "any"]


class TestCreateEventEmitter:
    """Tests for create_event_emitter factory function."""

    def test_returns_emitter(self) -> None:
        """Test that factory returns an EventEmitter."""
        emitter = create_event_emitter()
        assert isinstance(emitter, EventEmitter)

    def test_returns_new_instance(self) -> None:
        """Test that factory returns a new instance each time."""
        emitter1 = create_event_emitter()
        emitter2 = create_event_emitter()
        assert emitter1 is not emitter2

    def test_emitter_is_empty(self) -> None:
        """Test that factory returns an empty emitter."""
        emitter = create_event_emitter()
        assert emitter.handler_count() == 0


class TestModuleExports:
    """Tests for module exports."""

    def test_import_from_tui(self) -> None:
        """Test that events can be imported from tui package."""
        from zoyd.tui import (
            Event,
            EventEmitter,
            EventHandler,
            EventType,
            create_event_emitter,
        )

        assert EventType is not None
        assert EventEmitter is not None
        assert Event is not None
        assert EventHandler is not None
        assert create_event_emitter is not None

    def test_event_handler_type_alias(self) -> None:
        """Test that EventHandler type alias works."""
        from zoyd.tui.events import EventHandler

        def my_handler(event: Event) -> None:
            pass

        # Type alias should be callable
        handler: EventHandler = my_handler
        assert callable(handler)
