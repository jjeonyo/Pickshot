from __future__ import annotations

import shutil
from pathlib import Path

from app.models.photo import Classification, Photo
from app.utils.paths import CLASSIFICATION_DIRS, result_root


def ensure_result_dirs(source_folder: str | Path) -> dict[str, Path]:
    root = result_root(Path(source_folder).expanduser().resolve())
    dirs: dict[str, Path] = {}
    for name in CLASSIFICATION_DIRS:
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        dirs[name] = directory
    return dirs


def unique_destination(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def export_photo(photo: Photo, source_folder: str | Path, action: str = "copy") -> Path:
    if action not in {"copy", "move"}:
        raise ValueError("action must be 'copy' or 'move'")
    dirs = ensure_result_dirs(source_folder)
    destination = unique_destination(dirs[photo.classification], photo.path.name)
    if action == "copy":
        return Path(shutil.copy2(photo.path, destination))
    return Path(shutil.move(photo.path, destination))


def export_photos(photos: list[Photo], source_folder: str | Path, action: str = "copy") -> list[Path]:
    return [export_photo(photo, source_folder, action=action) for photo in photos]


def set_classification(photo: Photo, classification: Classification) -> None:
    if classification not in CLASSIFICATION_DIRS:
        raise ValueError(f"Invalid classification: {classification}")
    photo.classification = classification
