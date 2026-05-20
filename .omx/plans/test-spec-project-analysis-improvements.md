# Test Spec: Robust folder analysis

## Unit tests
- Create one valid image and one corrupt `.jpg`; `analyze_images` returns groups for the valid image and one skipped entry.
- Create only a corrupt `.jpg`; `analyze_images` returns no groups and one skipped entry.

## Regression tests
- Existing grouping, hashing, quality, and recommendation tests must still pass.

## Verification command
- From `shotkeeper/`: `./.venv/bin/python -m pytest -q`
