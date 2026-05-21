from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core.apple_photos import ApplePhotoAlbum, ApplePhotoAsset, ApplePhotosPage  # noqa: E402
from app.ui.apple_photos_dialog import ApplePhotosPickerDialog  # noqa: E402


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_picker_pages_assets_and_returns_selected_ids(tmp_path: Path) -> None:
    app()
    calls = []

    def loader(offset: int, limit: int, album_identifier=None, search_text="") -> ApplePhotosPage:  # noqa: ANN001
        calls.append((offset, limit, album_identifier, search_text))
        assets = [ApplePhotoAsset(identifier=f"id-{offset}", filename=f"img-{offset}.jpg", width=100, height=80)]
        return ApplePhotosPage(assets=assets, total_count=2, offset=offset, limit=limit)

    def thumbnail_loader(identifier: str, destination: str | Path) -> Path:
        path = Path(destination) / f"{identifier}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"not-real-pixmap")
        return path

    dialog = ApplePhotosPickerDialog(
        page_size=1,
        loader=loader,
        album_loader=lambda: [ApplePhotoAlbum(identifier="", title="전체 사진", asset_count=2)],
        thumbnail_loader=thumbnail_loader,
        thumbnail_root=tmp_path,
    )
    dialog.load_next_page()
    dialog.list_widget.item(1).setSelected(True)

    assert calls == [(0, 1, None, ""), (1, 1, None, "")]
    assert dialog.list_widget.count() == 2
    assert dialog.selected_asset_ids() == ["id-1"]
    assert dialog.load_more_button.isEnabled() is False


def test_picker_applies_album_and_search_filters(tmp_path: Path) -> None:
    app()
    calls = []

    def loader(offset: int, limit: int, album_identifier=None, search_text="") -> ApplePhotosPage:  # noqa: ANN001
        calls.append((offset, album_identifier, search_text))
        return ApplePhotosPage(assets=[], total_count=0, offset=offset, limit=limit)

    dialog = ApplePhotosPickerDialog(
        page_size=10,
        loader=loader,
        album_loader=lambda: [
            ApplePhotoAlbum(identifier="", title="전체 사진", asset_count=10),
            ApplePhotoAlbum(identifier="album-1", title="여행", asset_count=3),
        ],
        thumbnail_loader=lambda identifier, destination: tmp_path / "missing.jpg",
        thumbnail_root=tmp_path,
    )
    dialog.album_combo.setCurrentIndex(1)
    dialog.search_input.setText("busan")
    dialog.reset_and_load()

    assert calls[-1] == (0, "album-1", "busan")
