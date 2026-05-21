from __future__ import annotations

import os
import plistlib
import subprocess
from pathlib import Path

APP_NAME = "ShotKeeper"
BUNDLE_ID = "local.shotkeeper.desktop"
PHOTO_USAGE = "ShotKeeper가 사용자가 선택한 Apple 사진을 유사도 분석하고 정리 후보로 보여주기 위해 사진 보관함을 읽습니다. 원본 사진은 삭제하거나 수정하지 않습니다."


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_app_bundle(root: Path) -> Path:
    app_path = root / "build" / f"{APP_NAME}.app"
    contents = app_path / "Contents"
    macos = contents / "MacOS"
    macos.mkdir(parents=True, exist_ok=True)

    plist = {
        "CFBundleDevelopmentRegion": "ko",
        "CFBundleDisplayName": APP_NAME,
        "CFBundleExecutable": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "10.15",
        "NSHighResolutionCapable": True,
        "NSPhotoLibraryUsageDescription": PHOTO_USAGE,
    }
    with (contents / "Info.plist").open("wb") as file:
        plistlib.dump(plist, file)

    executable = macos / APP_NAME
    executable.write_text(
        "#!/bin/zsh\n"
        "set -e\n"
        f"cd {root}\n"
        "exec ./.venv/bin/python main.py\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return app_path


def main() -> int:
    root = project_root()
    app_path = build_app_bundle(root)
    subprocess.run(["open", "-na", str(app_path)], check=True)
    print(f"{app_path} 실행 요청 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
