---
phase: 15-evidence-pipeline-validate-advance-gates
plan: "02"
type: execute-summary
completed: 2026-03-12
requirements-completed: [VAD-03, VAD-04, CFG-07]
files-modified:
  - minilegion/cli/commands.py
  - minilegion/core/config.py
  - tests/test_cli_validate_advance.py
  - tests/test_config.py
  - tests/test_cli.py
verification:
  - python -m pytest tests/test_cli_validate_advance.py::TestAdvancePass tests/test_cli_validate_advance.py::TestAdvanceReject tests/test_config.py::TestWorkflowConfig tests/test_cli.py::TestCLIHelp::test_all_commands_registered -q
---

# Phase 15 Plan 02 Summary

- Added `WorkflowConfig` defaults in `minilegion/core/config.py` (`strict_mode=True`, `require_validation=True`) and wired it into `MiniLegionConfig` as an optional backward-compatible section.
- Implemented `minilegion advance` in `minilegion/cli/commands.py` as the only forward stage mutator, gated on passing current-stage evidence (except `init`), with clear refusal messages for missing/failing evidence.
- Ensured successful `advance` appends durable history events and updates state by exactly one forward stage.
- Added focused regression coverage in `tests/test_cli_validate_advance.py` (`TestAdvancePass`/`TestAdvanceReject`) plus config compatibility coverage in `tests/test_config.py::TestWorkflowConfig`.
- Verification passed: `python -m pytest tests/test_cli_validate_advance.py::TestAdvancePass tests/test_cli_validate_advance.py::TestAdvanceReject tests/test_config.py::TestWorkflowConfig tests/test_cli.py::TestCLIHelp::test_all_commands_registered -q`.
