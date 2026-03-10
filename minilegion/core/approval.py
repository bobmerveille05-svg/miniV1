"""Human approval gates for MiniLegion pipeline.

Each approval gate displays a summary of the artifact, prompts Y/N via
``typer.confirm()``, and either persists the approval atomically or raises
``ApprovalError`` without touching STATE.json.

CRITICAL (APRV-06): The ``approve()`` function MUST NOT modify the ``state``
object or call ``save_state()`` before ``typer.confirm()`` returns True.
Rejection raises immediately — no mutation, no rollback needed.

Gate mapping:
    approve_brief   -> brief_approved
    approve_research -> research_approved
    approve_design  -> design_approved
    approve_plan    -> plan_approved
    approve_patch   -> execute_approved
"""

from pathlib import Path

import typer

from minilegion.core.exceptions import ApprovalError
from minilegion.core.state import ProjectState, save_state


def approve(
    gate_name: str,
    summary: str,
    state: ProjectState,
    state_path: Path,
) -> bool:
    """Core approval function shared by all gates.

    Displays *summary* to the user, prompts ``Approve {gate_name}?``.

    On approval:
        1. Sets ``state.approvals[gate_name] = True``
        2. Adds a history entry with action ``"approval"``
        3. Persists state atomically via ``save_state()``
        4. Returns ``True``

    On rejection:
        Raises ``ApprovalError`` immediately — **no** state mutation occurs.

    Args:
        gate_name: Approval key (e.g. ``"brief_approved"``).
        summary: Human-readable summary displayed before the prompt.
        state: Current project state (mutated only on approval).
        state_path: Path to STATE.json for atomic persistence.

    Returns:
        ``True`` if approved.

    Raises:
        ApprovalError: If the user rejects the gate.
    """
    typer.echo(summary)
    approved = typer.confirm(f"Approve {gate_name}?")

    if not approved:
        raise ApprovalError(f"Rejected: {gate_name}")

    # --- Mutation only after confirmed approval ---
    state.approvals[gate_name] = True
    state.add_history("approval", f"Approved: {gate_name}")
    save_state(state, state_path)
    return True


# ---------------------------------------------------------------------------
# Gate-specific wrapper functions
# ---------------------------------------------------------------------------


def approve_brief(state: ProjectState, state_path: Path, brief_content: str) -> bool:
    """Approval gate for the brief artifact (APRV-01).

    Displays the brief content and prompts for approval.
    Sets ``brief_approved`` in STATE.json on acceptance.
    """
    summary = f"=== Brief for Approval ===\n\n{brief_content}\n"
    return approve("brief_approved", summary, state, state_path)


def approve_research(
    state: ProjectState, state_path: Path, research_summary: str
) -> bool:
    """Approval gate for the research artifact (APRV-02).

    Displays the research summary and prompts for approval.
    Sets ``research_approved`` in STATE.json on acceptance.
    """
    summary = f"=== Research Summary for Approval ===\n\n{research_summary}\n"
    return approve("research_approved", summary, state, state_path)


def approve_design(state: ProjectState, state_path: Path, design_summary: str) -> bool:
    """Approval gate for the design artifact (APRV-03).

    Displays the design summary and prompts for approval.
    Sets ``design_approved`` in STATE.json on acceptance.
    """
    summary = f"=== Design for Approval ===\n\n{design_summary}\n"
    return approve("design_approved", summary, state, state_path)


def approve_plan(state: ProjectState, state_path: Path, plan_summary: str) -> bool:
    """Approval gate for the plan artifact (APRV-04).

    Displays the plan summary and prompts for approval.
    Sets ``plan_approved`` in STATE.json on acceptance.
    """
    summary = f"=== Plan for Approval ===\n\n{plan_summary}\n"
    return approve("plan_approved", summary, state, state_path)


def approve_patch(state: ProjectState, state_path: Path, diff_text: str) -> bool:
    """Approval gate for the patch/execute artifact (APRV-05).

    Displays the diff text and prompts for approval.
    Sets ``execute_approved`` in STATE.json on acceptance.
    """
    summary = f"=== Patch for Approval ===\n\n{diff_text}\n"
    return approve("execute_approved", summary, state, state_path)


def approve_review(state: ProjectState, state_path: Path, review_summary: str) -> bool:
    """Approval gate for the review artifact.

    Displays the review summary and prompts for approval.
    Sets ``review_approved`` in STATE.json on acceptance.
    """
    summary = f"=== Review for Approval ===\n\n{review_summary}\n"
    return approve("review_approved", summary, state, state_path)
