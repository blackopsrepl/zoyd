"""Tests for zoyd.config module."""

import pytest
from pathlib import Path
from click.testing import CliRunner

from zoyd.config import ZoydConfig, find_config_file, load_config, CONFIG_FILENAME
from zoyd.cli import cli


class TestZoydConfig:
    """Tests for ZoydConfig dataclass."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = ZoydConfig()
        assert config.prd == "PRD.md"
        assert config.progress == "progress.txt"
        assert config.max_iterations == 10
        assert config.model is None
        assert config.delay == 1.0
        assert config.auto_commit is True
        assert config.verbose is False
        assert config.fail_fast is False

    def test_from_dict_all_values(self):
        """from_dict loads all config values."""
        data = {
            "prd": "custom.md",
            "progress": "custom_progress.txt",
            "max_iterations": 5,
            "model": "opus",
            "delay": 2.5,
            "auto_commit": False,
            "verbose": True,
            "fail_fast": True,
        }
        config = ZoydConfig.from_dict(data)
        assert config.prd == "custom.md"
        assert config.progress == "custom_progress.txt"
        assert config.max_iterations == 5
        assert config.model == "opus"
        assert config.delay == 2.5
        assert config.auto_commit is False
        assert config.verbose is True
        assert config.fail_fast is True

    def test_from_dict_partial_values(self):
        """from_dict uses defaults for missing values."""
        data = {"prd": "custom.md", "max_iterations": 20}
        config = ZoydConfig.from_dict(data)
        assert config.prd == "custom.md"
        assert config.progress == "progress.txt"  # default
        assert config.max_iterations == 20
        assert config.model is None  # default
        assert config.delay == 1.0  # default

    def test_from_dict_empty(self):
        """from_dict with empty dict returns defaults."""
        config = ZoydConfig.from_dict({})
        assert config.prd == "PRD.md"
        assert config.max_iterations == 10

    def test_from_dict_model_none(self):
        """from_dict handles None model correctly."""
        data = {"model": None}
        config = ZoydConfig.from_dict(data)
        assert config.model is None


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_finds_config_in_current_dir(self, tmp_path):
        """Finds config file in current directory."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("prd = 'test.md'\n")

        result = find_config_file(tmp_path)
        assert result == config_file

    def test_finds_config_in_parent_dir(self, tmp_path):
        """Finds config file in parent directory."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("prd = 'test.md'\n")
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = find_config_file(subdir)
        assert result == config_file

    def test_finds_config_multiple_levels_up(self, tmp_path):
        """Finds config file multiple levels up."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("prd = 'test.md'\n")
        subdir = tmp_path / "a" / "b" / "c"
        subdir.mkdir(parents=True)

        result = find_config_file(subdir)
        assert result == config_file

    def test_returns_none_when_not_found(self, tmp_path):
        """Returns None when no config file exists."""
        # Use a subdir to avoid accidentally finding config in repo root
        subdir = tmp_path / "isolated"
        subdir.mkdir()

        result = find_config_file(subdir)
        assert result is None

    def test_prefers_closest_config(self, tmp_path):
        """Prefers config file closer to start_dir."""
        parent_config = tmp_path / CONFIG_FILENAME
        parent_config.write_text("prd = 'parent.md'\n")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        child_config = subdir / CONFIG_FILENAME
        child_config.write_text("prd = 'child.md'\n")

        result = find_config_file(subdir)
        assert result == child_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_loads_from_explicit_path(self, tmp_path):
        """Loads config from explicit path."""
        config_file = tmp_path / "custom_config.toml"
        config_file.write_text('prd = "explicit.md"\nmax_iterations = 15\n')

        config = load_config(config_file)
        assert config.prd == "explicit.md"
        assert config.max_iterations == 15

    def test_returns_defaults_when_file_missing(self, tmp_path):
        """Returns defaults when config file doesn't exist."""
        config = load_config(tmp_path / "nonexistent.toml")
        assert config.prd == "PRD.md"
        assert config.max_iterations == 10

    def test_returns_defaults_when_path_none(self, tmp_path, monkeypatch):
        """Returns defaults when no config file found."""
        # Change to isolated temp dir to avoid finding repo's config
        monkeypatch.chdir(tmp_path)
        config = load_config(None)
        assert config.prd == "PRD.md"

    def test_loads_root_level_config(self, tmp_path):
        """Loads config values from root level."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("""
