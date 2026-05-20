from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.models.photo import Photo, QualityMetrics

_FACE_CASCADE = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"))
_EYE_CASCADE = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / "haarcascade_eye.xml"))
_SMILE_CASCADE = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / "haarcascade_smile.xml"))

_FACE_NEUTRAL_SCORE = 5.0


def _read_image(path: str | Path, flags: int) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, flags)
    if image is None:
        raise ValueError(f"Unable to read image: {path}")
    return image


def _read_grayscale(path: str | Path) -> np.ndarray:
    return _read_image(path, cv2.IMREAD_GRAYSCALE)


def _read_color(path: str | Path) -> np.ndarray:
    return _read_image(path, cv2.IMREAD_COLOR)


def sharpness_score(path: str | Path) -> float:
    image = _read_grayscale(path)
    return float(cv2.Laplacian(image, cv2.CV_64F).var())


def focus_score(path: str | Path) -> float:
    image = _read_grayscale(path)
    height, width = image.shape[:2]
    y1, y2 = height // 4, height - height // 4
    x1, x2 = width // 4, width - width // 4
    center = image[y1:y2, x1:x2]
    if center.size == 0:
        center = image
    return float(cv2.Laplacian(center, cv2.CV_64F).var())


def exposure_score(path: str | Path) -> float:
    image = _read_grayscale(path)
    mean_brightness = float(np.mean(image))
    # 127.5 is treated as balanced exposure. Score drops toward 0 near black/white extremes.
    return max(0.0, 1.0 - abs(mean_brightness - 127.5) / 127.5)


def _detect_faces(gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    faces = _FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(32, 32))
    return [tuple(map(int, face)) for face in faces]


def _largest_face(faces: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int] | None:
    if not faces:
        return None
    return max(faces, key=lambda face: face[2] * face[3])


def face_score_from_detection(gray: np.ndarray, faces: list[tuple[int, int, int, int]]) -> float:
    face = _largest_face(faces)
    if face is None:
        return _FACE_NEUTRAL_SCORE

    height, width = gray.shape[:2]
    x, y, w, h = face
    face_area_ratio = (w * h) / float(width * height)
    size_score = max(0.0, min(10.0, face_area_ratio / 0.18 * 10.0))

    face_center_x = x + (w / 2)
    face_center_y = y + (h / 2)
    center_distance = ((face_center_x - width / 2) / (width / 2)) ** 2 + ((face_center_y - height / 2) / (height / 2)) ** 2
    center_score = max(0.0, 10.0 - center_distance * 5.0)
    return round((size_score * 0.45) + (center_score * 0.55), 1)


def eyes_open_score_from_detection(gray: np.ndarray, faces: list[tuple[int, int, int, int]]) -> float:
    face = _largest_face(faces)
    if face is None:
        return _FACE_NEUTRAL_SCORE

    x, y, w, h = face
    upper_face = gray[y : y + max(1, int(h * 0.62)), x : x + w]
    eyes = _EYE_CASCADE.detectMultiScale(upper_face, scaleFactor=1.1, minNeighbors=4, minSize=(10, 10))
    eye_count = len(eyes)
    if eye_count >= 2:
        return 10.0
    if eye_count == 1:
        return 6.0
    return 2.0


