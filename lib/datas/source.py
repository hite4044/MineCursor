import json
from base64 import b64decode, b64encode
from io import BytesIO
from os import walk, makedirs
from os.path import join, isfile, abspath, expandvars, dirname
from typing import cast, Any
from zipfile import ZipFile

from PIL import Image

from lib.config import config
from lib.datas.base_struct import AssetType
from lib.log import logger


class SourceNotFoundError(Exception):
    def __init__(self, source_id: str, *messages):
        super().__init__(*messages)
        self.source_id = source_id


class AssetSource:
    """某个目录下的素材源"""
    def __init__(self,
                 name: str,
                 id: str,
                 version: str = "",
                 authors: str = "",
                 description: str = "",
                 note: str = "",
                 source_dir: str = "assets/sources"):
        super().__init__()
        self.name = name
        self.id = id
        self.version = version
        self.authors = authors
        self.description = description
        self.source_dir = abspath(source_dir)
        self.note = note

        self.internal_source: bool = False

    def __str__(self):
        return f"<AssetSource:[{self.name}],{self.id}>"

    @property
    def textures_zip(self):
        return self.fmt("textures.zip")

    @property
    def recommend_file(self):
        t = self.fmt("recommend.json")
        return t if isfile(t) else None

    @property
    def icon(self):
        t = self.fmt("icon.png")
        return t if isfile(t) else None

    def fmt(self, filename: str):
        return join(abspath(self.source_dir), filename)

    @classmethod
    def from_file(cls, fp: str):
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            name=data["name"],
            id=data["id"],
            version=data["version"],
            authors=data["authors"],
            description=data["description"],
            note=data.get("note", ""),
            source_dir=abspath(dirname(fp))
        )

    def to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "version": self.version,
            "authors": self.authors,
            "description": self.description,
            "note": self.note
        }

    def save(self):
        context = json.dumps(self.to_dict(), ensure_ascii=False, indent=4)
        with open(self.fmt("source.json"), "w", encoding="utf-8") as f:
            f.write(context)


class AssetSourceManager:
    """素材源管理器"""
    MINECRAFT_25W32A = AssetSource.from_file("assets/sources/25w32a/source.json")
    DEFAULT = MINECRAFT_25W32A

    def __init__(self):
        super().__init__()
        self.user_sources_dir = join(abspath(expandvars(config.data_dir)), "User Sources")
        makedirs(self.user_sources_dir, exist_ok=True)

        self.internal_sources = self.find_internal_sources()
        self.user_sources: list[AssetSource] = self.load_sources(self.user_sources_dir)
        self.zips: dict[str, ZipFile] = {}

        if config.enabled_sources is None:
            config.enabled_sources = [source.id for source in self.sources]

    def load_zip(self, source_id: str):
        """加载素材源的资源压缩包, 缓存避免重复打开"""
        if source_id not in self.zips:
            source = source_manager.get_source_by_id(source_id)
            with open(source.fmt(source.textures_zip), "rb") as f:
                bytes_io = BytesIO(f.read())
            self.zips[source_id] = ZipFile(bytes_io)

        return self.zips[source_id]

    @staticmethod
    def load_sources(root: str):
        """从一个目录下加载所有有效的素材源, 并返回素材源列表"""
        logger.info(f"加载用户素材源... (From: {root})")
        _, dirs, files = next(walk(root))
        sources = []

        for source_dir in dirs:
            source_cfg_fp = join(root, source_dir, "source.json")
            if isfile(source_cfg_fp):
                logger.info(f"已加载素材源: {source_dir}")
                source = AssetSource.from_file(source_cfg_fp)
                sources.append(source)

        return sources

    def save_source(self):
        """保存所有用户素材源"""
        for source in self.user_sources:
            source.save()

    @property
    def sources(self) -> list[AssetSource]:
        return self.internal_sources + self.user_sources

    def get_source_by_id(self, target_id: str, raise_error: bool = True) -> AssetSource | None:
        """根据素材源ID查找对应素材源"""
        for source in self.sources:
            if target_id == source.id:
                return source
        if raise_error:
            raise SourceNotFoundError(target_id, f"未找到id为 [{target_id}] 的素材源")
        return None

    @classmethod
    def find_internal_sources(cls):
        """查找写死在程序里的内置素材源"""
        sources = []
        for name, value in cls.__dict__.items():
            if name == "DEFAULT":
                continue
            if isinstance(value, AssetSource):
                value.internal_source = True
                sources.append(value)
        return sources


class AssetSourceInfo:
    """特定类型的素材源信息"""
    def __init__(self, type_: AssetType,
                 source_id: str | None = None,
                 source_path: str | None = None,

                 size: tuple[int, int] | None = None,

                 color: tuple[int, int, int] | tuple[int, int, int, int] | None = None,

                 image: Image.Image | None = None):
        self.type: AssetType = type_
        self.source_id: str = source_id
        self.source_path: str = source_path

        self.size = size
        self.color = color

        self.image = image

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type.value}
        if self.type == AssetType.ZIP_FILE:
            data["source_id"] = self.source_id
            data["source_path"] = self.source_path
        elif self.type == AssetType.RECT:
            data["size"] = list(self.size)
            data["color"] = list(self.color)
        elif self.type == AssetType.IMAGE:
            image_io = BytesIO()
            self.image.save(image_io, format="PNG")
            data["size"] = list(self.size)
            data["image"] = b64encode(image_io.getvalue()).decode("utf-8")
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]):
        asset_type = AssetType(data["type"])
        if asset_type == AssetType.ZIP_FILE:
            return AssetSourceInfo(
                type_=asset_type,
                source_id=data["source_id"],
                source_path=data["source_path"],
            )
        elif asset_type == AssetType.RECT:
            return AssetSourceInfo(
                type_=asset_type,
                size=cast(tuple[int, int], tuple(data["size"])),
                color=cast(tuple[int, int, int, int], tuple(data["color"]))
            )
        elif asset_type == AssetType.IMAGE:
            image_io = BytesIO(b64decode(data["image"]))
            image = Image.open(image_io)
            return AssetSourceInfo(
                type_=asset_type,
                size=image.size,
                image=image
            )

    def load_frame(self) -> Image.Image:
        """将本素材源加载成帧"""
        if self.type == AssetType.ZIP_FILE:
            zip_file = source_manager.load_zip(self.source_id)
            return Image.open(zip_file.open(self.source_path)).convert("RGBA")
        elif self.type == AssetType.RECT:
            if len(self.color) == 3:
                return Image.new("RGBA", self.size, (*self.color, 255))
            elif len(self.color) == 4:
                return Image.new("RGBA", self.size, self.color)
        elif self.type == AssetType.IMAGE:
            return self.image
        raise NotImplementedError("Unsupported asset type")


source_manager: AssetSourceManager = AssetSourceManager()
