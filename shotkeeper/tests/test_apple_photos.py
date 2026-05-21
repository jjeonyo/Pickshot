from __future__ import annotations

from pathlib import Path

import pytest

from app.core.apple_photos import (
    ApplePhotosIntegrationError,
    cache_asset_thumbnail,
    cache_selected_photo_assets,
    list_photo_albums,
    list_photo_assets,
    next_cache_destination,
)


class FakeDate:
    def __str__(self) -> str:
        return "2026-05-21 10:00:00"


class FakeNativeAsset:
    def __init__(self, identifier: str, width: int = 4032, height: int = 3024, filename: str | None = None) -> None:
        self._identifier = identifier
        self._width = width
        self._height = height
        self._filename = filename

    def localIdentifier(self) -> str:
        return self._identifier

    def pixelWidth(self) -> int:
        return self._width

    def pixelHeight(self) -> int:
        return self._height

    def creationDate(self) -> FakeDate:
        return FakeDate()

    def filename(self) -> str | None:
        return self._filename


class FakeFetchResult:
    def __init__(self, items) -> None:  # noqa: ANN001
        self.items = items

    def count(self) -> int:
        return len(self.items)

    def objectAtIndex_(self, index: int):  # noqa: ANN001
        return self.items[index]


class FakeFetchOptions:
    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        return self

    def setSortDescriptors_(self, descriptors):  # noqa: ANN001
        self.descriptors = descriptors


class FakeCollection:
    def __init__(self, identifier: str, title: str, assets: list[FakeNativeAsset]) -> None:
        self._identifier = identifier
        self._title = title
        self.assets = assets

    def localIdentifier(self) -> str:
        return self._identifier

    def localizedTitle(self) -> str:
        return self._title


class FakeAssetClass:
    all_assets: list[FakeNativeAsset] = []

    @classmethod
    def fetchAssetsWithMediaType_options_(cls, media_type, options):  # noqa: ANN001
        return FakeFetchResult(cls.all_assets)

    @classmethod
    def fetchAssetsWithLocalIdentifiers_options_(cls, identifiers, options):  # noqa: ANN001
        by_id = {asset.localIdentifier(): asset for asset in cls.all_assets}
        return FakeFetchResult([by_id[identifier] for identifier in identifiers if identifier in by_id])

    @classmethod
    def fetchAssetsInAssetCollection_options_(cls, collection, options):  # noqa: ANN001
        return FakeFetchResult(collection.assets)


class FakeAssetCollectionClass:
    collections: list[FakeCollection] = []

    @classmethod
    def fetchAssetCollectionsWithType_subtype_options_(cls, collection_type, subtype, options):  # noqa: ANN001
        return FakeFetchResult(cls.collections)

    @classmethod
    def fetchAssetCollectionsWithLocalIdentifiers_options_(cls, identifiers, options):  # noqa: ANN001
        by_id = {collection.localIdentifier(): collection for collection in cls.collections}
        return FakeFetchResult([by_id[identifier] for identifier in identifiers if identifier in by_id])


class FakePhotoLibrary:
    @staticmethod
    def authorizationStatusForAccessLevel_(access_level):  # noqa: ANN001
        return 3


class FakeOptions:
    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        return self

    def setSynchronous_(self, value):  # noqa: ANN001
        self.sync = value

    def setNetworkAccessAllowed_(self, value):  # noqa: ANN001
        self.network = value

    def setDeliveryMode_(self, value):  # noqa: ANN001
        self.delivery = value

    def setResizeMode_(self, value):  # noqa: ANN001
        self.resize = value


class FakeImageManager:
    requested_sizes = []

    @classmethod
    def defaultManager(cls):
        return cls()

    def requestImageForAsset_targetSize_contentMode_options_resultHandler_(self, asset, target_size, mode, options, handler):  # noqa: ANN001
        self.requested_sizes.append(target_size)
        handler(FakeImage(), {})


class FakeImage:
    def TIFFRepresentation(self):
        return b"tiff"


class FakeBitmap:
    @staticmethod
    def imageRepWithData_(data):  # noqa: ANN001
        return FakeBitmap()

    def representationUsingType_properties_(self, image_type, properties):  # noqa: ANN001
        return FakeJPEGData()


class FakeJPEGData:
    def writeToFile_atomically_(self, path: str, atomically: bool) -> bool:
        Path(path).write_bytes(b"jpeg")
        return True


