# PRD: Robust folder analysis for ShotKeeper

## Decision
Implement a bounded robustness improvement: valid photos should still be analyzed when a folder contains corrupt or unreadable image files. Unreadable files are skipped and reported instead of aborting the entire analysis.

## Drivers
1. Real photo folders commonly include broken transfers, partially synced files, or unsupported/corrupt files with supported extensions.
2. ShotKeeper is local-first and should avoid destructive actions; skipping with a visible summary is safer than failing the run.
3. Existing deterministic OpenCV/Pillow/imagehash logic remains the right implementation surface.

## Alternatives considered
- Add new image codecs/dependencies such as HEIC support: rejected because dependency expansion is outside the current request and AGENTS says keep MVP simple.
- Catch every exception only in the UI: rejected because behavior would be hard to unit-test and reuse.
- Silently skip unreadable files: rejected because the user needs evidence that some files were not analyzed.

## Scope
- Add a core analysis orchestrator that returns groups plus skipped file records.
- Keep existing low-level hash/quality functions strict for direct callers and tests.
- Update UI status/messages to include skipped count.
- Add tests for corrupt images and all-invalid folders.
- Update user-facing docs to document skip behavior.

## Acceptance criteria
- A corrupt file with a supported extension does not prevent valid images from being grouped.
- Skipped files include a path and reason.
- If no valid analyzable photos remain, the UI/core can report no analyzable images rather than crashing.
- Existing tests continue to pass.
- New targeted tests cover the skip path.
