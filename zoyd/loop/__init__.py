"""
Loop module package.

This package contains the core loop functionality split into focused modules:

- prompt_templates.py: Prompt templates and detection patterns
- prompt_builder.py: Prompt building utilities
- commit_manager.py: Commit management utilities
- invoke.py: Claude invocation utilities

Core functionality:

- LoopRunner: Main loop orchestrator
- invoke_claude: Function to invoke Claude Code
- format_duration: Utility to format durations
"""

from .loop import LoopRunner
from .invoke import invoke_claude, format_duration
from .prompt_builder import (
    build_prompt,
    build_prompt_with_memory,
    _extract_recent_iterations,
    _format_relevant_context,
)
from .prompt_templates import (
    PROMPT_TEMPLATE,
    PROMPT_TEMPLATE_WITH_MEMORY,
    COMMIT_PROMPT_TEMPLATE,
    COMMIT_SYSTEM_PROMPT,
    detect_cannot_complete,
)
from .commit_manager import (
    generate_commit_message,
    commit_changes,
)