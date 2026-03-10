# Phase 9 Research: Execute Stage

## Existing Infrastructure

### Already in Place

**`minilegion/core/scope_lock.py`**
- `validate_scope(changed_files, allowed_files)` — raises `ValidationError` if any changed file is out of scope (GUARD-04)
- `normalize_path()` handles cross-platform path normalization (GUARD-05)

**`minilegion/core/approval.py`**
- `approve_patch(state, state_path, diff_text)` — sets `execute_approved` (APRV-05)
- Already fully implemented (lines 118-125)

**`minilegion/core/preflight.py`**
- `Stage.EXECUTE` already declared — requires `BRIEF.md`, `RESEARCH.json`, `DESIGN.json`, `PLAN.json` and approvals `brief_approved`, `research_approved`, `design_approved`, `plan_approved`

**`minilegion/core/schemas.py`**
- `ExecutionLogSchema` — `tasks: list[TaskResult]`
- `TaskResult` — `task_id`, `changed_files: list[ChangedFile]`, `unchanged_files`, `tests_run`, `test_result`, `blockers`, `out_of_scope_needed`
- `ChangedFile` — `path: str`, `action: Literal["create", "modify", "delete"]`, `content: str`

**`minilegion/core/registry.py`**
- `"execution_log"` registered in SCHEMA_REGISTRY — `validate_with_retry("execution_log", ...)` works

**`minilegion/core/renderer.py`**
- `render_execution_log_md()` fully implemented
- `save_dual()` dispatches to it

**`minilegion/prompts/builder.md`**
- System: "build, don't redesign", JSON-only output
- USER_TEMPLATE variables: `{{project_name}}`, `{{plan_json}}`, `{{source_files}}`

**`minilegion/cli/commands.py`**
- `execute()` command exists but calls `_pipeline_stub(Stage.EXECUTE, ...)`
- Accepts `--task` (int|None) and `--dry-run` (bool) flags — must be preserved
- `approve_patch` NOT yet imported — must add

### What Needs to Be Built

**`minilegion/core/patcher.py`** — NEW file:
```python
def apply_patch(changed_file: ChangedFile, project_root: Path, dry_run: bool = False) -> str:
    """Apply a single file patch. Returns description string.
    
    create/modify: write_atomic(path, content) unless dry_run
    delete: path.unlink() unless dry_run
    Returns: human-readable description of the change
    """
```

**`minilegion/cli/commands.py`** changes:
1. Import `approve_patch` from `minilegion.core.approval`
2. Import `apply_patch` from `minilegion.core.patcher`
3. Import `validate_scope` from `minilegion.core.scope_lock`
4. Replace `_pipeline_stub(Stage.EXECUTE, ...)` with full implementation

### execute() Flow

```
find_project_dir() → load_config(parent) → load_state → StateMachine →
can_transition(Stage.EXECUTE) → check_preflight(Stage.EXECUTE, project_dir) →
read PLAN.json, build source_files string from plan.touched_files →
load_prompt("builder") + render_prompt(project_name, plan_json, source_files) →
OpenAIAdapter(config) → validate_with_retry(llm_call, user_message, "execution_log", config, project_dir) →

# Scope check
validate_scope(all_changed_file_paths, plan.touched_files) →  # raises ValidationError on violation

# Optional: --task N filter
if task arg: filter execution_log.tasks to matching task only

# Dry-run branch
if dry_run:
    for each changed_file: apply_patch(cf, cwd, dry_run=True) → print description
    typer.echo("Dry run complete. No files modified.")
    return  # no approval, no save, no state transition

# Normal branch: per-patch approval loop
for each task_result in execution_log.tasks:
    for each changed_file in task_result.changed_files:
        diff_text = apply_patch(cf, cwd, dry_run=True)  # get description first
        approve_patch(state, state_path, diff_text)     # raises ApprovalError if rejected
        apply_patch(cf, cwd, dry_run=False)             # actually apply

# After all patches approved and applied:
save_dual(execution_log, EXECUTION_LOG.json, EXECUTION_LOG.md)
sm.transition(Stage.EXECUTE)
state.current_stage = Stage.EXECUTE.value
save_state(state, project_dir / "STATE.json")
```

### Key Design Points

- `apply_patch` preview (dry_run=True) is called BEFORE approve_patch to generate the diff description
- `apply_patch` real (dry_run=False) is called AFTER approve_patch confirms
- `save_dual` is called AFTER all patches applied (not before approval loop)
- State transition happens only after all patches approved and applied
- ApprovalError on any patch rejection: log "Patch rejected. Stopping." + exit 0 (not an error)
- `validate_scope` raises `ValidationError` (subclass of `MiniLegionError`) → caught by MiniLegionError handler → exit 1

### Source Files String Format

```
## {path}
{content}
---
```

Cap each file at config.scan_max_file_size bytes. If file doesn't exist (new file being created), skip it.

### --task N Semantics

`--task N` is 1-indexed (task number in list, not task.id). Filter `execution_log.tasks` to `[tasks[N-1]]`. If N out of range, print error and exit 1.
