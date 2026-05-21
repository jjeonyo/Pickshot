from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ApplePhotosIntegrationError(RuntimeError):
    """Raised when ShotKeeper cannot read from the Apple Photos library."""


@dataclass(frozen=True, slots=True)
class ApplePhotoAsset:
    """Small, UI-safe descriptor for an Apple Photos asset."""

    identifier: str
    filename: str
    width: int
    height: int
    created_at: str | None = None
    _native: Any = field(default=None, repr=False, compare=False)

    @property
    def display_title(self) -> str:
        return self.filename.replace(".jpg", "")


@dataclass(frozen=True, slots=True)
class ApplePhotoAlbum:
    identifier: str
    title: str
    asset_count: int


@dataclass(frozen=True, slots=True)
class ApplePhotosPage:
    assets: list[ApplePhotoAsset]
    total_count: int
    offset: int
    limit: int

    @property
    def next_offset(self) -> int:
        return self.offset + len(self.assets)

    @property
    def has_more(self) -> bool:
        return self.next_offset < self.total_count


@dataclass(frozen=True, slots=True)
class ApplePhotosLibraryResult:
    destination: Path
    exported_count: int
    assets: list[ApplePhotoAsset]


ApplePhotosImportResult = ApplePhotosLibraryResult


def default_apple_photos_cache_root() -> Path:
    return Path.home() / "Pictures" / "ShotKeeper_Apple_Photos_Cache"


def default_apple_photos_import_root() -> Path:
    return default_apple_photos_cache_root()


def next_cache_destination(root: str | Path | None = None) -> Path:
    base = Path(root) if root is not None else default_apple_photos_cache_root()
    candidate = base / "latest"
    if not candidate.exists():
        return candidate

    counter = 1
    while True:
        candidate = base / f"latest_{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def next_import_destination(root: str | Path | None = None) -> Path:
    return next_cache_destination(root)


def list_photo_albums(
    *,
    photos_module: Any | None = None,
    foundation_module: Any | None = None,
) -> list[ApplePhotoAlbum]:
    """List user and smart albums for narrowing Apple Photos selection."""

    photos = photos_module or _import_module("Photos", "pyobjc-framework-Photos")
    foundation = foundation_module or _import_module("Foundation", "pyobjc-framework-Cocoa")
    _ensure_authorized(photos)

    albums = [ApplePhotoAlbum(identifier="", title="전체 사진", asset_count=_fetch_all_image_assets(photos, foundation).count())]
    seen = {""}
    for collection_type in (
        getattr(photos, "PHAssetCollectionTypeAlbum", 1),
        getattr(photos, "PHAssetCollectionTypeSmartAlbum", 2),
    ):
        fetch_result = photos.PHAssetCollection.fetchAssetCollectionsWithType_subtype_options_(
            collection_type,
            getattr(photos, "PHAssetCollectionSubtypeAny", 9223372036854775807),
            None,
        )
        for index in range(int(fetch_result.count())):
            collection = fetch_result.objectAtIndex_(index)
            identifier = str(_call(collection, "localIdentifier", fallback=""))
            if not identifier or identifier in seen:
                continue
            count = int(photos.PHAsset.fetchAssetsInAssetCollection_options_(collection, None).count())
            if count <= 0:
                continue
            title = str(_call(collection, "localizedTitle", fallback="앨범")) or "앨범"
            albums.append(ApplePhotoAlbum(identifier=identifier, title=title, asset_count=count))
            seen.add(identifier)
    return albums


