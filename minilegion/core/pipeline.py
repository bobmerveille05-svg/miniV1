"""Pipeline service layer — orchestration logic extracted from CLI commands.

Each public function handles the business logic for one pipeline stage.
CLI commands (commands.py) are reduced to argument parsing + echo only.

Public API:
  run_research(project_dir, state, sm, config) -> None
  run_design(project_dir, state, sm, config)   -> None
  run_plan(project_dir, state, sm, config, *, fast) -> None
  run_execute(project_dir, state, sm, config, *, task, dry_run) -> None
  run_review(project_dir, state, sm, config)   -> None
  run_archive(project_dir, state, sm)          -> ArchiveResult
  build_llm_caller(adapter, system_prompt)     -> Callable[[str], str]
  read_source_files(file_paths, project_root, config) -> str
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from minilegion.adapters.factory import get_adapter
from minilegion.core.approval import (
    approve_brief,
    approve_design,
    approve_patch,
    approve_plan,
    approve_research,
    approve_review,
)
from minilegion.core.coherence import check_coherence, CoherenceIssue
from minilegion.core.config import MiniLegionConfig
from minilegion.core.context_scanner import scan_codebase
from minilegion.core.diff import generate_diff_text
from minilegion.core.exceptions import MiniLegionError
from minilegion.core.file_io import write_atomic
from minilegion.core.patcher import apply_patch
from minilegion.core.preflight import check_preflight
from minilegion.core.provider_health import run_provider_healthcheck
from minilegion.core.renderer import render_decisions_md, save_dual
from minilegion.core.retry import validate_with_retry
from minilegion.core.schemas import (
    DesignSchema,
    ExecutionLogSchema,
    PlanSchema,
    ReviewSchema,
    Verdict,
)
from minilegion.core.scope_lock import validate_scope
from minilegion.core.state import ProjectState, Stage, StateMachine, save_state
from minilegion.prompts.loader import load_prompt, render_prompt

_MAX_REVISE_ITERATIONS = 2


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def build_llm_caller(
    config: MiniLegionConfig, system_prompt: str
) -> Callable[[str], str]:
    """Return a callable that sends a user message to the configured LLM.

    Uses get_adapter(config) so the correct provider is selected automatically.
    """
    adapter = get_adapter(config)

    def _call(prompt: str) -> str:
        return adapter.call_for_json(system_prompt, prompt).content

    return _call


def read_source_files(
    file_paths: list[str], project_root: Path, config: MiniLegionConfig
) -> str:
    """Read source files for builder context, capped at scan_max_file_size_kb.

    Args:
        file_paths: Relative paths of files to read.
        project_root: Root directory to resolve relative paths from.
        config: Config with scan_max_file_size_kb limit.

    Returns:
        Formatted string of file contents, or a placeholder message.
    """
    parts: list[str] = []
    size_limit = config.scan_max_file_size_kb * 1024
    for path_str in file_paths:
        fpath = project_root / path_str
        if not fpath.exists() or not fpath.is_file():
            continue
        size = fpath.stat().st_size
        if size > size_limit:
            parts.append(f"## {path_str}\n[File too large: {size} bytes]\n---\n")
            continue
        content = fpath.read_text(encoding="utf-8", errors="replace")
        parts.append(f"## {path_str}\n{content}\n---\n")
    return "\n".join(parts) if parts else "(no existing source files)"


def get_skip_stages(state: ProjectState) -> set[str]:
    """Return the set of stage names recorded as skipped in state metadata."""
    raw = state.metadata.get("skipped_stages", "[]")
    try:
        return set(_json.loads(raw))
    except (ValueError, TypeError):
        return set()


# ---------------------------------------------------------------------------
# Stage: brief
# ---------------------------------------------------------------------------


def run_brief(
    project_dir: Path,
    state: ProjectState,
    sm: StateMachine,
    text: str,
) -> None:
    """Execute the brief stage.

    Writes BRIEF.md, runs approval gate, transitions state.

    Raises:
        ApprovalError: If user rejects the brief.
        MiniLegionError: On any other failure.
    """
    brief_content = f"# Project Brief\n\n## Overview\n\n{text}\n"
    write_atomic(project_dir / "BRIEF.md", brief_content)
    approve_brief(state, project_dir / "STATE.json", brief_content)

    sm.transition(Stage.BRIEF)
    state.current_stage = Stage.BRIEF.value
    state.add_history("brief", "Brief created and approved")
    save_state(state, project_dir / "STATE.json")


# ---------------------------------------------------------------------------
# Stage: research
# ---------------------------------------------------------------------------


def run_research(
    project_dir: Path,
    state: ProjectState,
    sm: StateMachine,
    config: MiniLegionConfig,
) -> None:
    """Execute the research stage.

    Scans codebase, calls LLM, saves dual output, runs approval gate,
    transitions state.

    Raises:
        ApprovalError: If user rejects the research.
        MiniLegionError: On any other failure.
    """
    # Provider healthcheck — fail fast before any research work
    if config.provider_healthcheck:
        run_provider_healthcheck(config)

    check_preflight(Stage.RESEARCH, project_dir)

    codebase_context = scan_codebase(project_dir, config)

    # Context compaction — truncate deterministically if over threshold
    _CONTEXT_COMPACT_THRESHOLD = 50_000
    if (
        config.context_auto_compact
        and len(codebase_context) > _CONTEXT_COMPACT_THRESHOLD
    ):
        codebase_context = (
            codebase_context[:_CONTEXT_COMPACT_THRESHOLD]
            + f"\n[CONTEXT TRUNCATED: original length {len(codebase_context)} chars, "
            f"truncated to {_CONTEXT_COMPACT_THRESHOLD} chars for prompt budget]"
        )

    system_prompt, user_template = load_prompt("researcher")
    brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")
    user_message = render_prompt(
        user_template,
        project_name=project_dir.parent.name,
        brief_content=brief_content,
        codebase_context=codebase_context,
        mode="fact",
        num_options="3",
    )

    research_data = validate_with_retry(
        build_llm_caller(config, system_prompt),
        user_message,
        "research",
        config,
        project_dir,
    )
    save_dual(research_data, project_dir / "RESEARCH.json", project_dir / "RESEARCH.md")

    research_md = (project_dir / "RESEARCH.md").read_text(encoding="utf-8")
    approve_research(state, project_dir / "STATE.json", research_md)

    sm.transition(Stage.RESEARCH)
    state.current_stage = Stage.RESEARCH.value
    state.add_history("research", "Research completed and approved")
    save_state(state, project_dir / "STATE.json")


# ---------------------------------------------------------------------------
# Stage: design
# ---------------------------------------------------------------------------


def run_design(
    project_dir: Path,
    state: ProjectState,
    sm: StateMachine,
    config: MiniLegionConfig,
) -> None:
    """Execute the design stage.

    Raises:
        ApprovalError: If user rejects the design.
        MiniLegionError: On any other failure.
    """
    check_preflight(Stage.DESIGN, project_dir)

    system_prompt, user_template = load_prompt("designer")
    brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")
    research_json = (project_dir / "RESEARCH.json").read_text(encoding="utf-8")
    user_message = render_prompt(
        user_template,
        project_name=project_dir.parent.name,
        brief_content=brief_content,
        research_json=research_json,
        focus_files_content="(Focus file reading deferred to Phase 9)",
    )

    design_data = validate_with_retry(
        build_llm_caller(config, system_prompt),
        user_message,
        "design",
        config,
        project_dir,
    )
    save_dual(design_data, project_dir / "DESIGN.json", project_dir / "DESIGN.md")

    design_md = (project_dir / "DESIGN.md").read_text(encoding="utf-8")
    approve_design(state, project_dir / "STATE.json", design_md)

    sm.transition(Stage.DESIGN)
    state.current_stage = Stage.DESIGN.value
    state.add_history("design", "Design completed and approved")
    save_state(state, project_dir / "STATE.json")


# ---------------------------------------------------------------------------
# Stage: plan
# ---------------------------------------------------------------------------


def run_plan(
    project_dir: Path,
    state: ProjectState,
    sm: StateMachine,
    config: MiniLegionConfig,
    *,
    fast: bool = False,
) -> None:
    """Execute the plan stage (normal or fast mode).

    Raises:
        ApprovalError: If user rejects the plan.
        MiniLegionError: On any other failure.
    """
    if fast:
        _run_plan_fast(project_dir, state, sm, config)
    else:
        _run_plan_normal(project_dir, state, sm, config)


def _run_plan_normal(
    project_dir: Path,
    state: ProjectState,
    sm: StateMachine,
    config: MiniLegionConfig,
) -> None:
    check_preflight(Stage.PLAN, project_dir)

    system_prompt, user_template = load_prompt("planner")
    user_message = render_prompt(
        user_template,
        project_name=project_dir.parent.name,
        brief_content=(project_dir / "BRIEF.md").read_text(encoding="utf-8"),
        research_json=(project_dir / "RESEARCH.json").read_text(encoding="utf-8"),
        design_json=(project_dir / "DESIGN.json").read_text(encoding="utf-8"),
    )

    plan_data = validate_with_retry(
        build_llm_caller(config, system_prompt),
        user_message,
        "plan",
        config,
        project_dir,
    )
    save_dual(plan_data, project_dir / "PLAN.json", project_dir / "PLAN.md")

    plan_md = (project_dir / "PLAN.md").read_text(encoding="utf-8")
    approve_plan(state, project_dir / "STATE.json", plan_md)

    sm.transition(Stage.PLAN)
    state.current_stage = Stage.PLAN.value
    state.add_history("plan", "Plan completed and approved")
    save_state(state, project_dir / "STATE.json")


def _run_plan_fast(
    project_dir: Path,
    state: ProjectState,
    sm: StateMachine,
    config: MiniLegionConfig,
) -> None:
    """Fast mode: synthetically advance through research/design, plan from brief only."""
    skip_stages: set[str] = {"research", "design"}

    # Synthetic transitions through skipped stages
    current = Stage(state.current_stage)
    if current == Stage.BRIEF:
        sm.transition(Stage.RESEARCH)
        current = Stage.RESEARCH
    if current == Stage.RESEARCH:
        sm.transition(Stage.DESIGN)

    check_preflight(Stage.PLAN, project_dir, skip_stages=skip_stages)

    codebase_tree = scan_codebase(project_dir.parent, config)
    system_prompt, user_template = load_prompt("planner")
    user_message = render_prompt(
        user_template,
        project_name=project_dir.parent.name,
        brief_content=(project_dir / "BRIEF.md").read_text(encoding="utf-8"),
        research_json=f"## Fast Mode: No research phase run\n\n{codebase_tree}",
        design_json=(
            '{"note": "Fast mode: no design phase run. '
            'Plan based on brief and codebase context."}'
        ),
    )

    plan_data = validate_with_retry(
        build_llm_caller(config, system_prompt),
        user_message,
        "plan",
        config,
        project_dir,
    )
    save_dual(plan_data, project_dir / "PLAN.json", project_dir / "PLAN.md")

    plan_md = (project_dir / "PLAN.md").read_text(encoding="utf-8")
    approve_plan(state, project_dir / "STATE.json", plan_md)

    state.approvals["research_approved"] = True
    state.approvals["design_approved"] = True
    sm.transition(Stage.PLAN)
    state.current_stage = Stage.PLAN.value
    state.metadata["skipped_stages"] = _json.dumps(sorted(skip_stages))
    state.add_history(
        "plan",
        "Fast mode: research and design skipped. Plan completed and approved.",
    )
    save_state(state, project_dir / "STATE.json")


# ---------------------------------------------------------------------------
# Stage: execute
# ---------------------------------------------------------------------------


def run_execute(
    project_dir: Path,
    state: ProjectState,
    sm: StateMachine,
    config: MiniLegionConfig,
    *,
    task: int | None = None,
    dry_run: bool = False,
) -> bool:
    """Execute the execute stage.

    Args:
        task: 1-indexed task number, or None for all tasks.
        dry_run: If True, show changes without applying.

    Returns:
        True if dry_run (caller should skip state transition).

    Raises:
        ApprovalError: If user rejects a patch.
        MiniLegionError: On any other failure.
    """
    check_preflight(Stage.EXECUTE, project_dir, skip_stages=get_skip_stages(state))

    plan_json_str = (project_dir / "PLAN.json").read_text(encoding="utf-8")
    plan_data = PlanSchema.model_validate_json(plan_json_str)
    project_root = project_dir.parent

    source_files = read_source_files(plan_data.touched_files, project_root, config)
    system_prompt, user_template = load_prompt("builder")
    user_message = render_prompt(
        user_template,
        project_name=project_dir.parent.name,
        plan_json=plan_json_str,
        source_files=source_files,
        corrective_actions="",
    )

    execution_log = validate_with_retry(
        build_llm_caller(config, system_prompt),
        user_message,
        "execution_log",
        config,
        project_dir,
    )

    all_changed = [cf.path for tr in execution_log.tasks for cf in tr.changed_files]
    validate_scope(all_changed, plan_data.touched_files)

    if task is not None:
        idx = task - 1
        if idx < 0 or idx >= len(execution_log.tasks):
            raise MiniLegionError(
                f"Task index {task} out of range (1–{len(execution_log.tasks)})"
            )
        execution_log = ExecutionLogSchema(tasks=[execution_log.tasks[idx]])

    if dry_run:
        patches = []
        for tr in execution_log.tasks:
            for cf in tr.changed_files:
                patches.append(apply_patch(cf, project_root, dry_run=True))
        return patches  # type: ignore[return-value]

    for tr in execution_log.tasks:
        for cf in tr.changed_files:
            desc = apply_patch(cf, project_root, dry_run=True)
            approve_patch(state, project_dir / "STATE.json", desc)
            apply_patch(cf, project_root, dry_run=False)

    save_dual(
        execution_log,
        project_dir / "EXECUTION_LOG.json",
        project_dir / "EXECUTION_LOG.md",
    )

    sm.transition(Stage.EXECUTE)
    state.current_stage = Stage.EXECUTE.value
    state.add_history("execute", "Execution completed and approved")
    save_state(state, project_dir / "STATE.json")
    return False


# ---------------------------------------------------------------------------
# Stage: review
# ---------------------------------------------------------------------------


def run_review(
    project_dir: Path,
    state: ProjectState,
    sm: StateMachine,
    config: MiniLegionConfig,
    *,
    want_redesign_fn: Callable[[], bool] | None = None,
) -> str:
    """Execute the review stage (including revise loop).

    Args:
        want_redesign_fn: Callable that returns True if user wants re-design.
                          Defaults to a typer.confirm prompt. Injected for testing.

    Returns:
        "passed" | "escalated" | "redesign"

    Raises:
        ApprovalError: If user rejects the review.
        MiniLegionError: On any other failure.
    """
    import typer as _typer

    if want_redesign_fn is None:
        want_redesign_fn = lambda: _typer.confirm("Re-design before re-executing?")  # noqa: E731

    check_preflight(Stage.REVIEW, project_dir, skip_stages=get_skip_stages(state))

    plan_json_str = (project_dir / "PLAN.json").read_text(encoding="utf-8")
    plan_data = PlanSchema.model_validate_json(plan_json_str)
    project_root = project_dir.parent
    project_name = project_dir.parent.name

    design_path = project_dir / "DESIGN.json"
    research_path = project_dir / "RESEARCH.json"
    design_json_str = (
        design_path.read_text(encoding="utf-8")
        if design_path.exists()
        else '{"note": "Fast mode: no design phase run."}'
    )
    research_json_str = (
        research_path.read_text(encoding="utf-8")
        if research_path.exists()
        else '{"existing_conventions": []}'
    )
    conventions = "\n".join(
        _json.loads(research_json_str).get("existing_conventions", [])
    )

    revise_count = int(state.metadata.get("revise_count", "0"))

    while True:
        execution_log_json = (project_dir / "EXECUTION_LOG.json").read_text(
            encoding="utf-8"
        )
        execution_log = ExecutionLogSchema.model_validate_json(execution_log_json)
        diff_text = generate_diff_text(execution_log)

        system_prompt, user_template = load_prompt("reviewer")
        user_message = render_prompt(
            user_template,
            project_name=project_name,
            diff_text=diff_text,
            plan_json=plan_json_str,
            design_json=design_json_str,
            conventions=conventions,
        )

        review_data = validate_with_retry(
            build_llm_caller(config, system_prompt),
            user_message,
            "review",
            config,
            project_dir,
        )
        save_dual(review_data, project_dir / "REVIEW.json", project_dir / "REVIEW.md")

        review_md = (project_dir / "REVIEW.md").read_text(encoding="utf-8")
        approve_review(state, project_dir / "STATE.json", review_md)

        if review_data.verdict == Verdict.PASS:
            sm.transition(Stage.REVIEW)
            state.current_stage = Stage.REVIEW.value
            state.add_history("review", "Review passed and approved")
            save_state(state, project_dir / "STATE.json")
            return "passed"

        if revise_count >= _MAX_REVISE_ITERATIONS:
            return "escalated"

        if not review_data.design_conformity.conforms:
            if want_redesign_fn():
                sm.transition(Stage.DESIGN)
                state.current_stage = Stage.DESIGN.value
                state.add_history("review", "Backtracked to design for re-design")
                save_state(state, project_dir / "STATE.json")
                return "redesign"

        revise_count += 1
        state.metadata["revise_count"] = str(revise_count)
        save_state(state, project_dir / "STATE.json")

        corrective_text = ""
        if review_data.corrective_actions:
            corrective_text = (
                "\n## Corrective Actions from Review\n"
                + "\n".join(f"- {a}" for a in review_data.corrective_actions)
                + "\n"
            )

        source_files = read_source_files(plan_data.touched_files, project_root, config)
        builder_system, builder_template = load_prompt("builder")
        builder_message = render_prompt(
            builder_template,
            project_name=project_name,
            plan_json=plan_json_str,
            source_files=source_files,
            corrective_actions=corrective_text,
        )

        new_execution_log = validate_with_retry(
            build_llm_caller(config, builder_system),
            builder_message,
            "execution_log",
            config,
            project_dir,
        )

        all_changed = [
            cf.path for tr in new_execution_log.tasks for cf in tr.changed_files
        ]
        validate_scope(all_changed, plan_data.touched_files)

        for tr in new_execution_log.tasks:
            for cf in tr.changed_files:
                desc = apply_patch(cf, project_root, dry_run=True)
                approve_patch(state, project_dir / "STATE.json", desc)
                apply_patch(cf, project_root, dry_run=False)

        save_dual(
            new_execution_log,
            project_dir / "EXECUTION_LOG.json",
            project_dir / "EXECUTION_LOG.md",
        )


# ---------------------------------------------------------------------------
# Stage: archive
# ---------------------------------------------------------------------------


@dataclass
class ArchiveResult:
    """Result of the archive stage."""

    task_count: int
    verdict: str
    coherence_issues: list[CoherenceIssue]


def run_archive(
    project_dir: Path,
    state: ProjectState,
    sm: StateMachine,
) -> ArchiveResult:
    """Execute the archive stage (no LLM calls).

    Raises:
        MiniLegionError: On any failure.
    """
    check_preflight(Stage.ARCHIVE, project_dir, skip_stages=get_skip_stages(state))

    execution_log = ExecutionLogSchema.model_validate_json(
        (project_dir / "EXECUTION_LOG.json").read_text(encoding="utf-8")
    )
    review_data = ReviewSchema.model_validate_json(
        (project_dir / "REVIEW.json").read_text(encoding="utf-8")
    )
    design_path = project_dir / "DESIGN.json"
    design_data = (
        DesignSchema.model_validate_json(design_path.read_text(encoding="utf-8"))
        if design_path.exists()
        else None
    )

    issues = check_coherence(project_dir)

    task_ids = [tr.task_id for tr in execution_log.tasks]
    state.completed_tasks = task_ids
    state.metadata["final_verdict"] = review_data.verdict.value
    if issues:
        state.metadata["coherence_issues"] = _json.dumps(
            [
                {"check": i.check_name, "severity": i.severity, "message": i.message}
                for i in issues
            ]
        )

    decisions_content = (
        render_decisions_md(design_data)
        if design_data is not None
        else "# Architecture Decisions\n\n_Fast mode: no design phase run._\n"
    )
    write_atomic(project_dir / "DECISIONS.md", decisions_content)

    sm.transition(Stage.ARCHIVE)
    state.current_stage = Stage.ARCHIVE.value
    state.add_history(
        "archive",
        f"Pipeline archived. {len(task_ids)} tasks. Verdict: {review_data.verdict.value}.",
    )
    save_state(state, project_dir / "STATE.json")

    return ArchiveResult(
        task_count=len(task_ids),
        verdict=review_data.verdict.value,
        coherence_issues=issues,
    )
