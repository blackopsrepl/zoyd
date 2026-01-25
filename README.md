# Zoyd

Minimal autonomous agent loop for Claude Code.

Zoyd repeatedly invokes Claude Code against a PRD file, tracking progress across iterations. Each iteration gets fresh context, and tasks are marked complete when their checkbox is checked (`[x]`).

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Create a starter PRD
zoyd init "My Project"

# Edit PRD.md to add your tasks, then run
zoyd run

# Check progress
zoyd status
```

## Usage

### Initialize a PRD

```bash
# Create PRD.md with template
zoyd init "Project Name"

# Custom output path
zoyd init --output docs/tasks.md "Feature Work"

# Overwrite existing
zoyd init --force "New Project"
```

### Run the loop

```bash
# Run with defaults (PRD.md in current directory)
zoyd run

# Custom PRD file and iteration limit
zoyd run --prd SPEC.md -n 20

# Use a specific model
zoyd run --model opus

# Resume from existing progress
zoyd run --resume

# Dry run - show prompts without executing
zoyd run --dry-run

# Disable TUI for plain text output
zoyd run --no-tui

# Set cost limit
zoyd run --max-cost 5.00

# Verbose output
zoyd run -v
```

### Check status

```bash
zoyd status              # Show completion status
zoyd status --prd SPEC.md
zoyd status --json       # Machine-readable output
```

## Configuration

Zoyd can be configured via a `zoyd.toml` file in your project directory. CLI options override config values.

```toml
# zoyd.toml
prd = "PRD.md"
progress = "progress.txt"
max_iterations = 10
model = "sonnet"
delay = 1.0
auto_commit = true
verbose = false
fail_fast = false
max_cost = 10.0

# TUI options
tui_enabled = true
tui_refresh_rate = 4.0
tui_compact = false

# Session logging
session_logging = false
sessions_dir = ".zoyd/sessions"
```

Config can also be nested under a `[zoyd]` section if needed.

## PRD Format

Zoyd parses markdown checkboxes to track tasks:

```markdown
# Project: My App

## Tasks

- [ ] Set up project structure
- [ ] Implement core feature
- [ ] Add tests
- [x] Write documentation (completed)

## Notes

Additional context for Claude goes here.
```

## How It Works

1. Zoyd reads the PRD and progress files
2. If all tasks are complete (`[x]`), exit successfully
3. Build a prompt with PRD content, progress log, and iteration info
4. Invoke Claude Code with `--print --permission-mode acceptEdits`
5. Append Claude's output to the progress file
6. Optionally auto-commit changes after each completed task
7. Repeat until done or max iterations reached

## Exit Codes

- `0` - All tasks complete
- `1` - Max iterations reached
- `2` - Too many consecutive failures
- `130` - Interrupted (Ctrl+C)

## CLI Options

### `zoyd run`

| Option | Description | Default |
|--------|-------------|---------|
| `--prd PATH` | PRD file path | `PRD.md` |
| `--progress PATH` | Progress file path | `progress.txt` |
| `-n, --max-iterations N` | Maximum iterations | `10` |
| `--model MODEL` | Claude model (opus, sonnet) | default |
| `--delay SECONDS` | Pause between iterations | `1.0` |
| `--auto-commit/--no-auto-commit` | Auto-commit after tasks | enabled |
| `--resume` | Resume from existing progress | disabled |
| `--fail-fast` | Exit on first failure | disabled |
| `--max-cost USD` | Cost limit before stopping | none |
| `--no-tui` | Disable Rich TUI | disabled |
| `--session-log/--no-session-log` | Enable session logging | disabled |
| `--sessions-dir PATH` | Session log directory | `.zoyd/sessions` |
| `--dry-run` | Show prompts without running | disabled |
| `-v, --verbose` | Verbose output | disabled |

### `zoyd init`

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output PATH` | Output file path | `PRD.md` |
| `-f, --force` | Overwrite existing file | disabled |

### `zoyd status`

| Option | Description | Default |
|--------|-------------|---------|
| `--prd PATH` | PRD file path | `PRD.md` |
| `--progress PATH` | Progress file path | `progress.txt` |
| `--json` | JSON output format | disabled |

## Example

```bash
# Create a simple PRD
cat > PRD.md << 'EOF'
# Project: Hello

## Tasks
- [ ] Create hello.py that prints "Hello, World!"
- [ ] Add a greet(name) function
EOF

# Run Zoyd
zoyd run -n 5

# Check status
zoyd status
```
