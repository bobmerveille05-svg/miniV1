"""MiniLegion CLI commands — all 8 pipeline commands.

Commands register themselves with the Typer app imported from minilegion.cli.
"""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Annotated

import typer

from minilegion.cli import app
from minilegion.core.config import MiniLegionConfig, load_config
from minilegion.core.approval import (
    ApprovalError,
    approve_brief,
    approve_research,
    approve_design,
    approve_plan,
    approve_patch,
    approve_review,
)
from minilegion.core.context_scanner import scan_codebase
from minilegion.core.diff import generate_diff_text
from minilegion.core.exceptions import (
    ConfigError,
    MiniLegionError,
)
from minilegion.core.file_io import write_atomic
from minilegion.core.patcher import apply_patch
from minilegion.core.preflight import check_preflight
from minilegion.core.provider_health import run_provider_healthcheck
from minilegion.core.renderer import save_dual, render_decisions_md
from minilegion.core.retry import validate_with_retry
from minilegion.core.schemas import (
    DesignSchema,
    ExecutionLogSchema,
    PlanSchema,
    ReviewSchema,
)
from minilegion.core.scope_lock import validate_scope
from minilegion.core.state import (
    ProjectState,
    Stage,
    StateMachine,
    load_state,
    save_state,
)
from minilegion.prompts.loader import load_prompt, render_prompt
from minilegion.adapters.factory import get_adapter
from minilegion.core.coherence import check_coherence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def find_project_dir() -> Path:
    """Find project-ai/ in current working directory.

    Returns:
        Path to the project-ai/ directory.

    Raises:
        ConfigError: If project-ai/ does not exist.
    """
    project_dir = Path.cwd() / "project-ai"
    if not project_dir.is_dir():
        raise ConfigError(
            "No MiniLegion project found. Run `minilegion init <name>` first."
        )
    return project_dir


def _get_skip_stages(state: ProjectState) -> set[str]:
    """Return set of stage names recorded as skipped in state metadata.

    Used by downstream commands (execute, review, archive) to pass
    skip_stages to check_preflight() when fast mode was used for plan.

    Args:
        state: The loaded ProjectState.

    Returns:
        Set of stage names (e.g. {"research", "design"}) or empty set.
    """
    raw = state.metadata.get("skipped_stages", "[]")
    try:
        return set(_json.loads(raw))
    except (ValueError, TypeError):
        return set()


