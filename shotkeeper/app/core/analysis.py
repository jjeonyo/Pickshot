from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.grouping import group_similar_photos
from app.core.hasher import attach_hashes
from app.core.quality import attach_quality_scores, sharpness_score
from app.core.scanner import scan_images
from app.models.photo import Photo, PhotoGroup


@dataclass(frozen=True, slots=True)
class SkippedPhoto:
    """A scanned file that could not be analyzed safely."""

    path: Path
    reason: str


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    groups: list[PhotoGroup] = field(default_factory=list)
    skipped: list[SkippedPhoto] = field(default_factory=list)

    @property
    def photos(self) -> list[Photo]:
        return [photo for group in self.groups for photo in group.photos]


def analyze_images(folder: str | Path) -> AnalysisResult:
    """Scan, hash, score, and group analyzable images from a folder.

    Files that match a supported extension but fail decoding are reported as
    skipped instead of aborting the entire local analysis run.
    """

    scanned = scan_images(folder)
    analyzable: list[Photo] = []
    skipped: list[SkippedPhoto] = []

    for photo in scanned:
        try:
            attach_hashes([photo])
        except Exception as exc:  # Decode boundary: keep the rest of the folder usable.
            skipped.append(SkippedPhoto(path=photo.path, reason=str(exc)))
        else:
            analyzable.append(photo)

    quality_ready: list[Photo] = []
    for photo in analyzable:
        try:
            sharpness_score(photo.path)
        except Exception as exc:  # OpenCV decode boundary: skip only the failing file.
            skipped.append(SkippedPhoto(path=photo.path, reason=str(exc)))
        else:
            quality_ready.append(photo)

    if not quality_ready:
        return AnalysisResult(skipped=skipped)

    attach_quality_scores(quality_ready)
    return AnalysisResult(groups=group_similar_photos(quality_ready), skipped=skipped)