def list_photo_assets(
    *,
    offset: int = 0,
    limit: int = 200,
    album_identifier: str | None = None,
    search_text: str = "",
    photos_module: Any | None = None,
    foundation_module: Any | None = None,
) -> ApplePhotosPage:
    """List Apple Photos image assets for UI selection without analyzing images."""

    if offset < 0:
        raise ApplePhotosIntegrationError("Apple 사진첩 시작 위치는 0 이상이어야 합니다.")
    if limit <= 0:
        raise ApplePhotosIntegrationError("Apple 사진첩 표시 개수는 1장 이상이어야 합니다.")

    photos = photos_module or _import_module("Photos", "pyobjc-framework-Photos")
    foundation = foundation_module or _import_module("Foundation", "pyobjc-framework-Cocoa")
    _ensure_authorized(photos)

    fetch_result = _fetch_image_assets(photos, foundation, album_identifier=album_identifier)
    raw_count = int(fetch_result.count())
    if search_text.strip():
        query = search_text.strip().casefold()
        descriptors = [
            descriptor
            for index in range(raw_count)
            if query in _search_blob((descriptor := _asset_descriptor(fetch_result.objectAtIndex_(index), index=index + 1)))
        ]
        total_count = len(descriptors)
        end = min(offset + limit, total_count)
        return ApplePhotosPage(assets=descriptors[offset:end], total_count=total_count, offset=offset, limit=limit)

    total_count = raw_count
    end = min(offset + limit, total_count)
    assets = [_asset_descriptor(fetch_result.objectAtIndex_(index), index=index + 1) for index in range(offset, end)]
    return ApplePhotosPage(assets=assets, total_count=total_count, offset=offset, limit=limit)


def cache_asset_thumbnail(
    identifier: str,
    destination: str | Path,
    *,
    photos_module: Any | None = None,
    appkit_module: Any | None = None,
    max_dimension: int = 240,
) -> Path:
    """Create a small thumbnail cache for a displayed Apple Photos asset."""

    photos = photos_module or _import_module("Photos", "pyobjc-framework-Photos")
    appkit = appkit_module or _import_module("AppKit", "pyobjc-framework-Cocoa")
    _ensure_authorized(photos)
    native_assets = _fetch_assets_by_identifiers(photos, [identifier])
    if not native_assets:
        raise ApplePhotosIntegrationError("Apple 사진 썸네일을 찾지 못했습니다.")
    thumb_dir = Path(destination).expanduser().resolve()
    thumb_dir.mkdir(parents=True, exist_ok=True)
    output_path = thumb_dir / f"{_safe_identifier(identifier)}.jpg"
    if not output_path.exists():
        _write_asset_jpeg(photos, appkit, native_assets[0], output_path, max_dimension=max_dimension)
    return output_path


def cache_selected_photo_assets(
    identifiers: list[str],
    destination: str | Path,
    *,
    photos_module: Any | None = None,
    appkit_module: Any | None = None,
    foundation_module: Any | None = None,
) -> ApplePhotosLibraryResult:
    """Cache only user-selected Apple Photos assets for ShotKeeper analysis."""

    unique_identifiers = list(dict.fromkeys(identifier for identifier in identifiers if identifier))
    if not unique_identifiers:
        raise ApplePhotosIntegrationError("분석할 Apple 사진을 먼저 선택하세요.")

    photos = photos_module or _import_module("Photos", "pyobjc-framework-Photos")
    appkit = appkit_module or _import_module("AppKit", "pyobjc-framework-Cocoa")
    foundation = foundation_module or _import_module("Foundation", "pyobjc-framework-Cocoa")
    _ensure_authorized(photos)

    native_assets = _fetch_assets_by_identifiers(photos, unique_identifiers)
    if not native_assets:
        raise ApplePhotosIntegrationError("선택한 Apple 사진을 보관함에서 찾지 못했습니다.")

    cache_destination = Path(destination).expanduser().resolve()
    cache_destination.mkdir(parents=True, exist_ok=True)

    exported_assets: list[ApplePhotoAsset] = []
    for index, native_asset in enumerate(native_assets, start=1):
        descriptor = _asset_descriptor(native_asset, index=index)
        output_path = cache_destination / descriptor.filename
        _write_asset_jpeg(photos, appkit, native_asset, output_path)
        exported_assets.append(descriptor)

    return ApplePhotosLibraryResult(
        destination=cache_destination,
        exported_count=len(exported_assets),
        assets=exported_assets,
    )


