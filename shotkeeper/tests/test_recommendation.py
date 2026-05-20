from __future__ import annotations

from pathlib import Path

from app.core.grouping import mark_best_photos
from app.core.recommendation import best_photo_explanation, overall_rank, recommendation_status
from app.models.photo import Photo, PhotoGroup, QualityMetrics


def make_group() -> PhotoGroup:
    group = PhotoGroup(
        id=1,
        photos=[
            Photo(path=Path("soft.jpg"), metrics=QualityMetrics(sharpness=3.0, focus=3.0, exposure=7.0, face=5.0, expression=5.0, eyes_open=5.0, composition=4.0, color=4.0, overall=3.8)),
            Photo(path=Path("sharp.jpg"), metrics=QualityMetrics(sharpness=9.0, focus=8.0, exposure=8.0, face=8.0, expression=9.0, eyes_open=10.0, composition=8.0, color=7.0, overall=8.5)),
        ],
    )
    mark_best_photos([group])
    return group


def test_overall_rank() -> None:
    group = make_group()

    assert overall_rank(group, group.photos[1]) == 1
    assert overall_rank(group, group.photos[0]) == 2


def test_best_photo_explanation_is_one_line_and_mentions_metrics() -> None:
    group = make_group()

    explanation = best_photo_explanation(group, group.photos[1])

    assert "\n" not in explanation
    assert "종합 8.5/10" in explanation
    assert "베스트샷" in explanation
    assert "선명도" in explanation
    assert any(name in explanation for name in ["초점", "노출", "얼굴", "표정", "눈뜸", "구도", "색감"])


def test_non_best_explanation_mentions_best_filename() -> None:
    group = make_group()

    explanation = best_photo_explanation(group, group.photos[0])

    assert "sharp.jpg" in explanation
    assert "3.8/10" in explanation


def test_recommendation_status_prioritizes_user_action() -> None:
    group = make_group()

    title, reason = recommendation_status(group, group.photos[0])

    assert title == "현재 사진: 검토 권장"
    assert "추천 사진은 sharp.jpg" in reason
    assert "선명도" in reason


def test_recommendation_status_marks_best_as_keep() -> None:
    group = make_group()

    title, reason = recommendation_status(group, group.photos[1])

    assert title == "현재 사진: 보관 추천"
    assert "베스트샷" in reason
