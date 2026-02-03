"""Prompt templates and related utilities for the Zoyd loop."""

import re

# Prompt templates for different modes
PROMPT_TEMPLATE = """You are working on a project defined by the PRD.
Complete the next incomplete task marked with [ ].

When you complete a task:
1. Make code changes
2. Run tests to verify
3. Mark task complete ([ ] -> [x]) in PRD

Status: Iteration {iteration}, {completed}/{total} tasks complete

## Current Task (COMPLETE THIS ONLY)
{current_task}

IMPORTANT: Work on ONLY this task. Do NOT work on other tasks. Do NOT run any git commands (no git add, git commit, git push, etc.).

## PRD (for context only)
{prd_content}

## Progress Log
{progress_content}
"""

PROMPT_TEMPLATE_WITH_MEMORY = """You are working on a project defined by the PRD.
Complete the next incomplete task marked with [ ].

When you complete a task:
1. Make code changes
2. Run tests to verify
3. Mark task complete ([ ] -> [x]) in PRD

Status: Iteration {iteration}, {completed}/{total} tasks complete

## Current Task (COMPLETE THIS ONLY)
{current_task}

IMPORTANT: Work on ONLY this task. Do NOT work on other tasks. Do NOT run any git commands (no git add, git commit, git push, etc.).

## Relevant Context from Past Work
{relevant_context}

## Recent Progress
{recent_progress}

## PRD (for context only)
{prd_content}
"""

# Prompt template for generating commit messages (conventional commits, no signatures)
COMMIT_PROMPT_TEMPLATE = """Generate a git commit message for the changes below.

Changes made this iteration:
{iteration_output}

Task completed: {task_text}

Respond with ONLY the commit message, nothing else."""

# System-level rules for commit message generation (delivered via --append-system-prompt)
COMMIT_SYSTEM_PROMPT = """\
Use Conventional Commits format: <type>(<scope>): <description>
Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert.
Subject line: type(scope): description (72 chars max, lowercase).
Scope is optional but encouraged (e.g., feat(cli): add --json flag).
Body is optional, separated by blank line, explains why not what.
Never add Co-Authored-By, Signed-off-by, or any signature lines to commits.
Never use backticks, code blocks, or any markdown formatting in commit messages."""

# Patterns that indicate Claude cannot complete a task
CANNOT_COMPLETE_PATTERNS = [
    r"(?i)i (?:cannot|can't|am unable to|am not able to) (?:complete|finish|accomplish|do|perform) (?:this|the) task",
    r"(?i)(?:this|the) task (?:cannot|can't) be completed",
    r"(?i)unable to (?:complete|finish|accomplish) (?:this|the) task",
    r"(?i)(?:i'm|i am) (?:blocked|stuck) (?:on|by)",
    r"(?i)(?:cannot|can't) proceed (?:with|further)",
    r"(?i)task (?:is )?(?:impossible|infeasible|not possible)",
    r"(?i)(?:i )?(?:need|require) (?:more information|clarification|help)",
    r"(?i)(?:blocking|blocker|blocked)(?:\s+issue)?:",
    r"(?i)this (?:is )?beyond (?:my|the) (?:capabilities|ability|scope)",
]


def detect_cannot_complete(output: str) -> tuple[bool, str | None]:
    """Detect if Claude's output indicates it cannot complete the task.

    Args:
        output: Claude's output text.

    Returns:
        Tuple of (detected, matched_pattern). If detected is True, matched_pattern
        contains the first matching phrase found.
    """
    for pattern in CANNOT_COMPLETE_PATTERNS:
        match = re.search(pattern, output)
        if match:
            return True, match.group(0)
    return False, None