def load_recent_photos_library(
    destination: str | Path,
    *,
    limit: int = 200,
    photos_module: Any | None = None,
    appkit_module: Any | None = None,
    foundation_module: Any | None = None,
) -> ApplePhotosLibraryResult:
    """Compatibility wrapper; cache a recent page only when explicitly called."""

    page = list_photo_assets(offset=0, limit=limit, photos_module=photos_module, foundation_module=foundation_module)
    return cache_selected_photo_assets(
        [asset.identifier for asset in page.assets],
        destination,
        photos_module=photos_module,
        appkit_module=appkit_module,
        foundation_module=foundation_module,
    )


def _import_module(name: str, package_hint: str) -> Any:
    try:
        return __import__(name)
    except ModuleNotFoundError as exc:
        raise ApplePhotosIntegrationError(
            f"Apple 사진첩 직접 연동에는 {package_hint} 의존성이 필요합니다. requirements.txt 설치 후 다시 실행하세요."
        ) from exc


def _ensure_authorized(photos: Any, *, timeout_seconds: float = 60.0) -> None:
    read_write = getattr(photos, "PHAccessLevelReadWrite", None)
    authorized_values = {
        getattr(photos, "PHAuthorizationStatusAuthorized", 3),
        getattr(photos, "PHAuthorizationStatusLimited", 4),
    }

    status = _authorization_status(photos, read_write)
    if status in authorized_values:
        return

    request = getattr(photos.PHPhotoLibrary, "requestAuthorizationForAccessLevel_handler_", None)
    if request is None or read_write is None:
        raise ApplePhotosIntegrationError("macOS PhotoKit 권한 요청 API를 사용할 수 없습니다.")

    event = threading.Event()
    received: dict[str, int] = {}

    def handler(new_status: int) -> None:
        received["status"] = int(new_status)
        event.set()

    request(read_write, handler)
    if not event.wait(timeout_seconds):
        raise ApplePhotosIntegrationError("Apple 사진첩 접근 권한 확인 시간이 초과되었습니다.")

    if received.get("status") not in authorized_values:
        raise ApplePhotosIntegrationError("Apple 사진첩 접근 권한이 허용되지 않았습니다. macOS 개인정보 보호 설정을 확인하세요.")


def _authorization_status(photos: Any, read_write: int | None) -> int:
    if read_write is not None and hasattr(photos.PHPhotoLibrary, "authorizationStatusForAccessLevel_"):
        return int(photos.PHPhotoLibrary.authorizationStatusForAccessLevel_(read_write))
    return int(photos.PHPhotoLibrary.authorizationStatus())


def _fetch_all_image_assets(photos: Any, foundation: Any) -> Any:
    options = _sorted_fetch_options(photos, foundation)
    return photos.PHAsset.fetchAssetsWithMediaType_options_(photos.PHAssetMediaTypeImage, options)


def _fetch_image_assets(photos: Any, foundation: Any, *, album_identifier: str | None = None) -> Any:
    if not album_identifier:
        return _fetch_all_image_assets(photos, foundation)
    fetcher = getattr(photos.PHAssetCollection, "fetchAssetCollectionsWithLocalIdentifiers_options_", None)
    if fetcher is None:
        raise ApplePhotosIntegrationError("PhotoKit 앨범 조회 API를 사용할 수 없습니다.")
    collections = fetcher([album_identifier], None)
    if int(collections.count()) == 0:
        raise ApplePhotosIntegrationError("선택한 Apple 사진 앨범을 찾지 못했습니다.")
    return photos.PHAsset.fetchAssetsInAssetCollection_options_(collections.objectAtIndex_(0), _sorted_fetch_options(photos, foundation))


def _sorted_fetch_options(photos: Any, foundation: Any) -> Any:
    options = photos.PHFetchOptions.alloc().init()
    if hasattr(foundation, "NSSortDescriptor"):
        descriptor = foundation.NSSortDescriptor.sortDescriptorWithKey_ascending_("creationDate", False)
        options.setSortDescriptors_([descriptor])
    return options


def _fetch_assets_by_identifiers(photos: Any, identifiers: list[str]) -> list[Any]:
    fetcher = getattr(photos.PHAsset, "fetchAssetsWithLocalIdentifiers_options_", None)
    if fetcher is None:
        raise ApplePhotosIntegrationError("PhotoKit 선택 사진 조회 API를 사용할 수 없습니다.")
    fetch_result = fetcher(identifiers, None)
    return [fetch_result.objectAtIndex_(index) for index in range(int(fetch_result.count()))]