class FakePhotos:
    PHAccessLevelReadWrite = 2
    PHAuthorizationStatusAuthorized = 3
    PHAuthorizationStatusLimited = 4
    PHAssetMediaTypeImage = 1
    PHImageContentModeAspectFit = 0
    PHImageRequestOptionsDeliveryModeHighQualityFormat = 1
    PHImageRequestOptionsResizeModeExact = 2
    PHPhotoLibrary = FakePhotoLibrary
    PHFetchOptions = FakeFetchOptions
    PHAsset = FakeAssetClass
    PHAssetCollection = FakeAssetCollectionClass
    PHAssetCollectionTypeAlbum = 1
    PHAssetCollectionTypeSmartAlbum = 2
    PHAssetCollectionSubtypeAny = 999
    PHImageRequestOptions = FakeOptions
    PHImageManager = FakeImageManager


class FakeSortDescriptor:
    @staticmethod
    def sortDescriptorWithKey_ascending_(key, ascending):  # noqa: ANN001
        return (key, ascending)


class FakeFoundation:
    NSSortDescriptor = FakeSortDescriptor


class FakeAppKit:
    NSImageCompressionFactor = "compression"
    NSBitmapImageFileTypeJPEG = 3
    NSBitmapImageRep = FakeBitmap


def test_list_photo_assets_pages_without_caching_images() -> None:
    FakeAssetClass.all_assets = [FakeNativeAsset("one"), FakeNativeAsset("two"), FakeNativeAsset("three")]

    page = list_photo_assets(offset=1, limit=1, photos_module=FakePhotos, foundation_module=FakeFoundation)

    assert page.total_count == 3
    assert page.has_more is True
    assert [asset.identifier for asset in page.assets] == ["two"]


def test_list_photo_assets_filters_by_album_and_search() -> None:
    FakeAssetClass.all_assets = [FakeNativeAsset("one"), FakeNativeAsset("two"), FakeNativeAsset("three")]
    FakeAssetCollectionClass.collections = [FakeCollection("album-1", "여행", [FakeAssetClass.all_assets[1]])]

    page = list_photo_assets(
        album_identifier="album-1",
        search_text="two",
        photos_module=FakePhotos,
        foundation_module=FakeFoundation,
    )

    assert page.total_count == 1
    assert [asset.identifier for asset in page.assets] == ["two"]


def test_list_photo_albums_includes_non_empty_albums() -> None:
    FakeAssetClass.all_assets = [FakeNativeAsset("one"), FakeNativeAsset("two")]
    FakeAssetCollectionClass.collections = [FakeCollection("album-1", "여행", [FakeAssetClass.all_assets[0]])]

    albums = list_photo_albums(photos_module=FakePhotos, foundation_module=FakeFoundation)

    assert [(album.identifier, album.title, album.asset_count) for album in albums] == [
        ("", "전체 사진", 2),
        ("album-1", "여행", 1),
    ]


def test_cache_selected_photo_assets_caches_only_selected_assets(tmp_path: Path) -> None:
    FakeAssetClass.all_assets = [
        FakeNativeAsset("A/B", filename="IMG_0001.HEIC"),
        FakeNativeAsset("C:D", filename="IMG_0002.PNG"),
        FakeNativeAsset("skip"),
    ]

    result = cache_selected_photo_assets(
        ["C:D", "A/B", "C:D"],
        tmp_path / "cache",
        photos_module=FakePhotos,
        appkit_module=FakeAppKit,
        foundation_module=FakeFoundation,
    )

    assert result.destination == (tmp_path / "cache").resolve()
    assert result.exported_count == 2
    assert [asset.identifier for asset in result.assets] == ["C:D", "A/B"]
    assert sorted(path.name for path in result.destination.glob("*.jpg")) == ["0001_IMG_0002.jpg", "0002_IMG_0001.jpg"]
    assert all(asset.filename.endswith(".jpg") for asset in result.assets)


def test_cache_selected_photo_assets_requires_selection(tmp_path: Path) -> None:
    with pytest.raises(ApplePhotosIntegrationError, match="선택"):
        cache_selected_photo_assets([], tmp_path / "cache", photos_module=FakePhotos, appkit_module=FakeAppKit, foundation_module=FakeFoundation)


def test_list_photo_assets_requires_available_photokit(monkeypatch) -> None:  # noqa: ANN001
    real_import = __import__

    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if name == "Photos":
            raise ModuleNotFoundError("Photos")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(ApplePhotosIntegrationError, match="pyobjc-framework-Photos"):
        list_photo_assets()


def test_cache_asset_thumbnail_writes_small_preview(tmp_path: Path) -> None:
    FakeAssetClass.all_assets = [FakeNativeAsset("thumb")]

    path = cache_asset_thumbnail("thumb", tmp_path / "thumbs", photos_module=FakePhotos, appkit_module=FakeAppKit)

    assert path.read_bytes() == b"jpeg"
    assert path.name == "thumb.jpg"


def test_next_cache_destination_avoids_existing_latest_folder(tmp_path: Path) -> None:
    (tmp_path / "latest").mkdir()

    assert next_cache_destination(tmp_path) == tmp_path / "latest_1"
