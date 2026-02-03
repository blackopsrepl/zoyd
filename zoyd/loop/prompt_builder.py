"""Prompt building utilities for the Zoyd loop."""

from typing import Optional

from .prompt_templates import (
    PROMPT_TEMPLATE,
    PROMPT_TEMPLATE_WITH_MEMORY,
)


def build_prompt(
    prd_content: str,
    progress_content: str,
    iteration: int,
    completed: int,
    total: int,
    current_task: str,
) -> str:
    """Build the prompt for Claude.

    Args:
        prd_content: Content of the PRD file.
        progress_content: Content of the progress file.
        iteration: Current iteration number.
        completed: Number of completed tasks.
        total: Total number of tasks.
        current_task: Text of the current task to complete.

    Returns:
        Formatted prompt string.
    """
    return PROMPT_TEMPLATE.format(
        iteration=iteration,
        completed=completed,
        total=total,
        current_task=current_task,
        prd_content=prd_content,
        progress_content=progress_content or "(No progress yet)",
    )


def build_prompt_with_memory(
    prd_content: str,
    relevant_context: str,
    recent_progress: str,
    iteration: int,
    completed: int,
    total: int,
    current_task: str,
) -> str:
    """Build a prompt using vector memory context instead of the full progress log.

    Uses ``PROMPT_TEMPLATE_WITH_MEMORY`` which replaces the unbounded progress
    log with two focused sections: semantically relevant past work retrieved
    via vector search, and only the last N iterations of progress.

    Args:
        prd_content: Content of the PRD file.
        relevant_context: Formatted string of semantically relevant past work
            from vector search results.
        recent_progress: The last N iterations extracted from the progress log.
        iteration: Current iteration number.
        completed: Number of completed tasks.
        total: Total number of tasks.
        current_task: Text of the current task to complete.

    Returns:
        Formatted prompt string.
    """
    return PROMPT_TEMPLATE_WITH_MEMORY.format(
        iteration=iteration,
        completed=completed,
        total=total,
        current_task=current_task,
        relevant_context=relevant_context or "(No relevant context found)",
        recent_progress=recent_progress or "(No progress yet)",
        prd_content=prd_content,
    )


def _extract_recent_iterations(progress_content: str, n: int) -> str:
    """Extract the last N iterations from progress content.

    Splits the progress content on ``## Iteration`` headers and returns the
    last *n* iteration sections joined together.  Any preamble text before the
    first ``## Iteration`` header is excluded.

    Args:
        progress_content: Full progress file content.
        n: Number of recent iterations to return.

    Returns:
        The last *n* iteration sections as a single string, or an empty string
        if there are no iterations.
    """
    if not progress_content:
        return ""

    parts = progress_content.split("\n## Iteration ")
    # parts[0] is the preamble (before the first header), remaining are iterations
    # Each iteration part (after the first) needs the header prefix restored
    iterations = [f"## Iteration {part}" for part in parts[1:]]

    if not iterations:
        return ""

    return "\n".join(iterations[-n:])


def _format_relevant_context(results: list[dict]) -> str:
    """Format vector search results into a readable prompt section.

    Takes the list of dicts returned by
    :meth:`VectorMemory.find_relevant_outputs` and produces a human-readable
    string suitable for insertion into the ``{relevant_context}`` placeholder
    of :data:`PROMPT_TEMPLATE_WITH_MEMORY`.

    Each result is rendered as a numbered entry with its task, session, and
    a preview of the output.

    Args:
        results: List of result dicts from ``find_relevant_outputs()``.  Each
            dict contains ``element_id``, ``score``, ``session_id``,
            ``iteration``, ``task_text``, ``output_preview``, ``timestamp``,
            ``return_code``.

    Returns:
        Formatted context string, or ``"(No relevant context found)"`` if
        *results* is empty.
    """
    if not results:
        return "(No relevant context found)"

    sections: list[str] = []
    for i, result in enumerate(results, 1):
        task = result.get("task_text", "Unknown task")
        session = result.get("session_id", "unknown")[:8]
        iteration = result.get("iteration", "?")
        score = result.get("score", 0.0)
        preview = result.get("output_preview", "")
        rc = result.get("return_code", None)

        header = f"### {i}. {task}"
        meta_parts = [f"Session: {session}", f"Iteration: {iteration}"]
        if rc is not None:
            meta_parts.append(f"Exit: {rc}")
        meta_parts.append(f"Similarity: {score:.3f}")
        meta_line = " | ".join(meta_parts)

        section = f"{header}\n{meta_line}\n\n{preview}"
        sections.append(section)

    return "\n\n---\n\n".join(sections)