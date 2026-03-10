"""MiniLegion CLI commands — all 8 pipeline commands.

Commands register themselves with the Typer app imported from minilegion.cli.
"""

from __future__ import annotations

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
)
from minilegion.core.context_scanner import scan_codebase
from minilegion.core.exceptions import (
    ConfigError,
    InvalidTransitionError,
    MiniLegionError,
)
from minilegion.core.file_io import write_atomic
from minilegion.core.preflight import check_preflight
from minilegion.core.renderer import save_dual
from minilegion.core.retry import validate_with_retry
from minilegion.core.state import (
    ProjectState,
    Stage,
    StateMachine,
    load_state,
    save_state,
)
from minilegion.prompts.loader import load_prompt, render_prompt
from minilegion.adapters.openai_adapter import OpenAIAdapter


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

        # Preflight validation (requires BRIEF.md + brief_approved in STATE.json)
        check_preflight(Stage.RESEARCH, project_dir)

        # Scan codebase for context
        typer.echo("Scanning codebase...")
        codebase_context = scan_codebase(project_dir, config)

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

        # LLM call — OpenAIAdapter takes full config, NOT individual fields
        typer.echo("Running researcher...")
        adapter = OpenAIAdapter(config)

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
        adapter = OpenAIAdapter(config)

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
    _pipeline_stub(
        Stage.PLAN,
        extra_info=f"fast={fast}, skip_research_design={skip_research_design}",
    )


@app.command()
def execute(
    task: Annotated[
        int | None, typer.Option("--task", help="Execute specific task")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show changes without applying")
    ] = False,
) -> None:
    """Run the execute stage."""
    _pipeline_stub(
        Stage.EXECUTE,
        extra_info=f"task={task}, dry_run={dry_run}",
    )


@app.command()
def review() -> None:
    """Run the review stage."""
    _pipeline_stub(Stage.REVIEW)
