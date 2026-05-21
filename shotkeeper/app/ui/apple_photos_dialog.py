from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.core.apple_photos import (
    ApplePhotoAlbum,
    ApplePhotoAsset,
    ApplePhotosIntegrationError,
    ApplePhotosPage,
    cache_asset_thumbnail,
    default_apple_photos_cache_root,
    list_photo_albums,
    list_photo_assets,
)

AssetPageLoader = Callable[..., ApplePhotosPage]
AlbumLoader = Callable[[], list[ApplePhotoAlbum]]
ThumbnailLoader = Callable[[str, str | Path], Path]


class ApplePhotosPickerDialog(QDialog):
    """Apple Photos browser that analyzes only explicit user selections."""

    def __init__(
        self,
        *,
        page_size: int = 80,
        loader: AssetPageLoader = list_photo_assets,
        album_loader: AlbumLoader = list_photo_albums,
        thumbnail_loader: ThumbnailLoader = cache_asset_thumbnail,
        thumbnail_root: str | Path | None = None,
        parent=None,  # noqa: ANN001
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Apple 사진첩에서 분석할 사진 선택")
        self.resize(980, 720)
        self.page_size = page_size
        self.loader = loader
        self.album_loader = album_loader
        self.thumbnail_loader = thumbnail_loader
        self.thumbnail_root = Path(thumbnail_root) if thumbnail_root is not None else default_apple_photos_cache_root() / "thumbnails"
        self.next_offset = 0
        self.total_count = 0
        self.assets_by_id: dict[str, ApplePhotoAsset] = {}

        self.description = QLabel(
            "사진첩 전체를 분석하지 않습니다. 앨범/검색으로 범위를 좁히고 정리할 사진만 선택하세요."
        )
        self.description.setWordWrap(True)
        self.count_label = QLabel("사진첩을 불러오지 않았습니다.")
        self.album_combo = QComboBox()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("파일명, 날짜, 식별자로 검색")
        self.search_button = QPushButton("검색")
        self.clear_button = QPushButton("초기화")

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setMovement(QListWidget.Movement.Static)
        self.list_widget.setIconSize(QSize(132, 132))
        self.list_widget.setGridSize(QSize(180, 210))
        self.list_widget.setSpacing(10)
        self.list_widget.setWordWrap(True)

        self.load_more_button = QPushButton("사진 더 보기")
        self.analyze_button = QPushButton("선택한 사진만 분석")
        self.cancel_button = QPushButton("취소")

        layout = QVBoxLayout(self)
        layout.addWidget(self.description)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("앨범"))
        filter_row.addWidget(self.album_combo, 2)
        filter_row.addWidget(self.search_input, 3)
        filter_row.addWidget(self.search_button)
        filter_row.addWidget(self.clear_button)
        layout.addLayout(filter_row)
        layout.addWidget(self.count_label)
        layout.addWidget(self.list_widget)

        button_row = QHBoxLayout()
        button_row.addWidget(self.load_more_button)
        button_row.addStretch()
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.analyze_button)
        layout.addLayout(button_row)

        self.load_more_button.clicked.connect(self.load_next_page)
        self.cancel_button.clicked.connect(self.reject)
        self.analyze_button.clicked.connect(self.accept_selected)
        self.search_button.clicked.connect(self.reset_and_load)
        self.clear_button.clicked.connect(self.clear_filters)
        self.search_input.returnPressed.connect(self.reset_and_load)
        self.album_combo.currentIndexChanged.connect(self.reset_and_load)
        self.list_widget.itemSelectionChanged.connect(self._refresh_count_label)

        self._load_albums()
        self.load_next_page()

    def selected_asset_ids(self) -> list[str]:
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.list_widget.selectedItems()]

    def reset_and_load(self) -> None:
        self.next_offset = 0
        self.total_count = 0
        self.assets_by_id = {}
        self.list_widget.clear()
        self.load_next_page()

    def clear_filters(self) -> None:
        self.search_input.clear()
        if self.album_combo.count():
            self.album_combo.setCurrentIndex(0)
        else:
            self.reset_and_load()

    def load_next_page(self) -> None:
        try:
            page = self.loader(
                offset=self.next_offset,
                limit=self.page_size,
                album_identifier=self.current_album_identifier(),
                search_text=self.search_input.text(),
            )
        except ApplePhotosIntegrationError as exc:
            QMessageBox.warning(self, "Apple 사진첩 연동 실패", str(exc))
            self.load_more_button.setEnabled(False)
            return

        self.total_count = page.total_count
        self.next_offset = page.next_offset
        self._append_assets(page.assets)
        self._refresh_count_label()
        self.load_more_button.setEnabled(page.has_more)
        if not page.assets and self.list_widget.count() == 0:
            self.count_label.setText("현재 필터에서 표시할 이미지를 찾지 못했습니다.")

    def current_album_identifier(self) -> str | None:
        value = self.album_combo.currentData(Qt.ItemDataRole.UserRole)
        return value or None

    def accept_selected(self) -> None:
        if not self.selected_asset_ids():
            QMessageBox.information(self, "ShotKeeper", "분석할 사진을 먼저 선택하세요.")
            return
        self.accept()

    def _load_albums(self) -> None:
        self.album_combo.blockSignals(True)
        self.album_combo.clear()
        try:
            albums = self.album_loader()
        except ApplePhotosIntegrationError as exc:
            QMessageBox.warning(self, "Apple 사진첩 연동 실패", str(exc))
            albums = [ApplePhotoAlbum(identifier="", title="전체 사진", asset_count=0)]
        for album in albums:
            self.album_combo.addItem(f"{album.title} ({album.asset_count})", album.identifier)
        self.album_combo.blockSignals(False)

    def _append_assets(self, assets: list[ApplePhotoAsset]) -> None:
        for asset in assets:
            if asset.identifier in self.assets_by_id:
                continue
            self.assets_by_id[asset.identifier] = asset
            created = asset.created_at or "날짜 없음"
            item = QListWidgetItem(f"{asset.display_title}\n{created}")
            item.setToolTip(f"{asset.filename}\n{asset.width}×{asset.height}\n{asset.identifier}")
            item.setData(Qt.ItemDataRole.UserRole, asset.identifier)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            item.setSizeHint(QSize(174, 204))
            thumb_path = self._thumbnail_path(asset.identifier)
            if thumb_path is not None:
                pixmap = QPixmap(str(thumb_path))
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap))
            self.list_widget.addItem(item)

    def _thumbnail_path(self, identifier: str) -> Path | None:
        try:
            return self.thumbnail_loader(identifier, self.thumbnail_root)
        except ApplePhotosIntegrationError:
            return None

    def _refresh_count_label(self) -> None:
        selected_count = len(self.selected_asset_ids())
        self.count_label.setText(
            f"표시 중 {self.list_widget.count()}장 / 현재 범위 {self.total_count}장 · "
            f"선택 {selected_count}장 · 선택한 사진만 캐시하고 분석합니다."
        )
