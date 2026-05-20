from __future__ import annotations

from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
RESULT_DIR_NAME = "ShotKeeper_Result"
CLASSIFICATION_DIRS = ("keep", "review", "trash_candidate")


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def result_root(source_folder: Path) -> Path:
    return source_folder / RESULT_DIR_NAME
