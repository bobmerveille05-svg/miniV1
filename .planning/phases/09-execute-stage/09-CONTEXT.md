# Phase 9 Context: Execute Stage

## Phase Goal

User can run `minilegion execute` and see EXECUTION_LOG.json produced with per-task patches that are individually approved before application.

## Requirements to Satisfy

- BUILD-01: Builder role receives PLAN.json + source files and produces EXECUTION_LOG.json with structured patches
- BUILD-02: EXECUTION_LOG.json contains per-task: task_id, changed_files (path, action, content), unchanged_files, tests_run, test_result, blockers, out_of_scope_needed
- BUILD-03: Each patch is displayed to user for approval before application
- BUILD-04: Patcher module applies approved patches to the filesystem
- BUILD-05: Dry-run mode shows what would change without modifying files

## Decisions (YOLO auto-generated)

1. **Two plans** — Phase 9 has two distinct deliverables: (A) patcher module (new file, filesystem operations), (B) execute() command (LLM orchestration + per-patch loop). Splitting reduces risk.

2. **Patcher module** — `minilegion/core/patcher.py` provides `apply_patch(changed_file: ChangedFile, project_root: Path, dry_run: bool) -> str`. For `create`/`modify`: write full content atomically. For `delete`: remove file. Returns a diff-like description string for display. Dry-run returns the description without touching files.

3. **execute() pattern** — Same pipeline start as design/plan, then differs: after validate_with_retry produces ExecutionLogSchema, iterate over task results; for each changed_file, call approve_patch(state, state_path, diff_text) then apply_patch(). save_dual writes EXECUTION_LOG.json + EXECUTION_LOG.md after all patches applied.

4. **Scope lock** — After LLM returns ExecutionLogSchema, call validate_scope() on all changed_files against PLAN.json touched_files. Scope violation raises ValidationError → exit 1.

5. **--task N** — Filter ExecutionLogSchema.tasks to the single task with matching id or index before the patch loop. If not found, exit 1.

6. **--dry-run** — Pass dry_run=True to apply_patch(); display changes but skip approve_patch() gate entirely (no confirmation needed for dry-run) and skip save_dual + state transition.

7. **approve_patch already exists** — approval.py has `approve_patch(state, state_path, diff_text)` — sets `execute_approved`. Import it in commands.py.

8. **State transition** — After all patches applied and approved: sm.transition(Stage.EXECUTE) + state.current_stage = Stage.EXECUTE.value + save_state(). The execute_approved flag is set by the last approve_patch call.

9. **Source files for prompt** — Read touched_files from PLAN.json; read each file that exists in the project root (cwd). Cap at config.scan_max_file_size. Pass as formatted string to builder prompt.