prd = "root_level.md"
progress = "root_progress.txt"
max_iterations = 25
model = "sonnet"
delay = 3.0
auto_commit = false
verbose = true
fail_fast = true
""")
        config = load_config(config_file)
        assert config.prd == "root_level.md"
        assert config.progress == "root_progress.txt"
        assert config.max_iterations == 25
        assert config.model == "sonnet"
        assert config.delay == 3.0
        assert config.auto_commit is False
        assert config.verbose is True
        assert config.fail_fast is True

    def test_loads_zoyd_section_config(self, tmp_path):
        """Loads config values from [zoyd] section."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("""
[zoyd]
prd = "section_level.md"
max_iterations = 30
""")
        config = load_config(config_file)
        assert config.prd == "section_level.md"
        assert config.max_iterations == 30


class TestCLIConfigIntegration:
    """Tests for CLI integration with config file."""

    def test_run_help_mentions_config(self):
        """run command help mentions zoyd.toml."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "zoyd.toml" in result.output

    def test_status_help_mentions_config(self):
        """status command help mentions zoyd.toml."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])
        assert "zoyd.toml" in result.output

    def test_run_uses_config_defaults(self, tmp_path):
        """run command uses config file defaults."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config file
            Path("zoyd.toml").write_text('prd = "custom.md"\nmax_iterations = 3\n')
            # Create the PRD file
            Path("custom.md").write_text("# Test PRD\n- [ ] Task 1\n")

            result = runner.invoke(cli, ["run", "--dry-run"])
            # Should use custom.md from config
            assert "PRD: custom.md" in result.output
            assert "Max iterations: 3" in result.output

    def test_run_cli_overrides_config(self, tmp_path):
        """CLI options override config file values."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config file with defaults
            Path("zoyd.toml").write_text('prd = "config.md"\nmax_iterations = 5\n')
            # Create both PRD files
            Path("config.md").write_text("# Config PRD\n- [ ] Task\n")
            Path("override.md").write_text("# Override PRD\n- [ ] Task\n")

            result = runner.invoke(cli, ["run", "--dry-run", "--prd", "override.md", "-n", "7"])
            # Should use CLI values
            assert "PRD: override.md" in result.output
            assert "Max iterations: 7" in result.output

    def test_status_uses_config_defaults(self, tmp_path):
        """status command uses config file defaults."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config file
            Path("zoyd.toml").write_text('prd = "status_test.md"\n')
            # Create PRD file
            Path("status_test.md").write_text("# Test\n- [x] Done\n- [ ] Todo\n")

            result = runner.invoke(cli, ["status"])
            assert "PRD: status_test.md" in result.output
            assert "Tasks: 1/2 complete" in result.output

    def test_status_cli_overrides_config(self, tmp_path):
        """status CLI options override config values."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config file
            Path("zoyd.toml").write_text('prd = "config.md"\n')
            Path("config.md").write_text("# Config\n- [ ] Task\n")
            Path("override.md").write_text("# Override\n- [x] Done\n")

            result = runner.invoke(cli, ["status", "--prd", "override.md"])
            assert "PRD: override.md" in result.output
            assert "Tasks: 1/1 complete" in result.output

    def test_run_model_from_config(self, tmp_path):
        """run command uses model from config."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("zoyd.toml").write_text('prd = "test.md"\nmodel = "opus"\n')
            Path("test.md").write_text("# Test\n- [ ] Task\n")

            result = runner.invoke(cli, ["run", "--dry-run"])
            assert "Model: opus" in result.output

    def test_missing_prd_shows_error(self, tmp_path):
        """Shows error when PRD from config doesn't exist."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("zoyd.toml").write_text('prd = "nonexistent.md"\n')

            result = runner.invoke(cli, ["run"])
            assert result.exit_code == 1
            assert "Error: PRD file 'nonexistent.md' does not exist" in result.output
