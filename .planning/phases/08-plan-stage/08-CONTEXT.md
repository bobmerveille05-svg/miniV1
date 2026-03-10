# Phase 8 Context: Plan Stage

## Phase Goal

User can run `minilegion plan` and see PLAN.json + PLAN.md produced with tasks, touched_files, and all required fields.

## Requirements to Satisfy

- PLAN-01: Planner role receives DESIGN.json + RESEARCH.json + BRIEF.md and produces PLAN.json + PLAN.md
- PLAN-02: PLAN.json contains: objective, design_ref, assumptions, tasks (with id, name, description, files, depends_on, component), touched_files, risks, success_criteria, test_plan
- PLAN-03: Each task references a component from DESIGN.json
- PLAN-04: touched_files must be a subset of files declared in DESIGN.json components
- PLAN-05: Planner prompt enforces "decompose, don't design" — design decisions are already made

## Decisions (YOLO auto-generated)

1. **Single plan** — Phase 8 is structurally identical to Phase 7 (design stage). The plan() command replaces a stub with the same pipeline pattern. One plan is sufficient.
2. **Pattern reuse** — plan() follows the exact same pattern as design(): find_project_dir → load_config(parent) → load_state → StateMachine → can_transition(Stage.PLAN) → check_preflight → read inputs (BRIEF.md, RESEARCH.json, DESIGN.json) → load_prompt("planner") + render_prompt → OpenAIAdapter(config) → validate_with_retry("plan", ...) → save_dual(PLAN.json, PLAN.md) → approve_plan → sm.transition(Stage.PLAN) + state.current_stage = Stage.PLAN.value + save_state.
3. **approve_plan already imported** — approval.py already has approve_plan; just needs to be imported in commands.py.
4. **Test pattern** — 10 tests mirroring TestDesignCommand with design-stage state fixture (current_stage=design, design_approved=True).
5. **PLAN-03 / PLAN-04** — These cross-field coherence checks (task.component in DESIGN.json, touched_files ⊆ DESIGN files) are enforced at the **prompt level** (planner.md already instructs this) and are Phase 11 Coherence concerns for mechanical validation. Phase 8 delivers the command; schema validation is already in PlanSchema.
