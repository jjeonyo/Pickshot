from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter

from app.core.quality import attach_quality_scores, sharpness_score
from app.models.photo import Photo


def test_sharp_image_scores_higher_than_blurred_image(tmp_path: Path) -> None:
    sharp_path = tmp_path / "sharp.png"
    blur_path = tmp_path / "blur.png"

    image = np.zeros((128, 128), dtype=np.uint8)
    cv2.rectangle(image, (24, 24), (104, 104), 255, -1)
    cv2.line(image, (0, 0), (127, 127), 128, 2)
    Image.fromarray(image).save(sharp_path)
    Image.fromarray(image).filter(ImageFilter.GaussianBlur(radius=4)).save(blur_path)

    assert sharpness_score(sharp_path) > sharpness_score(blur_path)


def test_attach_quality_scores_adds_zero_to_ten_metrics(tmp_path: Path) -> None:
    sharp_path = tmp_path / "sharp.png"
    blur_path = tmp_path / "blur.png"

    image = np.zeros((128, 128), dtype=np.uint8)
    cv2.rectangle(image, (24, 24), (104, 104), 255, -1)
    Image.fromarray(image).save(sharp_path)
    Image.fromarray(image).filter(ImageFilter.GaussianBlur(radius=4)).save(blur_path)

    photos = [Photo(path=sharp_path), Photo(path=blur_path)]
    attach_quality_scores(photos)

    for photo in photos:
        assert 0.0 <= photo.metrics.overall <= 10.0
        assert 0.0 <= photo.metrics.sharpness <= 10.0
        assert 0.0 <= photo.metrics.focus <= 10.0
        assert 0.0 <= photo.metrics.exposure <= 10.0
        assert 0.0 <= photo.metrics.face <= 10.0
        assert 0.0 <= photo.metrics.expression <= 10.0
        assert 0.0 <= photo.metrics.eyes_open <= 10.0
        assert 0.0 <= photo.metrics.composition <= 10.0
        assert 0.0 <= photo.metrics.color <= 10.0
    assert photos[0].metrics.sharpness > photos[1].metrics.sharpness
