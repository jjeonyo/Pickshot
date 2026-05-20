# ShotKeeper Agent Notes

- Keep MVP simple and local-first.
- Do not implement destructive deletion; use keep/review/trash_candidate folders only.
- Prefer deterministic OpenCV/Pillow/imagehash logic over deep learning models.
- Verify core behavior with pytest before claiming completion.
- When photo selection criteria change, update `docs/photo-selection-criteria.md` in the same change.
- When scoring or best-shot recommendation criteria change, update `docs/photo-recommendation-criteria.md` in the same change.
