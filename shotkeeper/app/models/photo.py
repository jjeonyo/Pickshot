from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Classification = Literal["keep", "review", "trash_candidate"]


@dataclass(slots=True)
class QualityMetrics:
    sharpness: float = 0.0
    focus: float = 0.0
    exposure: float = 0.0
    face: float = 0.0
    expression: float = 0.0
    eyes_open: float = 0.0
    composition: float = 0.0
    color: float = 0.0
    overall: float = 0.0

    def as_rows(self) -> list[tuple[str, float]]:
        return [
            ("종합", self.overall),
            ("선명도", self.sharpness),
            ("초점", self.focus),
            ("노출", self.exposure),
            ("얼굴", self.face),
            ("표정", self.expression),
            ("눈뜸", self.eyes_open),
            ("구도", self.composition),
            ("색감", self.color),
        ]


@dataclass(slots=True)
class Photo:
    path: Path
    phash: str | None = None
    sharpness: float = 0.0
    metrics: QualityMetrics = field(default_factory=QualityMetrics)
    classification: Classification = "review"
    is_best: bool = False

    @property
    def filename(self) -> str:
        return self.path.name


@dataclass(slots=True)
class PhotoGroup:
    id: int
    photos: list[Photo] = field(default_factory=list)

    @property
    def best_photo(self) -> Photo | None:
        best = [photo for photo in self.photos if photo.is_best]
        if best:
            return best[0]
        if not self.photos:
            return None
        return max(self.photos, key=lambda photo: photo.metrics.overall)