def _asset_descriptor(asset: Any, *, index: int) -> ApplePhotoAsset:
    identifier = str(_call(asset, "localIdentifier", fallback=f"asset-{index}"))
    width = int(_call(asset, "pixelWidth", fallback=0) or 0)
    height = int(_call(asset, "pixelHeight", fallback=0) or 0)
    created = _call(asset, "creationDate", fallback=None)
    created_text = str(created) if created is not None else None
    original_name = _call(asset, "filename", fallback=None) or _call(asset, "originalFilename", fallback=None)
    stem = Path(str(original_name)).stem if original_name else _safe_identifier(identifier)
    filename = f"{index:04d}_{_safe_identifier(stem)}.jpg"
    return ApplePhotoAsset(identifier=identifier, filename=filename, width=width, height=height, created_at=created_text, _native=asset)


def _search_blob(asset: ApplePhotoAsset) -> str:
    return " ".join([asset.identifier, asset.filename, asset.created_at or ""]).casefold()


def _write_asset_jpeg(photos: Any, appkit: Any, asset: Any, output_path: Path, *, max_dimension: int = 2400) -> None:
    manager = photos.PHImageManager.defaultManager()
    options = photos.PHImageRequestOptions.alloc().init()
    options.setSynchronous_(True)
    options.setNetworkAccessAllowed_(True)
    if hasattr(photos, "PHImageRequestOptionsDeliveryModeHighQualityFormat"):
        options.setDeliveryMode_(photos.PHImageRequestOptionsDeliveryModeHighQualityFormat)
    if hasattr(photos, "PHImageRequestOptionsResizeModeExact"):
        options.setResizeMode_(photos.PHImageRequestOptionsResizeModeExact)

    width = max(int(_call(asset, "pixelWidth", fallback=0) or 0), 1)
    height = max(int(_call(asset, "pixelHeight", fallback=0) or 0), 1)
    scale = min(1.0, max_dimension / max(width, height))
    target_size = (max(1, int(width * scale)), max(1, int(height * scale)))

    captured: dict[str, Any] = {"image": None}
    event = threading.Event()

    def handler(image: Any, info: Any) -> None:  # noqa: ANN001
        captured["image"] = image
        event.set()

    manager.requestImageForAsset_targetSize_contentMode_options_resultHandler_(
        asset,
        target_size,
        photos.PHImageContentModeAspectFit,
        options,
        handler,
    )
    event.wait(10)

    image = captured["image"]
    if image is None:
        raise ApplePhotosIntegrationError(f"Apple 사진 이미지를 캐시에 저장하지 못했습니다: {_call(asset, 'localIdentifier', fallback='unknown')}")

    _save_nsimage_as_jpeg(appkit, image, output_path)


def _save_nsimage_as_jpeg(appkit: Any, image: Any, output_path: Path) -> None:
    tiff_data = image.TIFFRepresentation()
    if tiff_data is None:
        raise ApplePhotosIntegrationError("Apple 사진 이미지를 JPEG로 변환하지 못했습니다.")

    bitmap = appkit.NSBitmapImageRep.imageRepWithData_(tiff_data)
    if bitmap is None:
        raise ApplePhotosIntegrationError("Apple 사진 이미지 데이터를 JPEG로 변환하지 못했습니다.")

    properties = {appkit.NSImageCompressionFactor: 0.92}
    jpeg_data = bitmap.representationUsingType_properties_(appkit.NSBitmapImageFileTypeJPEG, properties)
    if jpeg_data is None or not jpeg_data.writeToFile_atomically_(str(output_path), True):
        raise ApplePhotosIntegrationError(f"Apple 사진 캐시 파일을 저장하지 못했습니다: {output_path}")


def _call(obj: Any, name: str, *, fallback: Any = None) -> Any:
    attr = getattr(obj, name, None)
    if attr is None:
        return fallback
    return attr() if callable(attr) else attr


def _safe_identifier(identifier: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", identifier).strip("_")[:80] or "apple_photo"
