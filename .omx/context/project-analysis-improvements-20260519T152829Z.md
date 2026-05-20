# Autopilot Context Snapshot: project-analysis-improvements

## Task statement
Analyze the Pickshot/ShotKeeper project, identify practical improvement points, implement a bounded improvement, verify it, and complete code review through the Autopilot loop.

## Desired outcome
A small, safe improvement to the local-first ShotKeeper MVP that improves real-folder robustness without changing the no-delete safety model, with tests and documentation updated where behavior/criteria are affected.

## Known facts/evidence
- Project code lives under `shotkeeper/`.
- `shotkeeper/AGENTS.md` requires: local-first MVP, no destructive deletion, deterministic OpenCV/Pillow/imagehash over deep learning, pytest verification, and criteria docs updated when photo selection/scoring criteria change.
- Current tests pass with `./.venv/bin/python -m pytest -q`: 9 passed.
- Current UI analysis path scans images, attaches hashes, attaches quality scores, then groups photos.
- Current pipeline aborts the whole folder analysis if one image is unreadable/corrupt during hash or quality scoring.

## Constraints
- Do not add dependencies unless explicitly requested.
- Do not implement destructive deletion.
- Keep changes small and reversible.
- Preserve existing core behavior for valid images.
- Verify with pytest before claiming completion.

## Unknowns/open questions
- No Git repository is present in `/Users/harry/Workspace/Pickshot/Pickshot`, so diff/review must be file-based rather than git-diff based.
- No product preference was provided; choose the highest-confidence local robustness improvement.

## Likely codebase touchpoints
- `shotkeeper/app/core/analysis.py` (new orchestration helper)
- `shotkeeper/app/ui/main_window.py` (use orchestration helper and show skipped count)
- `shotkeeper/tests/` (new tests for corrupt/unreadable skip behavior)
- `shotkeeper/README.md` and/or docs when user-visible behavior changes
