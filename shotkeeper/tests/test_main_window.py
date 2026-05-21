from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core.apple_photos import ApplePhotosLibraryResult  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_apple_photos_selection_cached_sets_source_folder_and_runs_analysis(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    app()
    cache_folder = tmp_path / "photokit-cache"
    analyzed = []
    monkeypatch.setattr(MainWindow, "analyze_folder", lambda self: analyzed.append(self.source_folder))

    window = MainWindow()
    result = ApplePhotosLibraryResult(destination=cache_folder, exported_count=2, assets=[])
    window.on_apple_photos_selection_cached(result)

    assert window.source_folder == cache_folder
    assert analyzed == [cache_folder]
    assert window.apple_photos_button.isEnabled()
