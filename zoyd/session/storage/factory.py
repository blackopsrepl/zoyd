"""Factory function for creating storage backends.

Provides a unified interface for creating storage instances based on configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .file import FileStorage
from .interfaces import SessionStorage
from .redis import RedisStorage

if TYPE_CHECKING:
    from zoyd.config import ZoydConfig


def create_storage(
    config: "ZoydConfig | None" = None,
    backend: str | None = None,
    sessions_dir: str | None = None,
    redis_host: str | None = None,
    redis_port: int | None = None,
    redis_db: int | None = None,
    redis_password: str | None = None,
) -> SessionStorage:
    """Create a storage backend based on configuration.

    Factory function that returns either a FileStorage or RedisStorage
    instance based on the storage_backend setting.

    Args:
        config: ZoydConfig to use for settings. If provided, other args
                are used as overrides.
        backend: Storage backend type ("file" or "redis"). Overrides config.
        sessions_dir: Directory for file storage. Overrides config.
        redis_host: Redis server hostname. Overrides config.
        redis_port: Redis server port. Overrides config.
        redis_db: Redis database number. Overrides config.
        redis_password: Redis password. Overrides config.

    Returns:
        SessionStorage instance (FileStorage or RedisStorage).

    Raises:
        ValueError: If an unknown backend type is specified.
    """
    # Get defaults from config if provided
    if config is not None:
        _backend = backend if backend is not None else config.storage_backend
        _sessions_dir = sessions_dir if sessions_dir is not None else config.sessions_dir
        _redis_host = redis_host if redis_host is not None else config.redis_host
        _redis_port = redis_port if redis_port is not None else config.redis_port
        _redis_db = redis_db if redis_db is not None else config.redis_db
        _redis_password = redis_password if redis_password is not None else config.redis_password
    else:
        _backend = backend if backend is not None else "file"
        _sessions_dir = sessions_dir if sessions_dir is not None else ".zoyd/sessions"
        _redis_host = redis_host if redis_host is not None else "localhost"
        _redis_port = redis_port if redis_port is not None else 6379
        _redis_db = redis_db if redis_db is not None else 0
        _redis_password = redis_password

    if _backend == "file":
        return FileStorage(base_path=_sessions_dir)
    elif _backend == "redis":
        return RedisStorage(
            host=_redis_host,
            port=_redis_port,
            db=_redis_db,
            password=_redis_password,
        )
    else:
        raise ValueError(f"Unknown storage backend: {_backend!r}. Use 'file' or 'redis'.")