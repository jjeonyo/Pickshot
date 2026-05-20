from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.core.analysis import analyze_images


def save_image(path: Path, color: tuple[int, int, int] = (120, 20, 30)) -> None:
    Image.new("RGB", (64, 64), color).save(path)


def test_analyze_images_skips_corrupt_files_without_aborting(tmp_path: Path) -> None:
    valid = tmp_path / "valid.jpg"
    corrupt = tmp_path / "corrupt.jpg"
    save_image(valid)
    corrupt.write_bytes(b"not an image")

    result = analyze_images(tmp_path)

    assert [photo.path for photo in result.photos] == [valid]
    assert len(result.groups) == 1
    assert len(result.skipped) == 1
    assert result.skipped[0].path == corrupt
    assert result.skipped[0].reason


def test_analyze_images_reports_skipped_when_no_valid_images_remain(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.jpg"
    corrupt.write_bytes(b"not an image")

    result = analyze_images(tmp_path)

    assert result.groups == []
    assert result.photos == []
    assert len(result.skipped) == 1
    assert result.skipped[0].path == corrupt
