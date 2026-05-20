from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QProgressBar, QVBoxLayout, QWidget

from app.models.photo import Photo, PhotoGroup

CLASSIFICATION_LABELS = {
    "keep": "보관",
    "review": "검토",
    "trash_candidate": "제외 후보",
}


class ThumbnailLabel(QLabel):
    def __init__(self, size: int = 360) -> None:
        super().__init__("사진을 선택하세요")
        self.size = size
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(size, size)
        self.setStyleSheet("border: 1px solid #d8dde6; background: #f7f9fc; border-radius: 8px;")

    def show_image(self, path: Path | None) -> None:
        if path is None:
            self.setText("사진을 선택하세요")
            self.setPixmap(QPixmap())
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.setText(f"이미지를 불러올 수 없습니다\n{path.name}")
            self.setPixmap(QPixmap())
            return
        scaled = pixmap.scaled(self.size, self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)
        self.setText("")


class PhotoList(QListWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setIconSize(QSize(72, 72))
        self.setSpacing(6)

    def set_group(self, group: PhotoGroup | None) -> None:
        self.clear()
        if group is None:
            return
        sorted_photos = sorted(group.photos, key=lambda item: (not item.is_best, -item.metrics.overall, item.filename))
        for photo in sorted_photos:
            marker = "추천" if photo.is_best else "검토"
            label = CLASSIFICATION_LABELS[photo.classification]
            item = QListWidgetItem(
                f"{marker} · {photo.metrics.overall:.1f}점 · {label}\n{photo.filename}"
            )
            pixmap = QPixmap(str(photo.path))
            if not pixmap.isNull():
                item.setIcon(QIcon(pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            item.setData(Qt.UserRole, photo)
            item.setSizeHint(QSize(240, 82))
            self.addItem(item)


class GroupList(QListWidget):
    def set_groups(self, groups: list[PhotoGroup]) -> None:
        self.clear()
        for group in groups:
            best_score = group.best_photo.metrics.overall if group.best_photo else 0.0
            item = QListWidgetItem(f"그룹 {group.id} · {len(group.photos)}장 · 추천 {best_score:.1f}점")
            item.setData(Qt.UserRole, group)
            self.addItem(item)


class MetricsBarPanel(QWidget):
    """Bar-chart style metric view for the currently selected photo."""

    def __init__(self) -> None:
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel("품질 점수")
        self.title.setStyleSheet("font-weight: 700;")
        self.layout.addWidget(self.title)
        self.empty = QLabel("사진을 선택하면 주요 점수를 보여줍니다.")
        self.empty.setWordWrap(True)
        self.layout.addWidget(self.empty)

    def set_photo(self, photo: Photo | None) -> None:
        self._clear_rows()
        if photo is None:
            empty = QLabel("사진을 선택하면 주요 점수를 보여줍니다.")
            empty.setWordWrap(True)
            self.layout.addWidget(empty)
            return

        for label_text, score in photo.metrics.as_rows():
            label = QLabel(f"{label_text} {score:.1f}/10")
            label.setWordWrap(True)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(round(score * 10))
            bar.setFormat(f"{score:.1f}/10")
            bar.setStyleSheet(_bar_style(score, label_text == "종합"))
            self.layout.addWidget(label)
            self.layout.addWidget(bar)

    def _clear_rows(self) -> None:
        while self.layout.count() > 1:
            item = self.layout.takeAt(1)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


class EmptyState(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("Select a folder to analyze photos.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)


def _bar_style(score: float, is_overall: bool) -> str:
    if score >= 8.0:
        color = "#2e7d32"
    elif score >= 5.0:
        color = "#1976d2" if is_overall else "#f9a825"
    else:
        color = "#c62828"
    return (
        "QProgressBar { border: 1px solid #d8dde6; border-radius: 4px; background: #eef1f5; } "
        f"QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}"
    )
