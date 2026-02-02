"""Tests for the chat queue system."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from zoyd.chat import ChatMessage, ChatQueue, format_messages_for_prompt, parse_command


class TestChatMessage:
    """Test ChatMessage dataclass."""

    def test_create_basic_message(self):
        """Create a basic chat message."""
        msg = ChatMessage(text="Hello world")
        assert msg.text == "Hello world"
        assert msg.type == "chat"
        assert msg.source == "user"
        assert isinstance(msg.timestamp, datetime)

    def test_create_message_with_type(self):
        """Create message with specific type."""
        msg = ChatMessage(text="ls -la", type="bash")
        assert msg.type == "bash"
        assert msg.text == "ls -la"

    def test_message_with_metadata(self):
        """Create message with metadata."""
        msg = ChatMessage(
            text="Check this file",
            type="file",
            metadata={"filepath": "src/main.py", "line": 42}
        )
        assert msg.metadata["filepath"] == "src/main.py"
        assert msg.metadata["line"] == 42

    def test_to_dict(self):
        """Convert message to dictionary."""
        msg = ChatMessage(text="Test", type="chat")
        data = msg.to_dict()
        assert data["text"] == "Test"
        assert data["type"] == "chat"
        assert "timestamp" in data
        assert data["source"] == "user"

    def test_from_dict(self):
        """Create message from dictionary."""
        data = {
            "text": "Hello",
            "type": "bash",
            "timestamp": datetime.now().isoformat(),
            "source": "user",
            "metadata": {"command": "ls"},
        }
        msg = ChatMessage.from_dict(data)
        assert msg.text == "Hello"
        assert msg.type == "bash"
        assert msg.metadata["command"] == "ls"

    def test_roundtrip_serialization(self):
        """Message survives dict -> from_dict roundtrip."""
        original = ChatMessage(
            text="Test message",
            type="file",
            metadata={"path": "/tmp/test"}
        )
        data = original.to_dict()
        restored = ChatMessage.from_dict(data)
        assert restored.text == original.text
        assert restored.type == original.type
        assert restored.metadata == original.metadata


class TestChatQueue:
    """Test ChatQueue operations."""

    @pytest.fixture
    def temp_chat_file(self, tmp_path):
        """Create a temporary chat file."""
        return tmp_path / "chat.txt"

    @pytest.fixture
    def queue(self, temp_chat_file):
        """Create a chat queue with temp file."""
        return ChatQueue(temp_chat_file)

    def test_create_queue_creates_directory(self, tmp_path):
        """Queue creates parent directory if needed."""
        nested_path = tmp_path / "nested" / "dir" / "chat.txt"
        queue = ChatQueue(nested_path)
        assert nested_path.parent.exists()

    def test_enqueue_creates_file(self, queue, temp_chat_file):
        """Enqueue creates the chat file."""
        queue.enqueue("Hello")
        assert temp_chat_file.exists()

    def test_enqueue_single_message(self, queue):
        """Enqueue a single message."""
        queue.enqueue("Test message")
        assert queue.has_messages
        assert len(queue) == 1

    def test_enqueue_multiple_messages(self, queue):
        """Enqueue multiple messages."""
        queue.enqueue("First")
        queue.enqueue("Second")
        queue.enqueue("Third")
        assert len(queue) == 3

    def test_enqueue_with_type(self, queue):
        """Enqueue message with specific type."""
        queue.enqueue("ls -la", "bash")
        messages = queue.peek()
        assert messages[0].type == "bash"

    def test_enqueue_with_metadata(self, queue):
        """Enqueue message with metadata."""
        queue.enqueue("Check file", "file", filepath="src/main.py")
        messages = queue.peek()
        assert messages[0].metadata["filepath"] == "src/main.py"

    def test_peek_reads_without_removing(self, queue):
        """Peek doesn't remove messages."""
        queue.enqueue("Test")
        first_peek = queue.peek()
        second_peek = queue.peek()
        assert len(first_peek) == 1
        assert len(second_peek) == 1
        assert queue.has_messages

    def test_dequeue_all_removes_messages(self, queue):
        """Dequeue removes all messages."""
        queue.enqueue("First")
        queue.enqueue("Second")
        messages = queue.dequeue_all()
        assert len(messages) == 2
        assert not queue.has_messages
        assert len(queue) == 0

    def test_dequeue_all_returns_empty_list_when_empty(self, queue):
        """Dequeue returns empty list when no messages."""
        messages = queue.dequeue_all()
        assert messages == []

    def test_dequeue_all_returns_empty_list_when_file_missing(self, tmp_path):
        """Dequeue handles missing file gracefully."""
        queue = ChatQueue(tmp_path / "nonexistent" / "chat.txt")
        messages = queue.dequeue_all()
        assert messages == []

    def test_clear_removes_all_messages(self, queue):
        """Clear removes all messages."""
        queue.enqueue("Test")
        queue.clear()
        assert not queue.has_messages

    def test_has_messages_false_when_empty(self, queue):
        """has_messages returns False when queue empty."""
        assert not queue.has_messages

    def test_has_messages_true_when_has_messages(self, queue):
        """has_messages returns True when messages exist."""
        queue.enqueue("Test")
        assert queue.has_messages

    def test_file_format_is_jsonl(self, queue, temp_chat_file):
        """Messages stored as JSON Lines format."""
        queue.enqueue("First")
        queue.enqueue("Second")
        content = temp_chat_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 2
        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert "text" in data
            assert "timestamp" in data

    def test_handles_corrupted_lines(self, queue, temp_chat_file):
        """Queue skips corrupted lines gracefully."""
        # Write corrupted and valid lines
        with open(temp_chat_file, "w") as f:
            f.write('{"text": "Valid", "timestamp": "2024-01-01T00:00:00"}\n')
            f.write("not valid json\n")
            f.write('{"text": "Also valid", "timestamp": "2024-01-02T00:00:00"}\n')
        messages = queue.peek()
        assert len(messages) == 2
        assert messages[0].text == "Valid"
        assert messages[1].text == "Also valid"

    def test_message_order_preserved(self, queue):
        """Messages kept in FIFO order."""
        queue.enqueue("First")
        queue.enqueue("Second")
        queue.enqueue("Third")
        messages = queue.dequeue_all()
        texts = [m.text for m in messages]
        assert texts == ["First", "Second", "Third"]

    def test_repr(self, queue):
        """Queue has useful repr."""
        queue.enqueue("Test")
        repr_str = repr(queue)
        assert "ChatQueue" in repr_str
        assert "1 messages" in repr_str


