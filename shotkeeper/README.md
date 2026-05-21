# ShotKeeper

ShotKeeper is a local desktop MVP that scans a folder of photos, groups visually similar images, scores sharpness, recommends the best shot in each group, and lets the user sort files into `keep`, `review`, and `trash_candidate` result folders without deleting originals.

## Features

- Select an image folder from the UI
- macOS Apple 사진 보관함을 PhotoKit으로 열고 사용자가 선택한 사진만 분석
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

일반 폴더 분석만 사용할 때는 다음처럼 실행할 수 있습니다.

```bash
python main.py
```

Apple 사진첩 연동을 사용할 때는 macOS 개인정보 보호 설명 문구가 들어 있는 앱 번들 런처로 실행해야 합니다. 일반 `python main.py`로 사진 보관함에 접근하면 macOS가 프로세스를 강제 종료할 수 있습니다.

```bash
python scripts/run_macos_app.py
```

## Apple Photos Library

macOS에서는 `Apple 사진첩 열기`를 누르면 ShotKeeper 안에서 썸네일 그리드로 Apple 사진 보관함을 확인하고, 앨범 필터와 검색으로 범위를 좁힌 뒤 여러 장을 선택할 수 있습니다. 앱은 사진첩 전체를 분석하지 않고, 사용자가 선택한 항목만 `~/Pictures/ShotKeeper_Apple_Photos_Cache/` 아래 분석용 JPEG 캐시로 만든 뒤 기존 유사 사진 그룹/베스트샷 분석을 실행합니다. 원본 보관함은 수정하지 않습니다. 첫 실행 시 macOS가 사진 접근 권한을 요청할 수 있습니다.

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
