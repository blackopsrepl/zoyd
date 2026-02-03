"""Session storage backends for Zoyd.

This package provides storage interfaces and implementations for persisting session data:
- interfaces: Abstract base classes and type definitions
- helpers: Serialization utilities and common functions
- in_memory: In-memory storage for testing
- file: JSONL-based file storage for production
- redis: Redis-based storage for distributed systems
- factory: Factory function for creating storage instances

All backends implement the same interface defined in interfaces.py, allowing
seamless switching between storage solutions.
"""

from .factory import create_storage
from .helpers import (
    append_jsonl,
    from_json,
    read_json,
    read_jsonl,
    to_json,
    write_json,
)
from .file import FileStorage
from .in_memory import InMemoryStorage
from .interfaces import SessionStorage
from .redis import RedisStorage

__all__ = [
    # Storage backends
    "SessionStorage",
    "InMemoryStorage", 
    "FileStorage",
    "RedisStorage",
    # Factory
    "create_storage",
    # Serialization helpers
    "to_json",
    "from_json",
    "append_jsonl",
    "read_jsonl",
    "write_json",
    "read_json",
]