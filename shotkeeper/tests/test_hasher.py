from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.core.hasher import compute_phash, hash_distance


def save_solid(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (64, 64), color).save(path)


def test_compute_phash_is_stable_for_same_image(tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    save_solid(image, (120, 20, 30))

    assert compute_phash(image) == compute_phash(image)


def test_hash_distance_zero_for_identical_hash(tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    save_solid(image, (10, 20, 30))
    phash = compute_phash(image)

    assert hash_distance(phash, phash) == 0
