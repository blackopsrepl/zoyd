"""Shared test fixtures."""

from unittest.mock import patch

import pytest

from zoyd.config import ZoydConfig


@pytest.fixture(autouse=True)
def _isolate_config():
    """Prevent tests from reading zoyd.toml on disk.

    LoopRunner.__init__ calls load_config() to resolve None-sentinel
    defaults.  Without this fixture every test that constructs a
    LoopRunner would pick up whatever zoyd.toml happens to sit in the
    working directory, making assertions on default values brittle.

    The fixture patches load_config in the loop module (where it is
    imported) so that it always returns a pristine ZoydConfig with
    dataclass defaults.
    """
    with patch("zoyd.loop.loop.load_config", return_value=ZoydConfig(session_logging=False, storage_backend="file")):
        yield
