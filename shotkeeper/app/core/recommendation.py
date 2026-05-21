from __future__ import annotations

from dataclasses import dataclass

from app.models.photo import Photo, PhotoGroup


METRIC_PRIORITY = ("sharpness", "focus", "exposure", "face", "expression", "eyes_open", "composition", "color")
METRIC_LABELS = {
    "sharpness": "선명도",
    "focus": "초점",
    "exposure": "노출",
    "face": "얼굴",
    "expression": "표정",
    "eyes_open": "눈뜸",
    "composition": "구도",
    "color": "색감",
}


@dataclass(frozen=True, slots=True)
class MetricComparison:
    key: str
    label: str
    selected_score: float
    best_score: float
    delta: float


def overall_rank(group: PhotoGroup, photo: Photo) -> int | None:
    if photo not in group.photos:
        return None
    ordered = sorted(group.photos, key=lambda item: item.metrics.overall, reverse=True)
    return ordered.index(photo) + 1


def best_photo_explanation(group: PhotoGroup, photo: Photo) -> str:
    """Return a one-line UI explanation for why this photo is or is not best."""
    best = group.best_photo
    if best is None:
        return "아직 베스트컷을 판단할 사진이 없습니다."

    rank = overall_rank(group, photo)
    if photo is best:
        top_metrics = sorted(
            photo.metrics.as_rows()[1:],
            key=lambda row: row[1],
            reverse=True,
        )[:3]
        summary = ", ".join(f"{name} {score:.1f}" for name, score in top_metrics)
        return f"종합 {photo.metrics.overall:.1f}/10로 그룹 {rank}위이며 {summary} 점수가 좋아 베스트샷입니다."

    return (
        f"베스트샷은 {best.filename}이며 종합 {best.metrics.overall:.1f}/10로, "
        f"선택 사진({photo.metrics.overall:.1f}/10, 그룹 {rank}위)보다 품질 점수가 높습니다."
    )


def recommendation_status(group: PhotoGroup | None, photo: Photo | None) -> tuple[str, str]:
    """Return a short product-facing recommendation summary and reason."""
    if group is None or photo is None:
        return ("사진을 선택하세요", "그룹과 사진을 선택하면 추천 여부와 이유를 보여줍니다.")

    best = group.best_photo
    if best is None:
        return ("추천 판단 대기", "이 그룹에는 비교할 수 있는 사진이 없습니다.")

    rank = overall_rank(group, photo)
    if photo is best:
        return (
            "현재 사진: 보관 추천",
            f"그룹 {rank}위 · 종합 {photo.metrics.overall:.1f}/10점으로 이 그룹의 베스트샷입니다.",
        )

    gaps = []
    for metric in METRIC_PRIORITY:
        selected_score = getattr(photo.metrics, metric)
        best_score = getattr(best.metrics, metric)
        diff = round(best_score - selected_score, 1)
        if diff > 0:
            gaps.append((METRIC_LABELS[metric], diff))
    strongest_gaps = ", ".join(f"{label} -{diff:.1f}" for label, diff in gaps[:3]) or "세부 지표 차이는 작음"
    return (
        "현재 사진: 검토 권장",
        (
            f"추천 사진은 {best.filename} · 종합 {best.metrics.overall:.1f}/10점입니다. "
            f"현재 사진은 {photo.metrics.overall:.1f}/10점, 그룹 {rank}위이며 {strongest_gaps} 차이가 납니다."
        ),
    )


def compare_with_best(group: PhotoGroup | None, photo: Photo | None) -> list[MetricComparison]:
    """Compare the selected photo against the group's best photo by metric."""
    if group is None or photo is None or group.best_photo is None:
        return []

    best = group.best_photo
    return [
        MetricComparison(
            key=metric,
            label=METRIC_LABELS[metric],
            selected_score=getattr(photo.metrics, metric),
            best_score=getattr(best.metrics, metric),
            delta=round(getattr(photo.metrics, metric) - getattr(best.metrics, metric), 1),
        )
        for metric in METRIC_PRIORITY
    ]
