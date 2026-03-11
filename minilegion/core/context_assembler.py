"""Context assembler for MiniLegion.

Assembles a portable, tool-specific context block from the current project state,
adapters, memory files, stage templates, and recent artifacts.

The assembled block is a markdown string suitable for pasting at the start of a
conversation with any AI tool. The CLI command writes it to a file and prints to
stdout; this module is a pure function — no file writes happen here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from minilegion.core.config import MiniLegionConfig
from minilegion.core.state import load_state

# Ordered by pipeline stage for artifact lookup
_STAGE_ARTIFACTS: dict[str, str] = {
    "brief": "BRIEF.md",
    "research": "RESEARCH.md",
    "design": "DESIGN.md",
    "plan": "PLAN.md",
    "execute": "EXECUTION_LOG.md",
    "review": "REVIEW.md",
    "archive": "REVIEW.md",
}

_MEMORY_FILES: list[str] = ["decisions.md", "glossary.md", "constraints.md"]


def assemble_context(tool: str, project_dir: Path, config: MiniLegionConfig) -> str:
    """Assemble a portable context block for the given AI tool.

    Reads:
      - STATE.json (current stage, approvals, last history entries)
      - project-ai/adapters/<tool>.md  (tool-specific adapter — optional)
      - project-ai/adapters/_base.md   (fallback adapter — optional)
      - project-ai/memory/*.md         (memory files — optional)
      - project-ai/templates/<stage>.md (stage template — optional)
      - most recent stage artifact (BRIEF.md, RESEARCH.md, etc. — optional)

    Returns a markdown string with sections:
      ## Current State
      ## Previous Artifact
      ## Stage Template
      ## Memory
      ## Adapter Instructions

    Gracefully degrades if any optional file is absent — never raises on
    missing adapters, memory, or templates.

    Args:
        tool: Target AI tool name (e.g. "claude", "chatgpt", "copilot", "opencode").
        project_dir: Path to the project-ai/ directory.
        config: Loaded MiniLegionConfig with context sub-config.

    Returns:
        Assembled markdown string.
    """
    project_dir = Path(project_dir)
    max_tokens = config.context.max_injection_tokens
    parts: list[str] = []
    completed_task_ids: set[str] = set()

    # -----------------------------------------------------------------------
    # Section 1: Current State
    # -----------------------------------------------------------------------
    state_path = project_dir / "STATE.json"
    if state_path.exists():
        state = load_state(state_path)
        current_stage = state.current_stage
        completed_count = len(state.completed_tasks)
        completed_task_ids = set(state.completed_tasks)
        history_lines: list[str] = []
        for entry in state.history[-3:]:
            history_lines.append(
                f"- `{entry.timestamp}` **{entry.action}**: {entry.details}"
            )
        history_block = (
            "\n".join(history_lines) if history_lines else "_No history yet._"
        )
        state_section = (
            "## Current State\n\n"
            f"**Stage:** {current_stage}  \n"
            f"**Completed tasks:** {completed_count}  \n\n"
            "**Recent history:**\n"
            f"{history_block}\n"
        )
    else:
        current_stage = "init"
        state_section = "## Current State\n\n_STATE.json not found — project may not be initialized._\n"

    parts.append(state_section)

    # -----------------------------------------------------------------------
    # Section 2: Compact Plan
    # -----------------------------------------------------------------------
    compact_plan_lines: list[str] = []
    plan_path = project_dir / "PLAN.json"
    if plan_path.exists():
        try:
            plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
            tasks = plan_data.get("tasks") if isinstance(plan_data, dict) else None
            if isinstance(tasks, list):
                pending_tasks: list[tuple[str, str]] = []
                for task in tasks:
                    if not isinstance(task, dict):
                        continue
                    task_id = task.get("id")
                    if not isinstance(task_id, str) or not task_id.strip():
                        continue
                    if task_id in completed_task_ids:
                        continue
                    task_name = task.get("name")
                    display_name = (
                        task_name.strip()
                        if isinstance(task_name, str) and task_name.strip()
                        else "(unnamed task)"
                    )
                    pending_tasks.append((task_id, display_name))

                lookahead_limit = max(config.context.lookahead_tasks, 0)
                if pending_tasks and lookahead_limit > 0:
                    compact_plan_lines = [
                        f"- {task_id}: {task_name}"
                        for task_id, task_name in pending_tasks[:lookahead_limit]
                    ]
                elif pending_tasks:
                    compact_plan_lines = ["_Lookahead disabled (lookahead_tasks=0)._"]
                else:
                    compact_plan_lines = ["_No pending tasks in plan._"]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            compact_plan_lines = []

    if not compact_plan_lines:
        compact_plan_lines = ["_No plan context available._"]

    parts.append("## Compact Plan\n\n" + "\n".join(compact_plan_lines) + "\n")

    # -----------------------------------------------------------------------
    # Section 3: Previous Artifact
    # -----------------------------------------------------------------------
    artifact_name = _STAGE_ARTIFACTS.get(current_stage)
    if artifact_name:
        artifact_path = project_dir / artifact_name
        if artifact_path.exists():
            artifact_content = artifact_path.read_text(encoding="utf-8")
            if len(artifact_content) > max_tokens:
                artifact_content = artifact_content[:max_tokens] + "\n\n[TRUNCATED]"
            parts.append(f"## Previous Artifact\n\n{artifact_content}\n")

    # -----------------------------------------------------------------------
    # Section 4: Stage Template
    # -----------------------------------------------------------------------
    template_path = project_dir / "templates" / f"{current_stage}.md"
    if template_path.exists():
        template_content = template_path.read_text(encoding="utf-8")
        parts.append(f"## Stage Template\n\n{template_content}\n")
    else:
        parts.append(
            f"## Stage Template\n\n_No template defined for stage {current_stage}._\n"
        )

    # -----------------------------------------------------------------------
    # Section 5: Memory
    # -----------------------------------------------------------------------
    memory_parts: list[str] = []
    memory_dir = project_dir / "memory"
    if memory_dir.is_dir():
        for fname in _MEMORY_FILES:
            fpath = memory_dir / fname
            if fpath.exists():
                mem_content = fpath.read_text(encoding="utf-8").strip()
                if mem_content:
                    memory_parts.append(mem_content)

    if memory_parts:
        parts.append("## Memory\n\n" + "\n\n---\n\n".join(memory_parts) + "\n")

    # -----------------------------------------------------------------------
    # Section 6: Adapter Instructions
    # -----------------------------------------------------------------------
    adapters_dir = project_dir / "adapters"
    tool_adapter = adapters_dir / f"{tool}.md"
    base_adapter = adapters_dir / "_base.md"

    if tool_adapter.exists():
        adapter_content = tool_adapter.read_text(encoding="utf-8")
        parts.append(f"## Adapter Instructions\n\n{adapter_content}\n")
    elif base_adapter.exists():
        adapter_content = base_adapter.read_text(encoding="utf-8")
        parts.append(f"## Adapter Instructions\n\n{adapter_content}\n")
    else:
        parts.append(
            f"## Adapter Instructions\n\n"
            f"_Paste this context block at the start of your conversation with {tool}._\n"
        )

    # -----------------------------------------------------------------------
    # Warn if total output exceeds warn_threshold × max_injection_tokens
    # -----------------------------------------------------------------------
    assembled = "\n".join(parts)
    warn_limit = int(config.context.warn_threshold * max_tokens)
    if len(assembled) > warn_limit:
        print(
            f"[minilegion context] Warning: assembled context is {len(assembled)} chars "
            f"(warn threshold: {warn_limit} chars at {config.context.warn_threshold:.0%} of "
            f"max_injection_tokens={max_tokens}).",
            file=sys.stderr,
        )

    return assembled
