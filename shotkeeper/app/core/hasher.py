from __future__ import annotations

from pathlib import Path

import imagehash
from PIL import Image, ImageOps

from app.models.photo import Photo


def compute_phash(path: str | Path, hash_size: int = 8) -> str:
    with Image.open(path) as image:
        normalized = ImageOps.exif_transpose(image).convert("RGB")
        return str(imagehash.phash(normalized, hash_size=hash_size))


def hash_distance(left: str, right: str) -> int:
    return imagehash.hex_to_hash(left) - imagehash.hex_to_hash(right)


def attach_hashes(photos: list[Photo], hash_size: int = 8) -> list[Photo]:
    for photo in photos:
        photo.phash = compute_phash(photo.path, hash_size=hash_size)
    return photos
