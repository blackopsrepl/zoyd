"""Session logging and persistence for Zoyd.

This package provides infrastructure for persisting all session interactions,
statistics, and events for future querying and analysis.

Classes:
    SessionLogger: Main logger class that subscribes to LoopRunner events
    SessionStorage: Abstract base class for storage backends
    InMemoryStorage: In-memory storage for testing
    FileStorage: JSONL-based file storage for production

Data Models:
    SessionMetadata: Core session info (UUID, timestamps, config)
    SessionEvent: Individual event records
    ClaudeOutput: Full Claude response storage
    TaskTransition: Task state change records
    GitCommitRecord: Git commit metadata
    SessionStatistics: Aggregated statistics
    Session: Complete session combining all data

Example:
    from zoyd.session import SessionLogger, FileStorage

    logger = SessionLogger(storage=FileStorage(".zoyd/sessions"))
    logger.subscribe_to(runner.events)
    session_id = logger.start_session(config, working_dir="/path/to/repo")
    # ... run loop ...
    logger.end_session(exit_code=0, exit_reason="complete")
"""

from zoyd.session.logger import SessionLogger, create_session_logger
from zoyd.session.models import (
    ClaudeOutput,
    GitCommitRecord,
    Session,
    SessionEvent,
    SessionMetadata,
    SessionStatistics,
    TaskTransition,
)
from zoyd.session.storage import (
    FileStorage,
    InMemoryStorage,
    RedisStorage,
    SessionStorage,
    append_jsonl,
    create_storage,
    from_json,
    read_json,
    read_jsonl,
    to_json,
    write_json,
)

__all__ = [
    # Logger
    "SessionLogger",
    "create_session_logger",
    # Storage
    "SessionStorage",
    "InMemoryStorage",
    "FileStorage",
    "RedisStorage",
    "create_storage",
    # Models
    "SessionMetadata",
    "SessionEvent",
    "ClaudeOutput",
    "TaskTransition",
    "GitCommitRecord",
    "SessionStatistics",
    "Session",
    # Serialization helpers
    "to_json",
    "from_json",
    "append_jsonl",
    "read_jsonl",
    "write_json",
    "read_json",
]
