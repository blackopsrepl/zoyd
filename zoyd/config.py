"""Configuration file loading for Zoyd."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


CONFIG_FILENAME = "zoyd.toml"


@dataclass
class ZoydConfig:
    """Configuration loaded from zoyd.toml."""

    prd: str = "PRD.md"
    progress: str = "progress.txt"
    max_iterations: int = 10
    model: str | None = None
    delay: float = 1.0
    auto_commit: bool = True
    verbose: bool = False
    fail_fast: bool = False
    max_cost: float | None = None
    # TUI options
    tui_enabled: bool = True
    tui_refresh_rate: float = 4.0  # Dashboard refresh rate in Hz
    tui_compact: bool = False  # Use compact banner for narrow terminals

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ZoydConfig":
        """Create config from a dictionary (parsed TOML)."""
        config = cls()
        if "prd" in data:
            config.prd = str(data["prd"])
        if "progress" in data:
            config.progress = str(data["progress"])
        if "max_iterations" in data:
            config.max_iterations = int(data["max_iterations"])
        if "model" in data:
            config.model = str(data["model"]) if data["model"] else None
        if "delay" in data:
            config.delay = float(data["delay"])
        if "auto_commit" in data:
            config.auto_commit = bool(data["auto_commit"])
        if "verbose" in data:
            config.verbose = bool(data["verbose"])
        if "fail_fast" in data:
            config.fail_fast = bool(data["fail_fast"])
        if "max_cost" in data:
            config.max_cost = float(data["max_cost"]) if data["max_cost"] else None
        # TUI options
        if "tui_enabled" in data:
            config.tui_enabled = bool(data["tui_enabled"])
        if "tui_refresh_rate" in data:
            config.tui_refresh_rate = float(data["tui_refresh_rate"])
        if "tui_compact" in data:
            config.tui_compact = bool(data["tui_compact"])
        return config


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Find zoyd.toml in current directory or parents.

    Args:
        start_dir: Directory to start searching from (default: current directory)

    Returns:
        Path to zoyd.toml if found, None otherwise
    """
    if start_dir is None:
        start_dir = Path.cwd()

    current = start_dir.resolve()
    while True:
        config_path = current / CONFIG_FILENAME
        if config_path.exists():
            return config_path
        if current.parent == current:
            # Reached filesystem root
            return None
        current = current.parent


def load_config(config_path: Path | None = None) -> ZoydConfig:
    """Load configuration from zoyd.toml.

    Args:
        config_path: Explicit path to config file. If None, searches for zoyd.toml.

    Returns:
        ZoydConfig with loaded values or defaults if no config file found.
    """
    if config_path is None:
        config_path = find_config_file()

    if config_path is None or not config_path.exists():
        return ZoydConfig()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    # Config can be at root level or under [zoyd] section
    if "zoyd" in data:
        return ZoydConfig.from_dict(data["zoyd"])
    return ZoydConfig.from_dict(data)
