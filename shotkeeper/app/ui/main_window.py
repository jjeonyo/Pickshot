from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.core.analysis import analyze_images
from app.core.apple_photos import ApplePhotosIntegrationError, cache_selected_photo_assets, next_cache_destination
from app.core.file_ops import export_photos, set_classification
from app.core.recommendation import best_photo_explanation, compare_with_best, recommendation_status
from app.models.photo import Classification, Photo, PhotoGroup
from app.ui.apple_photos_dialog import ApplePhotosPickerDialog
from app.ui.components import (
    CLASSIFICATION_LABELS,
    BestComparisonPanel,
    GroupList,
    MetricsBarPanel,
    PhotoList,
    ThumbnailLabel,
)


class ApplePhotosCacheWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, destination: Path, asset_ids: list[str]) -> None:
        super().__init__()
        self.destination = destination
        self.asset_ids = asset_ids

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(cache_selected_photo_assets(self.asset_ids, self.destination))
        except ApplePhotosIntegrationError as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ShotKeeper")
        self.resize(1180, 760)

        self.source_folder: Path | None = None
        self.groups: list[PhotoGroup] = []
        self.current_group: PhotoGroup | None = None
        self.current_photo: Photo | None = None
        self.apple_photos_thread: QThread | None = None
        self.apple_photos_worker: ApplePhotosCacheWorker | None = None

        self.group_list = GroupList()
        self.photo_list = PhotoList()
        self.thumbnail = ThumbnailLabel(size=380)
        self.summary_label = QLabel("사진을 선택하면 추천 판단을 보여줍니다.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "font-size: 18px; font-weight: 700; padding: 10px; "
            "background: #eef7ee; border: 1px solid #c8e6c9; border-radius: 8px;"
        )
        self.detail_label = QLabel("그룹과 사진을 선택하세요.")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("padding: 8px; color: #374151;")
        self.comparison_panel = BestComparisonPanel()
        self.metrics_panel = MetricsBarPanel()
        self.explanation_label = QLabel("추천 사진과 현재 사진의 차이를 여기에서 설명합니다.")
        self.explanation_label.setWordWrap(True)
        self.explanation_label.setStyleSheet("padding: 10px; background: #f7f9fc; border: 1px solid #d8dde6;")
        self.advanced_label = QLabel("")
        self.advanced_label.setWordWrap(True)
        self.advanced_label.setStyleSheet("padding: 8px; color: #6b7280; font-size: 12px;")
        self.advanced_label.setVisible(False)
        self.advanced_toggle = QPushButton("고급 정보 보기")
        self.advanced_toggle.setCheckable(True)

        self.keep_radio = QRadioButton(CLASSIFICATION_LABELS["keep"])
        self.review_radio = QRadioButton(CLASSIFICATION_LABELS["review"])
        self.trash_radio = QRadioButton(CLASSIFICATION_LABELS["trash_candidate"])
        self.classification_group = QButtonGroup(self)
        for button in (self.keep_radio, self.review_radio, self.trash_radio):
            self.classification_group.addButton(button)
        self.review_radio.setChecked(True)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        toolbar = QToolBar("주요 작업")
        self.addToolBar(toolbar)

        select_button = QPushButton("폴더 선택")
        apple_photos_button = QPushButton("Apple 사진첩 열기")
        analyze_button = QPushButton("분석")
        copy_button = QPushButton("결과 복사")
        move_button = QPushButton("결과 폴더로 이동")
        toolbar.addWidget(select_button)
        toolbar.addWidget(apple_photos_button)
        toolbar.addWidget(analyze_button)
        toolbar.addSeparator()
        toolbar.addWidget(copy_button)
        toolbar.addWidget(move_button)

        self.select_button = select_button
        self.apple_photos_button = apple_photos_button
        self.analyze_button = analyze_button
        self.copy_button = copy_button
        self.move_button = move_button

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.group_list)
        splitter.addWidget(self.photo_list)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 16, 20, 16)
        right_layout.setSpacing(12)
        right_layout.addWidget(self.summary_label)
        right_layout.addWidget(self.thumbnail)
        right_layout.addWidget(self.detail_label)
        right_layout.addWidget(self.comparison_panel)
        metrics_scroll = QScrollArea()
        metrics_scroll.setWidgetResizable(True)
        metrics_scroll.setMinimumHeight(210)
        metrics_scroll.setWidget(self.metrics_panel)
        right_layout.addWidget(metrics_scroll)
        right_layout.addWidget(self.explanation_label)
        right_layout.addWidget(self.advanced_toggle)
        right_layout.addWidget(self.advanced_label)

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.keep_radio)
        radio_layout.addWidget(self.review_radio)
        radio_layout.addWidget(self.trash_radio)
        classification_panel = QFrame()
        classification_layout = QVBoxLayout(classification_panel)
        classification_layout.setContentsMargins(10, 10, 10, 10)
        classification_panel.setStyleSheet("QFrame { border: 1px solid #d8dde6; border-radius: 8px; }")
        classification_layout.addWidget(QLabel("선택 사진 분류"))
        classification_layout.addLayout(radio_layout)
        right_layout.addWidget(classification_panel)

        apply_button = QPushButton("선택 사진 분류 적용")
        apply_group_button = QPushButton("추천 사진만 보관, 나머지는 제외 후보")
        right_layout.addWidget(apply_button)
        right_layout.addWidget(apply_group_button)
        self.apply_button = apply_button
        self.apply_group_button = apply_group_button

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 5)
        self.setCentralWidget(splitter)
        self.setStatusBar(QStatusBar())

    def _connect_signals(self) -> None:
        self.select_button.clicked.connect(self.select_folder)
        self.apple_photos_button.clicked.connect(self.open_apple_photos_picker)
        self.analyze_button.clicked.connect(self.analyze_folder)
        self.copy_button.clicked.connect(lambda: self.export_results("copy"))
        self.move_button.clicked.connect(lambda: self.export_results("move"))
        self.apply_button.clicked.connect(self.apply_classification)
        self.apply_group_button.clicked.connect(self.classify_group_auto)
        self.advanced_toggle.toggled.connect(self.toggle_advanced_info)
        self.group_list.currentItemChanged.connect(self.on_group_selected)
        self.photo_list.currentItemChanged.connect(self.on_photo_selected)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "사진 폴더 선택")
        if folder:
            self.source_folder = Path(folder)
            self.statusBar().showMessage(f"선택한 폴더: {self.source_folder}")

    def open_apple_photos_picker(self) -> None:
        dialog = ApplePhotosPickerDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.analyze_selected_apple_photos(dialog.selected_asset_ids())

    def analyze_selected_apple_photos(self, asset_ids: list[str]) -> None:
        destination = next_cache_destination()
        self.apple_photos_button.setEnabled(False)
        self.statusBar().showMessage(f"선택한 Apple 사진 {len(asset_ids)}장을 분석 캐시로 준비하는 중...")

        thread = QThread(self)
        worker = ApplePhotosCacheWorker(destination, asset_ids)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self.on_apple_photos_selection_cached)
        worker.failed.connect(self.on_apple_photos_library_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_apple_photos_worker)
        self.apple_photos_thread = thread
        self.apple_photos_worker = worker
        thread.start()

    @Slot(object)
    def on_apple_photos_selection_cached(self, result) -> None:  # noqa: ANN001 - Qt signal payload
        self.source_folder = result.destination
        self.apple_photos_button.setEnabled(True)
        self.statusBar().showMessage(
            f"선택한 Apple 사진 {result.exported_count}장을 캐시했습니다. 분석을 시작합니다..."
        )
        self.analyze_folder()

    @Slot(str)
    def on_apple_photos_library_failed(self, message: str) -> None:
        self.apple_photos_button.setEnabled(True)
        QMessageBox.warning(self, "Apple 사진첩 연동 실패", message)
        self.statusBar().showMessage("Apple 사진첩 연동 실패")

    def _clear_apple_photos_worker(self) -> None:
        self.apple_photos_thread = None
        self.apple_photos_worker = None

    def analyze_folder(self) -> None:
        if self.source_folder is None:
            self.select_folder()
            if self.source_folder is None:
                return
        try:
            self.statusBar().showMessage("사진을 스캔하고 분석하는 중...")
            result = analyze_images(self.source_folder)
            self.groups = result.groups
            self.group_list.set_groups(self.groups)
            if self.groups:
                self.group_list.setCurrentRow(0)
            if not self.groups:
                message = "분석 가능한 지원 이미지가 없습니다."
                if result.skipped:
                    message += f" 읽을 수 없는 파일 {len(result.skipped)}개는 건너뛰었습니다."
                QMessageBox.information(self, "ShotKeeper", message)
                self.statusBar().showMessage(message)
                return
            analyzed_count = sum(len(group.photos) for group in self.groups)
            skipped_suffix = f" · 읽을 수 없는 파일 {len(result.skipped)}개 건너뜀" if result.skipped else ""
            self.statusBar().showMessage(
                f"{analyzed_count}장 분석 완료 · {len(self.groups)}개 그룹{skipped_suffix}"
            )
        except Exception as exc:  # UI boundary: show recoverable error.
            QMessageBox.critical(self, "분석 실패", str(exc))
            self.statusBar().showMessage("분석 실패")

    def on_group_selected(self, current, _previous) -> None:  # noqa: ANN001 - Qt callback
        group = current.data(Qt.UserRole) if current else None
        self.current_group = group
        self.photo_list.set_group(group)
        if group and group.photos:
            self.photo_list.setCurrentRow(0)

    def on_photo_selected(self, current, _previous) -> None:  # noqa: ANN001 - Qt callback
        photo = current.data(Qt.UserRole) if current else None
        self.current_photo = photo
        self.thumbnail.show_image(photo.path if photo else None)
        if photo is None:
            self.set_summary("사진을 선택하면 추천 판단을 보여줍니다.")
            self.detail_label.setText("그룹과 사진을 선택하세요.")
            self.comparison_panel.set_comparison(None, None, [])
            self.metrics_panel.set_photo(None)
            self.explanation_label.setText("추천 사진과 현재 사진의 차이를 여기에서 설명합니다.")
            self.advanced_label.setText("")
            return
        self.update_selected_photo_details()
        self._sync_radio(photo.classification)

    def update_selected_photo_details(self) -> None:
        if self.current_photo is None:
            return
        self.thumbnail.show_image(self.current_photo.path)
        status, reason = recommendation_status(self.current_group, self.current_photo)
        self.set_summary(status)
        self.detail_label.setText(
            f"{self.current_photo.filename}\n"
            f"종합 {self.current_photo.metrics.overall:.1f}/10 · "
            f"현재 분류 {CLASSIFICATION_LABELS[self.current_photo.classification]}"
        )
        best_photo = self.current_group.best_photo if self.current_group is not None else None
        self.comparison_panel.set_comparison(
            self.current_photo,
            best_photo,
            compare_with_best(self.current_group, self.current_photo),
        )
        self.metrics_panel.set_photo(self.current_photo)
        if self.current_group is not None:
            self.explanation_label.setText(f"{reason}\n\n{best_photo_explanation(self.current_group, self.current_photo)}")
        else:
            self.explanation_label.setText(reason)
        self.advanced_label.setText(
            f"고급 정보: {self.current_photo.path}\n"
            f"pHash {self.current_photo.phash} · Raw sharpness {self.current_photo.sharpness:.2f}"
        )

    def _sync_radio(self, classification: Classification) -> None:
        mapping = {
            "keep": self.keep_radio,
            "review": self.review_radio,
            "trash_candidate": self.trash_radio,
        }
        mapping[classification].setChecked(True)

    def selected_classification(self) -> Classification:
        if self.keep_radio.isChecked():
            return "keep"
        if self.trash_radio.isChecked():
            return "trash_candidate"
        return "review"

    def apply_classification(self) -> None:
        if self.current_photo is None:
            return
        set_classification(self.current_photo, self.selected_classification())
        self.refresh_current_views()

    def classify_group_auto(self) -> None:
        if self.current_group is None:
            return
        best = self.current_group.best_photo
        for photo in self.current_group.photos:
            photo.classification = "keep" if photo is best else "trash_candidate"
        self.refresh_current_views()

    def refresh_current_views(self) -> None:
        self.group_list.set_groups(self.groups)
        if self.current_group:
            self.photo_list.set_group(self.current_group)
        if self.current_photo:
            self.update_selected_photo_details()

    def export_results(self, action: str) -> None:
        if self.source_folder is None or not self.groups:
            QMessageBox.information(self, "ShotKeeper", "먼저 폴더를 분석하세요.")
            return
        if action == "move":
            answer = QMessageBox.question(
                self,
                "결과 폴더로 이동",
                "원본 파일을 ShotKeeper_Result 하위 폴더로 이동합니다. 계속할까요?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        photos = [photo for group in self.groups for photo in group.photos]
        try:
            paths = export_photos(photos, self.source_folder, action=action)
            action_label = "복사" if action == "copy" else "이동"
            QMessageBox.information(self, "ShotKeeper", f"{len(paths)}개 파일을 ShotKeeper_Result로 {action_label}했습니다.")
        except Exception as exc:  # UI boundary: show recoverable error.
            QMessageBox.critical(self, "내보내기 실패", str(exc))

    def set_summary(self, text: str) -> None:
        self.summary_label.setText(text)
        if "보관 추천" in text:
            background, border = "#eef7ee", "#c8e6c9"
        elif "검토 권장" in text:
            background, border = "#fff8e1", "#ffe082"
        else:
            background, border = "#f7f9fc", "#d8dde6"
        self.summary_label.setStyleSheet(
            f"font-size: 18px; font-weight: 700; padding: 10px; background: {background}; "
            f"border: 1px solid {border}; border-radius: 8px;"
        )

    def toggle_advanced_info(self, checked: bool) -> None:
        self.advanced_label.setVisible(checked)
        self.advanced_toggle.setText("고급 정보 숨기기" if checked else "고급 정보 보기")
