from __future__ import annotations

from app.core.hasher import hash_distance
from app.models.photo import Photo, PhotoGroup


def group_similar_photos(photos: list[Photo], max_distance: int = 10) -> list[PhotoGroup]:
    """Greedily group photos whose pHash is close to at least one group member."""
    groups: list[PhotoGroup] = []

    for photo in photos:
        if not photo.phash:
            raise ValueError(f"Photo has no phash: {photo.path}")

        matched_group: PhotoGroup | None = None
        best_distance: int | None = None

        for group in groups:
            distances = [hash_distance(photo.phash, member.phash or "") for member in group.photos]
            group_distance = min(distances)
            if group_distance <= max_distance and (best_distance is None or group_distance < best_distance):
                matched_group = group
                best_distance = group_distance

        if matched_group is None:
            groups.append(PhotoGroup(id=len(groups) + 1, photos=[photo]))
        else:
            matched_group.photos.append(photo)

    mark_best_photos(groups)
    return groups


def mark_best_photos(groups: list[PhotoGroup]) -> list[PhotoGroup]:
    for group in groups:
        if not group.photos:
            continue
        best = max(group.photos, key=lambda photo: photo.metrics.overall)
        for photo in group.photos:
            photo.is_best = photo is best
            if photo.is_best:
                photo.classification = "keep"
            elif photo.classification == "keep":
                photo.classification = "review"
    return groups
