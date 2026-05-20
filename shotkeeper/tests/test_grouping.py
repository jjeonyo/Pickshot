from __future__ import annotations

from pathlib import Path

from app.core.grouping import group_similar_photos
from app.models.photo import Photo, QualityMetrics


def photo(name: str, phash: str, overall: float) -> Photo:
    return Photo(path=Path(name), phash=phash, metrics=QualityMetrics(overall=overall))


def test_groups_similar_hashes_and_marks_highest_overall_best() -> None:
    photos = [
        photo("a.jpg", "0000000000000000", 3.0),
        photo("b.jpg", "0000000000000001", 8.0),
        photo("c.jpg", "ffffffffffffffff", 5.0),
    ]

    groups = group_similar_photos(photos, max_distance=2)

    assert [len(group.photos) for group in groups] == [2, 1]
    assert groups[0].best_photo is photos[1]
    assert photos[1].classification == "keep"
    assert photos[0].classification == "review"


def test_rejects_photos_without_hash() -> None:
    photos = [Photo(path=Path("missing.jpg"))]

    try:
        group_similar_photos(photos)
    except ValueError as exc:
        assert "no phash" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
