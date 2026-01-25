"""Tests for the zoyd.tui.spinners module."""

from __future__ import annotations

import io

import pytest

rich = pytest.importorskip("rich")

from rich.console import Console
from rich.live import Live

from zoyd.tui.spinners import (
    DEFAULT_SPINNER,
    SPINNER_DEFS,
    MindFlayerSpinner,
    create_spinner,
    get_spinner_frames,
    get_spinner_interval,
    get_spinner_names,
)


class TestSpinnerDefs:
    """Tests for spinner definitions."""

    def test_spinner_defs_is_dict(self) -> None:
        """SPINNER_DEFS should be a dictionary."""
        assert isinstance(SPINNER_DEFS, dict)

    def test_spinner_defs_has_required_spinners(self) -> None:
        """SPINNER_DEFS should have tentacles, psionic, and void spinners."""
        assert "tentacles" in SPINNER_DEFS
        assert "psionic" in SPINNER_DEFS
        assert "void" in SPINNER_DEFS

    def test_spinner_defs_has_bonus_spinners(self) -> None:
        """SPINNER_DEFS should have mind and elder spinners."""
        assert "mind" in SPINNER_DEFS
        assert "elder" in SPINNER_DEFS

    def test_spinner_def_structure(self) -> None:
        """Each spinner def should be a tuple of (frames, interval)."""
        for name, definition in SPINNER_DEFS.items():
            assert isinstance(definition, tuple), f"{name} should be a tuple"
            assert len(definition) == 2, f"{name} should have 2 elements"
            frames, interval = definition
            assert isinstance(frames, list), f"{name} frames should be a list"
            assert len(frames) > 0, f"{name} should have at least one frame"
            assert isinstance(interval, int), f"{name} interval should be int"
            assert interval > 0, f"{name} interval should be positive"

    def test_default_spinner_exists(self) -> None:
        """DEFAULT_SPINNER should be a valid spinner name."""
        assert DEFAULT_SPINNER in SPINNER_DEFS

    def test_default_spinner_is_psionic(self) -> None:
        """DEFAULT_SPINNER should be psionic."""
        assert DEFAULT_SPINNER == "psionic"


class TestMindFlayerSpinner:
    """Tests for MindFlayerSpinner class."""

    def test_create_default_spinner(self) -> None:
        """Should create a spinner with default settings."""
        spinner = MindFlayerSpinner()
        assert spinner.name == DEFAULT_SPINNER
        assert spinner.text == ""
        assert spinner.style == "zoyd.spinner"

    def test_create_spinner_with_name(self) -> None:
        """Should create a spinner with a specific name."""
        spinner = MindFlayerSpinner(name="tentacles")
        assert spinner.name == "tentacles"

    def test_create_spinner_with_text(self) -> None:
        """Should create a spinner with text."""
        spinner = MindFlayerSpinner(text="Loading...")
        assert spinner.text == "Loading..."

    def test_create_spinner_with_style(self) -> None:
        """Should create a spinner with custom style."""
        spinner = MindFlayerSpinner(style="bold red")
        assert spinner.style == "bold red"

    def test_invalid_name_falls_back_to_default(self) -> None:
        """Invalid spinner name should fall back to default."""
        spinner = MindFlayerSpinner(name="nonexistent")
        assert spinner.name == DEFAULT_SPINNER

    def test_spinner_has_correct_frames(self) -> None:
        """Spinner should have the correct frames from SPINNER_DEFS."""
        for name in SPINNER_DEFS:
            spinner = MindFlayerSpinner(name=name)
            expected_frames = SPINNER_DEFS[name][0]
            assert spinner.spinner.spinner_frames == expected_frames

    def test_spinner_has_correct_interval(self) -> None:
        """Spinner should have the correct interval from SPINNER_DEFS."""
        for name in SPINNER_DEFS:
            spinner = MindFlayerSpinner(name=name)
            expected_interval = SPINNER_DEFS[name][1] / 1000
            assert spinner.spinner.interval == expected_interval

    def test_update_text(self) -> None:
        """Should update spinner text."""
        spinner = MindFlayerSpinner()
        result = spinner.update("New text")
        assert spinner.text == "New text"
        assert result is spinner  # Should return self for chaining

    def test_rich_protocol(self) -> None:
        """Spinner should implement __rich__ protocol."""
        spinner = MindFlayerSpinner()
        rich_obj = spinner.__rich__()
        assert rich_obj is spinner._spinner

    def test_spinner_property(self) -> None:
        """spinner property should return the underlying Spinner."""
        spinner = MindFlayerSpinner()
        assert spinner.spinner is spinner._spinner


