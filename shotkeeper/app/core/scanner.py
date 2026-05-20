from __future__ import annotations

from pathlib import Path

from app.models.photo import Photo
from app.utils.paths import RESULT_DIR_NAME, is_image_file


def scan_images(folder: str | Path, recursive: bool = True) -> list[Photo]:
    root = Path(folder).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")

    iterator = root.rglob("*") if recursive else root.iterdir()
    photos: list[Photo] = []
    for path in iterator:
        if RESULT_DIR_NAME in path.parts:
            continue
        if is_image_file(path):
            photos.append(Photo(path=path.resolve()))
    return sorted(photos, key=lambda photo: str(photo.path).lower())
