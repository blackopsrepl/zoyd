"""Serialization helpers for session storage.

Provides utility functions for JSON serialization and deserialization.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def to_json(obj: Any, indent: int | None = None) -> str:
    """Convert an object to JSON string.

    Args:
        obj: Object to serialize. If it has a to_dict() method, that's used.
        indent: Indentation level for pretty printing (None for compact).

    Returns:
        JSON string representation.
    """
    if hasattr(obj, "to_dict"):
        data = obj.to_dict()
    else:
        data = obj
    return json.dumps(data, indent=indent, default=str)


def from_json(json_str: str, cls: type | None = None) -> Any:
    """Parse JSON string into an object.

    Args:
        json_str: JSON string to parse.
        cls: Optional class with from_dict() method to create instance.

    Returns:
        Parsed object (dict if cls is None, instance of cls otherwise).
    """
    data = json.loads(json_str)
    if cls is not None and hasattr(cls, "from_dict"):
        return cls.from_dict(data)
    return data


def append_jsonl(path: Path, obj: Any) -> None:
    """Append an object as a single JSON line to a file.

    Args:
        path: Path to the JSONL file.
        obj: Object to append (must have to_dict() or be serializable).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(to_json(obj) + "\n")


def read_jsonl(path: Path, cls: type | None = None) -> list[Any]:
    """Read all objects from a JSONL file.

    Args:
        path: Path to the JSONL file.
        cls: Optional class with from_dict() method to create instances.

    Returns:
        List of parsed objects.
    """
    if not path.exists():
        return []
    results = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(from_json(line, cls))
    return results


def write_json(path: Path, obj: Any, indent: int = 2) -> None:
    """Write an object to a JSON file.

    Args:
        path: Path to the JSON file.
        obj: Object to write (must have to_dict() or be serializable).
        indent: Indentation level for pretty printing (default: 2).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(to_json(obj, indent=indent))


def read_json(path: Path, cls: type | None = None) -> Any:
    """Read an object from a JSON file.

    Args:
        path: Path to the JSON file.
        cls: Optional class with from_dict() method to create instance.

    Returns:
        Parsed object (dict if cls is None, instance of cls otherwise).
    """
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return from_json(f.read(), cls)