def _pipeline_stub(stage: Stage, extra_info: str = "") -> None:
    """Common logic for pipeline stub commands.

    Loads state, validates transition, prints stub message or error.
    """
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        if not sm.can_transition(stage):
            typer.echo(
                typer.style(
                    f"Cannot transition from {state.current_stage} to {stage.value}",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(code=1)

        msg = f"Would run {stage.value}... (not yet implemented)"
        if extra_info:
            msg = f"Would run {stage.value} ({extra_info})... (not yet implemented)"
        typer.echo(typer.style(msg, fg=typer.colors.GREEN))

    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


def _read_source_files(
    file_paths: list[str], project_root: Path, config: MiniLegionConfig
) -> str:
    """Read source files for builder context, capped at scan_max_file_size_kb.

    Args:
        file_paths: Relative paths of files to read (from PLAN.json touched_files).
        project_root: Root directory to resolve relative paths from.
        config: Config with scan_max_file_size_kb limit.

    Returns:
        Formatted string of file contents for the builder prompt.
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


# ---------------------------------------------------------------------------
# BRIEF.md template content
# ---------------------------------------------------------------------------

BRIEF_TEMPLATE = """\
# Project Brief

## Overview

<!-- Describe the project in 2-3 sentences. -->

## Goals

<!-- What are the main objectives? -->

## Constraints

<!-- Any technical or business constraints? -->

## Success Criteria

<!-- How do you measure success? -->
"""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def init(
    name: Annotated[str, typer.Argument(help="Project name")],
) -> None:
    """Initialize a new MiniLegion project."""
    project_path = Path(name)
    if project_path.exists():
        typer.echo(
            typer.style(
                f"Warning: Directory '{name}' already exists. Not overwriting.",
                fg=typer.colors.YELLOW,
            )
        )
        raise typer.Exit(code=1)

    project_ai = project_path / "project-ai"
    project_ai.mkdir(parents=True)

    # Create prompts/ directory
    (project_ai / "prompts").mkdir()

    # Create STATE.json via ProjectState model + save_state (uses write_atomic)
    state = ProjectState()
    state.add_history("init", "Project initialized")
    save_state(state, project_ai / "STATE.json")

    # Create minilegion.config.json via write_atomic
    config = MiniLegionConfig()
    write_atomic(
        project_ai / "minilegion.config.json", config.model_dump_json(indent=2)
    )

    # Create BRIEF.md via write_atomic
    write_atomic(project_ai / "BRIEF.md", BRIEF_TEMPLATE)

    typer.echo(typer.style(f"Created project: {name}", fg=typer.colors.GREEN))


@app.command()
def status() -> None:
    """Show current project status."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")

        typer.echo(typer.style(f"Stage: {state.current_stage}", bold=True))
        typer.echo()

        # Approvals table
        typer.echo("Approvals:")
        for key, approved in state.approvals.items():
            color = typer.colors.GREEN if approved else typer.colors.RED
            status_text = "True" if approved else "False"
            typer.echo(f"  {key}: {typer.style(status_text, fg=color)}")

        typer.echo()
        typer.echo(f"Completed tasks: {len(state.completed_tasks)}")

        # Last history entry
        if state.history:
            last = state.history[-1]
            typer.echo(f"Last action: {last.action} — {last.details}")

    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


@app.command()
def brief(
    text: Annotated[str | None, typer.Argument(help="Brief text")] = None,
) -> None:
    """Run the brief stage."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        # Validate transition before doing any work
        if not sm.can_transition(Stage.BRIEF):
            typer.echo(
                typer.style(
                    f"Cannot transition from {state.current_stage} to {Stage.BRIEF.value}",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(code=1)

        # Read text argument or fall back to stdin
        if text is None:
            text = typer.get_text_stream("stdin").read().strip()

        brief_content = f"# Project Brief\n\n## Overview\n\n{text}\n"

        # Write atomically BEFORE approval gate (append-only artifact principle)
        write_atomic(project_dir / "BRIEF.md", brief_content)
        typer.echo(typer.style("BRIEF.md created.", fg=typer.colors.GREEN))

        # Approval gate — raises ApprovalError on rejection
        approve_brief(state, project_dir / "STATE.json", brief_content)

        # State mutation ONLY after confirmed approval
        sm.transition(Stage.BRIEF)
        state.current_stage = Stage.BRIEF.value  # CRITICAL: sync ProjectState manually
        state.add_history("brief", "Brief created and approved")
        save_state(state, project_dir / "STATE.json")
        typer.echo(typer.style("Brief approved. Stage: brief", fg=typer.colors.GREEN))

    except ApprovalError:
        typer.echo(
            typer.style("Brief rejected. Stage unchanged.", fg=typer.colors.YELLOW)
        )
        # exit code 0 — rejection is not an error
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


@app.command()
def research() -> None:
    """Run the research stage."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        # Validate transition before doing any work
        if not sm.can_transition(Stage.RESEARCH):
            typer.echo(
                typer.style(
                    f"Cannot transition from {state.current_stage} to {Stage.RESEARCH.value}",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(code=1)

        # Load config — CRITICAL: pass parent of project-ai dir, not project-ai itself
        # find_project_dir() returns .../myproject/project-ai/
        # load_config() internally appends "project-ai/minilegion.config.json"
        # So: load_config(project_dir.parent) → myproject/project-ai/minilegion.config.json ✓
        #     load_config(project_dir)        → myproject/project-ai/project-ai/minilegion.config.json ✗
        config = load_config(project_dir.parent)

        # Provider healthcheck — fail fast before any research work
        if config.provider_healthcheck:
            run_provider_healthcheck(config)

        # Preflight validation (requires BRIEF.md + brief_approved in STATE.json)
        check_preflight(Stage.RESEARCH, project_dir)

        # Scan codebase for context
        typer.echo("Scanning codebase...")
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

        # Load and render researcher prompt
        system_prompt, user_template = load_prompt("researcher")
        brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")
        project_name = project_dir.parent.name  # directory name user chose at init
        user_message = render_prompt(
            user_template,
            project_name=project_name,
            brief_content=brief_content,
            codebase_context=codebase_context,
        )

        # LLM call — use get_adapter(config) so the configured provider is used
        typer.echo("Running researcher...")
        adapter = get_adapter(config)

        def llm_call(prompt: str) -> str:
            # system_prompt is fixed; prompt is user message (with retry feedback appended)
            response = adapter.call_for_json(system_prompt, prompt)
            return response.content

        # validate_with_retry: (llm_call, prompt, artifact_name, config, project_dir)
        # 4th arg is full MiniLegionConfig — NOT config.max_retries int
        research_data = validate_with_retry(
            llm_call, user_message, "research", config, project_dir
        )

        # Save dual output (JSON + Markdown)
        save_dual(
            research_data, project_dir / "RESEARCH.json", project_dir / "RESEARCH.md"
        )
        typer.echo(
            typer.style("RESEARCH.json + RESEARCH.md saved.", fg=typer.colors.GREEN)
        )

        # Approval gate
        research_md = (project_dir / "RESEARCH.md").read_text(encoding="utf-8")
        approve_research(state, project_dir / "STATE.json", research_md)

        # State mutation ONLY after confirmed approval
        sm.transition(Stage.RESEARCH)
        state.current_stage = (
            Stage.RESEARCH.value
        )  # CRITICAL: sync ProjectState manually
        state.add_history("research", "Research completed and approved")
        save_state(state, project_dir / "STATE.json")
        typer.echo(
            typer.style("Research approved. Stage: research", fg=typer.colors.GREEN)
        )

    except ApprovalError:
        typer.echo(
            typer.style("Research rejected. Stage unchanged.", fg=typer.colors.YELLOW)
        )
        # exit code 0 — rejection is not an error
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


@app.command()
def design() -> None:
    """Run the design stage."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        if not sm.can_transition(Stage.DESIGN):
            typer.echo(
                typer.style(
                    f"Cannot transition from {state.current_stage} to {Stage.DESIGN.value}",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(code=1)

        config = load_config(project_dir.parent)
        check_preflight(Stage.DESIGN, project_dir)

        system_prompt, user_template = load_prompt("designer")
        project_name = project_dir.parent.name
        brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")
        research_json = (project_dir / "RESEARCH.json").read_text(encoding="utf-8")
        focus_files_content = "(Focus file reading deferred to Phase 9)"
        user_message = render_prompt(
            user_template,
            project_name=project_name,
            brief_content=brief_content,
            research_json=research_json,
            focus_files_content=focus_files_content,
        )

        typer.echo("Running designer...")
        adapter = get_adapter(config)

        def llm_call(prompt: str) -> str:
            response = adapter.call_for_json(system_prompt, prompt)
            return response.content

        design_data = validate_with_retry(
            llm_call, user_message, "design", config, project_dir
        )

        save_dual(design_data, project_dir / "DESIGN.json", project_dir / "DESIGN.md")
        typer.echo(typer.style("DESIGN.json + DESIGN.md saved.", fg=typer.colors.GREEN))

        design_md = (project_dir / "DESIGN.md").read_text(encoding="utf-8")
        approve_design(state, project_dir / "STATE.json", design_md)

        sm.transition(Stage.DESIGN)
        state.current_stage = Stage.DESIGN.value  # CRITICAL: sync ProjectState manually
        state.add_history("design", "Design completed and approved")
        save_state(state, project_dir / "STATE.json")
        typer.echo(typer.style("Design approved. Stage: design", fg=typer.colors.GREEN))

    except ApprovalError:
        typer.echo(
            typer.style("Design rejected. Stage unchanged.", fg=typer.colors.YELLOW)
        )
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


@app.command()
def plan(
    fast: Annotated[
        bool, typer.Option("--fast", help="Use basic context only")
    ] = False,
    skip_research_design: Annotated[
        bool,
        typer.Option("--skip-research-design", help="Skip research and design"),
    ] = False,
) -> None:
    """Run the plan stage."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        config = load_config(project_dir.parent)

        if fast or skip_research_design:
            # --- FAST MODE PATH (FAST-01, FAST-02) ---
            # Synthetically advance through skipped stages so the state machine
            # allows us to reach PLAN from BRIEF (or RESEARCH).
            sm = StateMachine(Stage(state.current_stage), state.approvals)
            current = Stage(state.current_stage)

            # Advance through RESEARCH if needed
            if current == Stage.BRIEF:
                if not sm.can_transition(Stage.RESEARCH):
                    typer.echo(
                        typer.style(
                            f"Cannot transition from {state.current_stage} to research",
                            fg=typer.colors.RED,
                        )
                    )
                    raise typer.Exit(code=1)
                sm.transition(Stage.RESEARCH)
                current = Stage.RESEARCH

            # Advance through DESIGN if needed
            if current == Stage.RESEARCH:
                if not sm.can_transition(Stage.DESIGN):
                    typer.echo(
                        typer.style(
                            f"Cannot transition from {current.value} to design",
                            fg=typer.colors.RED,
                        )
                    )
                    raise typer.Exit(code=1)
                sm.transition(Stage.DESIGN)
                current = Stage.DESIGN

            # Now transition to PLAN
            if not sm.can_transition(Stage.PLAN):
                typer.echo(
                    typer.style(
                        f"Cannot transition from {current.value} to plan",
                        fg=typer.colors.RED,
                    )
                )
                raise typer.Exit(code=1)

            # Preflight: bypass research/design requirements
            skip_stages: set[str] = {"research", "design"}
            check_preflight(Stage.PLAN, project_dir, skip_stages=skip_stages)

            # Build degraded context: codebase tree + brief (no research/design JSON)
            brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")
            codebase_tree = scan_codebase(project_dir.parent, config)
            research_sub = f"## Fast Mode: No research phase run\n\n{codebase_tree}"
            design_sub = (
                '{"note": "Fast mode: no design phase run. '
                'Plan based on brief and codebase context."}'
            )

            system_prompt, user_template = load_prompt("planner")
            project_name = project_dir.parent.name
            user_message = render_prompt(
                user_template,
                project_name=project_name,
                brief_content=brief_content,
                research_json=research_sub,
                design_json=design_sub,
            )

            typer.echo("Running planner (fast mode)...")
            adapter = get_adapter(config)

            def llm_call_fast(prompt: str) -> str:
                response = adapter.call_for_json(system_prompt, prompt)
                return response.content

            plan_data = validate_with_retry(
                llm_call_fast, user_message, "plan", config, project_dir
            )

            save_dual(plan_data, project_dir / "PLAN.json", project_dir / "PLAN.md")
            typer.echo(typer.style("PLAN.json + PLAN.md saved.", fg=typer.colors.GREEN))

            plan_md = (project_dir / "PLAN.md").read_text(encoding="utf-8")
            approve_plan(state, project_dir / "STATE.json", plan_md)

            # Set synthetic approvals for skipped stages (FAST-03)
            state.approvals["research_approved"] = True
            state.approvals["design_approved"] = True

            sm.transition(Stage.PLAN)
            state.current_stage = (
                Stage.PLAN.value
            )  # CRITICAL: sync ProjectState manually
            state.metadata["skipped_stages"] = _json.dumps(sorted(skip_stages))
            state.add_history(
                "plan",
                "Fast mode: research and design skipped. Plan completed and approved.",
            )
            save_state(state, project_dir / "STATE.json")
            typer.echo(
                typer.style(
                    "Plan approved. Stage: plan (fast mode)", fg=typer.colors.GREEN
                )
            )

        else:
            # --- NORMAL MODE PATH ---
            sm = StateMachine(Stage(state.current_stage), state.approvals)

            if not sm.can_transition(Stage.PLAN):
                typer.echo(
                    typer.style(
                        f"Cannot transition from {state.current_stage} to {Stage.PLAN.value}",
                        fg=typer.colors.RED,
                    )
                )
                raise typer.Exit(code=1)

            check_preflight(Stage.PLAN, project_dir)

            system_prompt, user_template = load_prompt("planner")
            project_name = project_dir.parent.name
            brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")
            research_json = (project_dir / "RESEARCH.json").read_text(encoding="utf-8")
            design_json = (project_dir / "DESIGN.json").read_text(encoding="utf-8")
            user_message = render_prompt(
                user_template,
                project_name=project_name,
                brief_content=brief_content,
                research_json=research_json,
                design_json=design_json,
            )

            typer.echo("Running planner...")
            adapter = get_adapter(config)

            def llm_call(prompt: str) -> str:
                response = adapter.call_for_json(system_prompt, prompt)
                return response.content

            plan_data = validate_with_retry(
                llm_call, user_message, "plan", config, project_dir
            )

            save_dual(plan_data, project_dir / "PLAN.json", project_dir / "PLAN.md")
            typer.echo(typer.style("PLAN.json + PLAN.md saved.", fg=typer.colors.GREEN))

            plan_md = (project_dir / "PLAN.md").read_text(encoding="utf-8")
            approve_plan(state, project_dir / "STATE.json", plan_md)

            sm.transition(Stage.PLAN)
            state.current_stage = (
                Stage.PLAN.value
            )  # CRITICAL: sync ProjectState manually
            state.add_history("plan", "Plan completed and approved")
            save_state(state, project_dir / "STATE.json")
            typer.echo(typer.style("Plan approved. Stage: plan", fg=typer.colors.GREEN))

    except ApprovalError:
        typer.echo(
            typer.style("Plan rejected. Stage unchanged.", fg=typer.colors.YELLOW)
        )
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


@app.command()
def execute(
    task: Annotated[
        int | None, typer.Option("--task", help="Execute specific task (1-indexed)")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show changes without applying")
    ] = False,
) -> None:
    """Run the execute stage."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        if not sm.can_transition(Stage.EXECUTE):
            typer.echo(
                typer.style(
                    f"Cannot transition from {state.current_stage} to {Stage.EXECUTE.value}",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(code=1)

        config = load_config(project_dir.parent)
        check_preflight(Stage.EXECUTE, project_dir, skip_stages=_get_skip_stages(state))
        plan_json_str = (project_dir / "PLAN.json").read_text(encoding="utf-8")
        plan_data = PlanSchema.model_validate_json(plan_json_str)
        project_root = project_dir.parent

        # Build source_files context string for builder prompt
        source_files = _read_source_files(plan_data.touched_files, project_root, config)

        # Load and render builder prompt
        system_prompt, user_template = load_prompt("builder")
        project_name = project_dir.parent.name
        user_message = render_prompt(
            user_template,
            project_name=project_name,
            plan_json=plan_json_str,
            source_files=source_files,
            corrective_actions="",
        )

        # LLM call — use get_adapter(config) so the configured provider is used
        typer.echo("Running builder...")
        adapter = get_adapter(config)

        def llm_call(prompt: str) -> str:
            response = adapter.call_for_json(system_prompt, prompt)
            return response.content

        execution_log = validate_with_retry(
            llm_call, user_message, "execution_log", config, project_dir
        )

        # Scope lock — validate all changed files are within PLAN.json touched_files
        all_changed = [cf.path for tr in execution_log.tasks for cf in tr.changed_files]
        validate_scope(all_changed, plan_data.touched_files)

        # --task N filter (1-indexed)
        if task is not None:
            idx = task - 1
            if idx < 0 or idx >= len(execution_log.tasks):
                typer.echo(
                    typer.style(
                        f"Task index {task} out of range (1-{len(execution_log.tasks)})",
                        fg=typer.colors.RED,
                    )
                )
                raise typer.Exit(code=1)
            execution_log = ExecutionLogSchema(tasks=[execution_log.tasks[idx]])

        # Dry-run branch (BUILD-05) — show changes, no approvals, no writes
        if dry_run:
            for tr in execution_log.tasks:
                for cf in tr.changed_files:
                    desc = apply_patch(cf, project_root, dry_run=True)
                    typer.echo(f"  [DRY RUN] {desc}")
            typer.echo(
                typer.style(
                    "Dry run complete. No files modified.", fg=typer.colors.CYAN
                )
            )
            return

        # Normal: per-patch approval + apply (BUILD-03, BUILD-04)
        for tr in execution_log.tasks:
            for cf in tr.changed_files:
                # Preview the change (dry_run=True generates description without writing)
                desc = apply_patch(cf, project_root, dry_run=True)
                # Approval gate — raises ApprovalError on rejection
                approve_patch(state, project_dir / "STATE.json", desc)
                # Apply only after confirmed approval
                apply_patch(cf, project_root, dry_run=False)

        # Save dual output after all patches applied and approved
        save_dual(
            execution_log,
            project_dir / "EXECUTION_LOG.json",
            project_dir / "EXECUTION_LOG.md",
        )
        typer.echo(
            typer.style(
                "EXECUTION_LOG.json + EXECUTION_LOG.md saved.", fg=typer.colors.GREEN
            )
        )

        sm.transition(Stage.EXECUTE)
        state.current_stage = (
            Stage.EXECUTE.value
        )  # CRITICAL: sync ProjectState manually
        state.add_history("execute", "Execution completed and approved")
        save_state(state, project_dir / "STATE.json")
        typer.echo(
            typer.style("Execution complete. Stage: execute", fg=typer.colors.GREEN)
        )

    except ApprovalError:
        typer.echo(
            typer.style("Patch rejected. Execution stopped.", fg=typer.colors.YELLOW)
        )
        # exit code 0 — rejection is not an error
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


_MAX_REVISE_ITERATIONS = 2


@app.command()
def review() -> None:
    """Run the review stage."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        if not sm.can_transition(Stage.REVIEW):
            typer.echo(
                typer.style(
                    f"Cannot transition from {state.current_stage} to {Stage.REVIEW.value}",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(code=1)

        config = load_config(project_dir.parent)
        skip_stages = _get_skip_stages(state)
        check_preflight(Stage.REVIEW, project_dir, skip_stages=skip_stages)

        # Read prior artifacts for reviewer context
        plan_json_str = (project_dir / "PLAN.json").read_text(encoding="utf-8")
        plan_data = PlanSchema.model_validate_json(plan_json_str)
        project_root = project_dir.parent
        project_name = project_dir.parent.name

        # Load DESIGN.json and RESEARCH.json — use stubs in fast mode
        design_path = project_dir / "DESIGN.json"
        research_path = project_dir / "RESEARCH.json"
        if design_path.exists():
            design_json_str = design_path.read_text(encoding="utf-8")
        else:
            design_json_str = '{"note": "Fast mode: no design phase run."}'
        if research_path.exists():
            research_json_str = research_path.read_text(encoding="utf-8")
        else:
            research_json_str = '{"existing_conventions": []}'

        # Extract conventions from RESEARCH.json
        research_data = _json.loads(research_json_str)
        conventions = "\n".join(research_data.get("existing_conventions", []))

        # Main review + revise loop
        revise_count = int(state.metadata.get("revise_count", "0"))

        while True:
            # Read current execution log (may be updated during revise)
            execution_log_json = (project_dir / "EXECUTION_LOG.json").read_text(
                encoding="utf-8"
            )
            execution_log = ExecutionLogSchema.model_validate_json(execution_log_json)
            diff_text = generate_diff_text(execution_log)

            # Load and render reviewer prompt
            system_prompt, user_template = load_prompt("reviewer")
            user_message = render_prompt(
                user_template,
                project_name=project_name,
                diff_text=diff_text,
                plan_json=plan_json_str,
                design_json=design_json_str,
                conventions=conventions,
            )

            # LLM call — use get_adapter(config) so the configured provider is used
            typer.echo("Running reviewer...")
            adapter = get_adapter(config)

            def llm_call(prompt: str) -> str:
                response = adapter.call_for_json(system_prompt, prompt)
                return response.content

            review_data = validate_with_retry(
                llm_call, user_message, "review", config, project_dir
            )

            # Save dual output
            save_dual(
                review_data, project_dir / "REVIEW.json", project_dir / "REVIEW.md"
            )
            typer.echo(
                typer.style("REVIEW.json + REVIEW.md saved.", fg=typer.colors.GREEN)
            )

            review_md = (project_dir / "REVIEW.md").read_text(encoding="utf-8")

            # Approval gate
            approve_review(state, project_dir / "STATE.json", review_md)

            # Check verdict
            from minilegion.core.schemas import Verdict

            if review_data.verdict == Verdict.PASS:
                # Done — transition to review stage
                sm.transition(Stage.REVIEW)
                state.current_stage = Stage.REVIEW.value
                state.add_history("review", "Review passed and approved")
                save_state(state, project_dir / "STATE.json")
                typer.echo(
                    typer.style("Review passed. Stage: review", fg=typer.colors.GREEN)
                )
                return

            # verdict == revise
            if revise_count >= _MAX_REVISE_ITERATIONS:
                typer.echo(
                    typer.style(
                        f"Revise limit reached ({_MAX_REVISE_ITERATIONS} iterations). "
                        "Manual intervention required.",
                        fg=typer.colors.RED,
                    )
                )
                typer.echo("Corrective actions needed:")
                for action in review_data.corrective_actions:
                    typer.echo(f"  - {action}")
                return  # exit 0 — human escalation

            # Offer re-design if design does not conform
            if not review_data.design_conformity.conforms:
                typer.echo(
                    typer.style(
                        "Design conformity failure detected. Re-design recommended.",
                        fg=typer.colors.YELLOW,
                    )
                )
                want_redesign = typer.confirm("Re-design before re-executing?")
                if want_redesign:
                    sm.transition(Stage.DESIGN)
                    state.current_stage = Stage.DESIGN.value
                    state.add_history("review", "Backtracked to design for re-design")
                    save_state(state, project_dir / "STATE.json")
                    typer.echo(
                        typer.style(
                            "Backtracked to design stage.", fg=typer.colors.YELLOW
                        )
                    )
                    return  # exit 0 — user will re-run design manually

            # Increment revise count and re-run builder
            revise_count += 1
            state.metadata["revise_count"] = str(revise_count)
            save_state(state, project_dir / "STATE.json")

            typer.echo(
                typer.style(
                    f"Verdict: revise (iteration {revise_count}/{_MAX_REVISE_ITERATIONS}). "
                    "Re-running builder with corrective actions...",
                    fg=typer.colors.YELLOW,
                )
            )

            # Build corrective_actions context string for builder prompt
            corrective_text = ""
            if review_data.corrective_actions:
                corrective_text = (
                    "\n## Corrective Actions from Review\n"
                    + "\n".join(f"- {a}" for a in review_data.corrective_actions)
                    + "\n"
                )

            # Re-run builder with corrective actions injected
            source_files = _read_source_files(
                plan_data.touched_files, project_root, config
            )
            builder_system, builder_template = load_prompt("builder")
            builder_message = render_prompt(
                builder_template,
                project_name=project_name,
                plan_json=plan_json_str,
                source_files=source_files,
                corrective_actions=corrective_text,
            )

            typer.echo("Re-running builder...")
            builder_adapter = get_adapter(config)

            def builder_llm_call(prompt: str) -> str:
                response = builder_adapter.call_for_json(builder_system, prompt)
                return response.content

            new_execution_log = validate_with_retry(
                builder_llm_call,
                builder_message,
                "execution_log",
                config,
                project_dir,
            )

            # Scope validation
            all_changed = [
                cf.path for tr in new_execution_log.tasks for cf in tr.changed_files
            ]
            validate_scope(all_changed, plan_data.touched_files)

            # Per-patch approval + apply
            for tr in new_execution_log.tasks:
                for cf in tr.changed_files:
                    desc = apply_patch(cf, project_root, dry_run=True)
                    approve_patch(state, project_dir / "STATE.json", desc)
                    apply_patch(cf, project_root, dry_run=False)

            # Save updated execution log
            save_dual(
                new_execution_log,
                project_dir / "EXECUTION_LOG.json",
                project_dir / "EXECUTION_LOG.md",
            )

            # Loop back to reviewer
            execution_log = new_execution_log

    except ApprovalError:
        typer.echo(
            typer.style("Review rejected. Stage unchanged.", fg=typer.colors.YELLOW)
        )
        # exit code 0 — rejection is not an error
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


@app.command()
def archive() -> None:
    """Run the archive stage — finalize pipeline cycle deterministically."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        if not sm.can_transition(Stage.ARCHIVE):
            typer.echo(
                typer.style(
                    f"Cannot transition from {state.current_stage} to {Stage.ARCHIVE.value}",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(code=1)

        # No load_config() — archive makes zero LLM calls (ARCH-01)
        skip_stages = _get_skip_stages(state)
        check_preflight(Stage.ARCHIVE, project_dir, skip_stages=skip_stages)

        # Read artifacts (ARCH-02, ARCH-03)
        execution_log = ExecutionLogSchema.model_validate_json(
            (project_dir / "EXECUTION_LOG.json").read_text(encoding="utf-8")
        )
        review_data = ReviewSchema.model_validate_json(
            (project_dir / "REVIEW.json").read_text(encoding="utf-8")
        )
        # DESIGN.json may be absent in fast mode
        design_path = project_dir / "DESIGN.json"
        if design_path.exists():
            design_data = DesignSchema.model_validate_json(
                design_path.read_text(encoding="utf-8")
            )
        else:
            design_data = None

        # Run coherence checks (non-blocking) — COHR-01..05
        issues = check_coherence(project_dir)
        for issue in issues:
            prefix = "[WARNING]" if issue.severity == "warning" else "[ERROR]"
            typer.echo(
                typer.style(
                    f"{prefix} {issue.check_name}: {issue.message}",
                    fg=typer.colors.YELLOW
                    if issue.severity == "warning"
                    else typer.colors.RED,
                )
            )

        # Update state (ARCH-02)
        task_ids = [tr.task_id for tr in execution_log.tasks]
        state.completed_tasks = task_ids
        state.metadata["final_verdict"] = review_data.verdict.value

        # Store coherence issues in metadata (non-blocking)
        if issues:
            state.metadata["coherence_issues"] = _json.dumps(
                [
                    {
                        "check": i.check_name,
                        "severity": i.severity,
                        "message": i.message,
                    }
                    for i in issues
                ]
            )

        # Write DECISIONS.md (ARCH-03) — write before save_state
        if design_data is not None:
            decisions_content = render_decisions_md(design_data)
        else:
            decisions_content = (
                "# Architecture Decisions\n\n_Fast mode: no design phase run._\n"
            )
        write_atomic(project_dir / "DECISIONS.md", decisions_content)

        # Transition state — CRITICAL: set .value for JSON serializability
        sm.transition(Stage.ARCHIVE)
        state.current_stage = Stage.ARCHIVE.value  # sync gap fix
        state.add_history(
            "archive",
            f"Pipeline archived. {len(task_ids)} tasks. Verdict: {review_data.verdict.value}.",
        )
        save_state(state, project_dir / "STATE.json")

        typer.echo(
            typer.style(
                f"Archiving... {len(task_ids)} tasks completed. "
                f"Verdict: {review_data.verdict.value}. DECISIONS.md written.",
                fg=typer.colors.GREEN,
            )
        )

    except MiniLegionError as exc:
        # NOTE: No ApprovalError block — archive has no approval gate
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
