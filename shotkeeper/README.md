# ShotKeeper

ShotKeeper is a local desktop MVP that scans a folder of photos, groups visually similar images, scores sharpness, recommends the best shot in each group, and lets the user sort files into `keep`, `review`, and `trash_candidate` result folders without deleting originals.

## Features

- Select an image folder from the UI
- Scan common image formats recursively
- Skip corrupt or unreadable matching files without aborting the whole folder analysis
- Compute perceptual hashes with `imagehash`
- Group similar photos by hash distance
- Score image sharpness with OpenCV Laplacian variance
- Recommend the sharpest image per group
- Classify files into `keep`, `review`, or `trash_candidate`
- Copy or move selected images to result folders


## Photo Selection Criteria

Photo selection rules are documented in [`docs/photo-selection-criteria.md`](docs/photo-selection-criteria.md). Best-shot scoring rules are documented in [`docs/photo-recommendation-criteria.md`](docs/photo-recommendation-criteria.md). Update the matching document whenever those criteria change.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Test

```bash
pytest
```

## Safety

MVP never deletes images. Classification copies or moves files into:

```text
<selected-folder>/ShotKeeper_Result/
├── keep/
├── review/
└── trash_candidate/
```