class TestCreateSpinner:
    """Tests for create_spinner factory function."""

    def test_create_spinner_default(self) -> None:
        """Should create a default spinner."""
        spinner = create_spinner()
        assert isinstance(spinner, MindFlayerSpinner)
        assert spinner.name == DEFAULT_SPINNER

    def test_create_spinner_with_name(self) -> None:
        """Should create a spinner with specific name."""
        spinner = create_spinner(name="void")
        assert spinner.name == "void"

    def test_create_spinner_with_text(self) -> None:
        """Should create a spinner with text."""
        spinner = create_spinner(text="Processing...")
        assert spinner.text == "Processing..."

    def test_create_spinner_with_style(self) -> None:
        """Should create a spinner with custom style."""
        spinner = create_spinner(style="cyan")
        assert spinner.style == "cyan"


class TestGetSpinnerNames:
    """Tests for get_spinner_names function."""

    def test_returns_list(self) -> None:
        """Should return a list."""
        names = get_spinner_names()
        assert isinstance(names, list)

    def test_contains_all_spinners(self) -> None:
        """Should contain all spinner names."""
        names = get_spinner_names()
        for name in SPINNER_DEFS:
            assert name in names

    def test_correct_length(self) -> None:
        """Should have same length as SPINNER_DEFS."""
        names = get_spinner_names()
        assert len(names) == len(SPINNER_DEFS)


class TestGetSpinnerFrames:
    """Tests for get_spinner_frames function."""

    def test_returns_frames_for_valid_name(self) -> None:
        """Should return frames for a valid spinner name."""
        frames = get_spinner_frames("tentacles")
        assert frames == SPINNER_DEFS["tentacles"][0]

    def test_returns_empty_list_for_invalid_name(self) -> None:
        """Should return empty list for invalid name."""
        frames = get_spinner_frames("nonexistent")
        assert frames == []

    def test_returns_correct_frames_for_each_spinner(self) -> None:
        """Should return correct frames for each defined spinner."""
        for name, (expected_frames, _) in SPINNER_DEFS.items():
            frames = get_spinner_frames(name)
            assert frames == expected_frames


class TestGetSpinnerInterval:
    """Tests for get_spinner_interval function."""

    def test_returns_interval_for_valid_name(self) -> None:
        """Should return interval for a valid spinner name."""
        interval = get_spinner_interval("psionic")
        assert interval == SPINNER_DEFS["psionic"][1]

    def test_returns_zero_for_invalid_name(self) -> None:
        """Should return 0 for invalid name."""
        interval = get_spinner_interval("nonexistent")
        assert interval == 0

    def test_returns_correct_interval_for_each_spinner(self) -> None:
        """Should return correct interval for each defined spinner."""
        for name, (_, expected_interval) in SPINNER_DEFS.items():
            interval = get_spinner_interval(name)
            assert interval == expected_interval


class TestSpinnerRendering:
    """Tests for spinner rendering capabilities."""

    def test_spinner_is_renderable(self) -> None:
        """Spinner should be renderable by Rich console."""
        spinner = MindFlayerSpinner(text="Test")
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        # Just verify it doesn't raise an exception
        console.print(spinner)

    def test_all_spinners_are_renderable(self) -> None:
        """All defined spinners should be renderable."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        for name in SPINNER_DEFS:
            spinner = MindFlayerSpinner(name=name)
            console.print(spinner)


class TestModuleExports:
    """Tests for module exports."""

    def test_import_from_spinners_module(self) -> None:
        """All exports should be importable from spinners module."""
        from zoyd.tui.spinners import (
            DEFAULT_SPINNER,
            SPINNER_DEFS,
            MindFlayerSpinner,
            create_spinner,
            get_spinner_frames,
            get_spinner_interval,
            get_spinner_names,
        )

        assert SPINNER_DEFS is not None
        assert DEFAULT_SPINNER is not None
        assert MindFlayerSpinner is not None
        assert create_spinner is not None
        assert get_spinner_names is not None
        assert get_spinner_frames is not None
        assert get_spinner_interval is not None

    def test_import_from_tui_package(self) -> None:
        """All exports should be importable from tui package."""
        from zoyd.tui import (
            DEFAULT_SPINNER,
            SPINNER_DEFS,
            MindFlayerSpinner,
            create_spinner,
            get_spinner_frames,
            get_spinner_interval,
            get_spinner_names,
        )

        assert SPINNER_DEFS is not None
        assert DEFAULT_SPINNER is not None
        assert MindFlayerSpinner is not None
        assert create_spinner is not None
        assert get_spinner_names is not None
        assert get_spinner_frames is not None
        assert get_spinner_interval is not None
