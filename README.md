# Zoyd

Minimal autonomous agent loop for Claude Code.

Zoyd repeatedly invokes Claude Code against a PRD file, tracking progress across iterations. Each iteration gets fresh context, and tasks are marked complete when their checkbox is checked (`[x]`).

## Installation

```bash
pip install -e .
```

## Usage

### Run the loop

```bash
# Run with defaults (PRD.md in current directory)
zoyd run

# Custom PRD file and iteration limit
zoyd run --prd SPEC.md -n 20

# Use a specific model
zoyd run --model opus

# Dry run - show prompts without executing
zoyd run --dry-run

# Verbose output
zoyd run -v
```

### Check status

```bash
zoyd status              # Show completion status
zoyd status --prd SPEC.md
```

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
6. Repeat until done or max iterations reached

## Exit Codes

- `0` - All tasks complete
- `1` - Max iterations reached
- `2` - Too many consecutive failures
- `130` - Interrupted (Ctrl+C)

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--prd PATH` | PRD file path | `PRD.md` |
| `--progress PATH` | Progress file path | `progress.txt` |
| `-n, --max-iterations N` | Maximum iterations | `10` |
| `--model MODEL` | Claude model (opus, sonnet) | default |
| `--dry-run` | Show prompts without running | false |
| `-v, --verbose` | Verbose output | false |

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