def expression_score_from_detection(gray: np.ndarray, faces: list[tuple[int, int, int, int]]) -> float:
    face = _largest_face(faces)
    if face is None:
        return _FACE_NEUTRAL_SCORE

    x, y, w, h = face
    lower_face = gray[y + h // 2 : y + h, x : x + w]
    smiles = _SMILE_CASCADE.detectMultiScale(lower_face, scaleFactor=1.7, minNeighbors=18, minSize=(15, 8))
    if len(smiles) > 0:
        return 9.0
    return 6.0


def composition_score_from_detection(gray: np.ndarray, faces: list[tuple[int, int, int, int]]) -> float:
    height, width = gray.shape[:2]
    face = _largest_face(faces)
    if face is not None:
        x, y, w, h = face
        cx = x + w / 2
        cy = y + h / 2
        targets = [(width / 3, height / 3), (width * 2 / 3, height / 3), (width / 2, height / 2)]
        normalized_dist = min(
            (((cx - tx) / width) ** 2 + ((cy - ty) / height) ** 2) ** 0.5 for tx, ty in targets
        )
        return round(max(0.0, 10.0 - normalized_dist * 18.0), 1)

    edges = cv2.Canny(gray, 80, 160)
    thirds_x = [width // 3, (width * 2) // 3]
    thirds_y = [height // 3, (height * 2) // 3]
    band = max(2, min(width, height) // 40)
    thirds_energy = 0
    for x in thirds_x:
        thirds_energy += int(edges[:, max(0, x - band) : min(width, x + band)].sum())
    for y in thirds_y:
        thirds_energy += int(edges[max(0, y - band) : min(height, y + band), :].sum())
    total_energy = int(edges.sum())
    if total_energy <= 0:
        return 5.0
    return round(max(0.0, min(10.0, 4.0 + (thirds_energy / total_energy) * 24.0)), 1)


def color_score(path: str | Path) -> float:
    image = _read_color(path)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = float(np.mean(hsv[:, :, 1])) / 255.0
    value = hsv[:, :, 2].astype(np.float32)
    contrast = float(np.std(value)) / 64.0
    saturation_score = max(0.0, min(10.0, saturation / 0.45 * 10.0))
    contrast_score = max(0.0, min(10.0, contrast * 10.0))
    return round((saturation_score * 0.55) + (contrast_score * 0.45), 1)


def _normalize_to_ten(values: list[float]) -> list[float]:
    if not values:
        return []
    max_value = max(values)
    if max_value <= 0:
        return [0.0 for _ in values]
    return [round(max(0.0, min(10.0, value / max_value * 10.0)), 1) for value in values]


def _overall_score(metrics: QualityMetrics) -> float:
    return round(
        (metrics.sharpness * 0.22)
        + (metrics.focus * 0.18)
        + (metrics.exposure * 0.12)
        + (metrics.face * 0.12)
        + (metrics.expression * 0.10)
        + (metrics.eyes_open * 0.10)
        + (metrics.composition * 0.08)
        + (metrics.color * 0.08),
        1,
    )


def attach_quality_scores(photos: list[Photo]) -> list[Photo]:
    raw_sharpness: list[float] = []
    raw_focus: list[float] = []
    raw_exposure: list[float] = []
    raw_face: list[float] = []
    raw_expression: list[float] = []
    raw_eyes_open: list[float] = []
    raw_composition: list[float] = []
    raw_color: list[float] = []

    for photo in photos:
        gray = _read_grayscale(photo.path)
        faces = _detect_faces(gray)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        focus = focus_score(photo.path)
        exposure = exposure_score(photo.path)
        face = face_score_from_detection(gray, faces)
        expression = expression_score_from_detection(gray, faces)
        eyes_open = eyes_open_score_from_detection(gray, faces)
        composition = composition_score_from_detection(gray, faces)
        color = color_score(photo.path)

        photo.sharpness = sharpness
        raw_sharpness.append(sharpness)
        raw_focus.append(focus)
        raw_exposure.append(exposure)
        raw_face.append(face)
        raw_expression.append(expression)
        raw_eyes_open.append(eyes_open)
        raw_composition.append(composition)
        raw_color.append(color)

    sharpness_scores = _normalize_to_ten(raw_sharpness)
    focus_scores = _normalize_to_ten(raw_focus)
    exposure_scores = [round(score * 10.0, 1) for score in raw_exposure]

    for photo, sharpness, focus, exposure, face, expression, eyes_open, composition, color in zip(
        photos,
        sharpness_scores,
        focus_scores,
        exposure_scores,
        raw_face,
        raw_expression,
        raw_eyes_open,
        raw_composition,
        raw_color,
        strict=True,
    ):
        metrics = QualityMetrics(
            sharpness=sharpness,
            focus=focus,
            exposure=exposure,
            face=face,
            expression=expression,
            eyes_open=eyes_open,
            composition=composition,
            color=color,
        )
        metrics.overall = _overall_score(metrics)
        photo.metrics = metrics
    return photos