class TestChatQueueEdgeCases:
    """Edge cases and error handling."""

    def test_concurrent_access(self, tmp_path):
        """Queue handles basic concurrent access."""
        import threading
        queue = ChatQueue(tmp_path / "chat.txt")
        errors = []

        def writer():
            try:
                for i in range(10):
                    queue.enqueue(f"Message {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(queue) == 30

    def test_empty_message_allowed(self, tmp_path):
        """Empty string messages are allowed."""
        queue = ChatQueue(tmp_path / "chat.txt")
        queue.enqueue("")
        messages = queue.dequeue_all()
        assert len(messages) == 1
        assert messages[0].text == ""

    def test_unicode_handling(self, tmp_path):
        """Unicode text handled correctly."""
        queue = ChatQueue(tmp_path / "chat.txt")
        queue.enqueue("Hello 世界 🌍")
        messages = queue.dequeue_all()
        assert messages[0].text == "Hello 世界 🌍"

    def test_large_message(self, tmp_path):
        """Large messages handled correctly."""
        queue = ChatQueue(tmp_path / "chat.txt")
        large_text = "x" * 10000
        queue.enqueue(large_text)
        messages = queue.dequeue_all()
        assert messages[0].text == large_text


class TestParseCommand:
    """Test command parsing functionality."""

    def test_parse_bash_command(self):
        """Parse !bash prefix."""
        msg_type, text, metadata = parse_command("!bash ls -la")
        assert msg_type == "bash"
        assert text == "ls -la"
        assert metadata == {}

    def test_parse_file_reference(self):
        """Parse @filepath prefix."""
        msg_type, text, metadata = parse_command("@src/main.py")
        assert msg_type == "file"
        assert text == "src/main.py"

    def test_parse_task_command(self):
        """Parse >task prefix."""
        msg_type, text, metadata = parse_command(">task Add more tests")
        assert msg_type == "task"
        assert text == "Add more tests"

    def test_parse_question(self):
        """Parse ?question prefix."""
        msg_type, text, metadata = parse_command("?How does this work?")
        assert msg_type == "question"
        assert text == "How does this work?"

    def test_parse_normal_chat(self):
        """Normal text returns chat type."""
        msg_type, text, metadata = parse_command("Hello world")
        assert msg_type == "chat"
        assert text == "Hello world"

    def test_parse_empty_string(self):
        """Empty string handled gracefully."""
        msg_type, text, metadata = parse_command("")
        assert msg_type == "chat"
        assert text == ""

    def test_parse_whitespace_only(self):
        """Whitespace-only string handled."""
        msg_type, text, metadata = parse_command("   ")
        assert msg_type == "chat"
        assert text == "   "

    def test_parse_with_urgent_marker(self):
        """Detect #urgent marker."""
        msg_type, text, metadata = parse_command("Fix this now #urgent")
        assert msg_type == "chat"
        assert text == "Fix this now"
        assert metadata["priority"] == "high"

    def test_parse_with_important_marker(self):
        """Detect !important marker."""
        msg_type, text, metadata = parse_command("!important Check this")
        assert msg_type == "chat"
        assert text == "Check this"
        assert metadata["priority"] == "high"

    def test_parse_bash_with_urgent(self):
        """Parse bash command with urgent marker."""
        msg_type, text, metadata = parse_command("!bash cat config.py #urgent")
        assert msg_type == "bash"
        assert text == "cat config.py"
        assert metadata["priority"] == "high"

    def test_strips_whitespace_after_removing_markers(self):
        """Clean up whitespace after removing markers."""
        msg_type, text, metadata = parse_command("  !bash   ls   #urgent  ")
        assert msg_type == "bash"
        assert text == "ls"


class TestFormatMessagesForPrompt:
    """Test message formatting for prompts."""

    def test_format_empty_list(self):
        """Empty list returns empty string."""
        result = format_messages_for_prompt([])
        assert result == ""

    def test_format_chat_message(self):
        """Format simple chat message."""
        msg = ChatMessage(text="Hello", type="chat")
        result = format_messages_for_prompt([msg])
        assert "User Messages" in result
        assert "Hello" in result

    def test_format_bash_message(self):
        """Format bash command message."""
        msg = ChatMessage(text="ls -la", type="bash")
        result = format_messages_for_prompt([msg])
        assert "Bash command" in result
        assert "`ls -la`" in result

    def test_format_file_message(self):
        """Format file reference message."""
        msg = ChatMessage(text="src/main.py", type="file")
        result = format_messages_for_prompt([msg])
        assert "File reference" in result

    def test_format_task_message(self):
        """Format task suggestion message."""
        msg = ChatMessage(text="Add tests", type="task")
        result = format_messages_for_prompt([msg])
        assert "New task suggestion" in result

    def test_format_question_message(self):
        """Format question message."""
        msg = ChatMessage(text="How does this work?", type="question")
        result = format_messages_for_prompt([msg])
        assert "Question" in result

    def test_format_with_urgent_priority(self):
        """Format message with urgent priority marker."""
        msg = ChatMessage(
            text="Fix bug",
            type="chat",
            metadata={"priority": "high"}
        )
        result = format_messages_for_prompt([msg])
        assert "[URGENT]" in result

    def test_format_multiple_messages(self):
        """Format multiple messages."""
        messages = [
            ChatMessage(text="First", type="chat"),
            ChatMessage(text="ls -la", type="bash"),
            ChatMessage(text="Add feature", type="task"),
        ]
        result = format_messages_for_prompt(messages)
        assert result.count("- [") == 3  # Three bullet points
        assert "First" in result
        assert "ls -la" in result
        assert "Add feature" in result
