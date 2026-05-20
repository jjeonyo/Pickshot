# Ralph Evidence: project-analysis-improvements

## Implemented
- Added `shotkeeper/app/core/analysis.py` as a testable analysis orchestrator.
- The orchestrator scans images, skips hash/decode failures per file, pre-checks OpenCV readability per file, then scores and groups only analyzable photos.
- Updated `MainWindow.analyze_folder` to use the orchestrator and show analyzed/skipped counts.
- Added regression tests for corrupt `.jpg` handling.
- Updated README and photo selection criteria documentation for unreadable-file skip behavior.

## Fresh verification
- Timestamp: 2026-05-19T17:09:53Z
- `./.venv/bin/python -m pytest -q` from `shotkeeper/`: 11 passed in 0.61s.
- `./.venv/bin/python -m compileall -q app tests` from `shotkeeper/`: passed.

## Changed files
- `shotkeeper/app/core/analysis.py`
- `shotkeeper/app/ui/main_window.py`
- `shotkeeper/tests/test_analysis.py`
- `shotkeeper/README.md`
- `shotkeeper/docs/photo-selection-criteria.md`
