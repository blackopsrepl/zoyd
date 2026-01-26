# Project: Fix Tests for Redis-by-Default

Redis is now the default storage backend with session logging enabled. Tests fail because they run in isolated filesystems without `zoyd.toml`, causing them to use hardcoded defaults and attempt connections to `localhost:6379`.

## Tasks

### Fix LoopRunner to Skip Redis in Dry-Run Mode
- [x] Modify session logging initialization to skip when dry_run=True (zoyd/loop.py)

### Fix test_config.py Tests
- [x] Add --no-session-log flag to test_run_uses_config_defaults (tests/test_config.py)
- [ ] Add --no-session-log flag to test_run_cli_overrides_config (tests/test_config.py)
- [ ] Add --no-session-log flag to test_run_model_from_config (tests/test_config.py)
- [ ] Add --no-session-log flag to test_config_panel_* tests (tests/test_config.py)
- [ ] Add --no-session-log flag to test_tui_enabled_config_controls_no_tui (tests/test_config.py)
- [ ] Add --no-session-log flag to test_no_tui_flag_overrides_config (tests/test_config.py)

### Fix test_loop.py Tests
- [ ] Add --no-session-log or session_logging=False to test_resume_* tests (tests/test_loop.py)
- [ ] Add --no-session-log or session_logging=False to test_fail_fast_* tests (tests/test_loop.py)

## Notes

- The alternative approach of making LoopRunner skip Redis in dry-run mode is cleaner since there's no point logging a dry run
- Modify `zoyd/loop.py` lines 386-396 to check `if self.session_logging and not self.dry_run:`
- Tests that invoke CLI with `--dry-run` don't need session logging functionality

## Success Criteria

- All checkboxes marked `[x]`
- `pytest tests/test_config.py tests/test_loop.py -v` passes
