import os.path
import random
import re
import typing
from base64 import b64encode, b64decode
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from io import BytesIO
from os import makedirs
from os.path import expandvars, join
from typing import Any, cast
from zipfile import ZipFile

from PIL import Image

from lib.config import config
from lib.cursor.setter import CursorKind
from lib.struct import ThemeType

INVALID_FILENAME_CHAR = re.compile(r'[<>:"/\\|?*]')


def generate_id(length: int = 4):
    return hex(int.from_bytes(random.randbytes(length), "big"))[2:]


class DataClassSaveLoadMixin:
    def save(self, use_dict: bool = False) -> list[Any] | dict[str, Any]:
        field_names = getattr(self, "__dataclass_fields__").keys()
        if use_dict:
            fields = {}
            for field_name in field_names:
                attr_value = getattr(self, field_name)
                fields[field_name] = attr_value
        else:
            fields = []
            for field_name in field_names:
                fields.append(getattr(self, field_name))
        return fields

    # noinspection PyArgumentList
    @classmethod
    def load(cls, data: list[Any] | dict[str, Any]):
        if isinstance(data, dict):
            return cls(**data)
        else:
            return cls(*data)

    def __getitem__(self, item):
        field_names = list(getattr(self, "__dataclass_fields__").keys())
        return getattr(self, field_names[item])


class SourceLoadManager:
    def __init__(self):
        self.zips: dict[str, ZipFile] = {}

    def load_zip(self, source_id: str):
        if source_id not in self.zips:
            source = AssetSources.get_source_by_id(source_id)
            with open(source.textures_zip, "rb") as f:
                bytes_io = BytesIO(f.read())
            self.zips[source_id] = ZipFile(bytes_io)

        return self.zips[source_id]


class DataDir(str):
    def __new__(cls, path: str, *args, **kwargs) -> 'DataDir':
        makedirs(path, exist_ok=True)
        instance = str.__new__(cls, path)
        instance.make_sub_dir = lambda name: DataDir.make_sub_dir(typing.cast(DataDir, instance), name)
        return typing.cast(DataDir, instance)

    def make_sub_dir(self, name: str) -> 'DataDir':
        makedirs(join(self, name), exist_ok=True)
        return DataDir(join(self, name))


@dataclass
class Position(DataClassSaveLoadMixin):
    x: int
    y: int


@dataclass
class Scale2D(DataClassSaveLoadMixin):
    x: float
    y: float


@dataclass
class Margins(DataClassSaveLoadMixin):
    left: int
    right: int
    up: int
    down: int


class AssetType(Enum):
    ZIP_FILE = 0
    RECT = 1
    IMAGE = 2


class AssetSourceInfo:
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

    def to_dict(self):
        if self.type == AssetType.ZIP_FILE:
            return {
                "type": self.type.value,
                "source_id": self.source_id,
                "source_path": self.source_path,
            }
        elif self.type == AssetType.RECT:
            return {
                "type": self.type.value,
                "size": list(self.size),
                "color": list(self.color)
            }
        elif self.type == AssetType.IMAGE:
            image_io = BytesIO()
            self.image.save(image_io, format="PNG")
            return {
                "type": self.type.value,
                "size": list(self.size),
                "image": b64encode(image_io.getvalue()).decode("utf-8")
            }

    @staticmethod
    def from_dict(data: dict):
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
        if self.type == AssetType.ZIP_FILE:
            zip_file = source_load_manager.load_zip(self.source_id)
            return Image.open(zip_file.open(self.source_path)).convert("RGBA")
        elif self.type == AssetType.RECT:
            if len(self.color) == 3:
                return Image.new("RGBA", self.size, (*self.color, 255))
            elif len(self.color) == 4:
                return Image.new("RGBA", self.size, self.color)
        elif self.type == AssetType.IMAGE:
            return self.image
        raise NotImplementedError


class ProcessStep(Enum):
    TRANSPOSE = 1
    CROP = 2
    SCALE = 3
    ROTATE = 4


class ReverseWay(Enum):
    X_FIRST = 0
    Y_FIRST = 1
    BOTH = 2


class SubProjectFrames(list):
    def __init__(self, project: 'CursorProject'):
        super().__init__()
        from lib.render import render_project_frame
        self.render_project_frame = render_project_frame
        self.project = project

    def __getitem__(self, index: int):
        return self.render_project_frame(self.project, index)

    def __len__(self):
        return self.project.frame_count


@dataclass
class AnimationKeyData(DataClassSaveLoadMixin):
    frame_start: int = 0
    frame_inv: int = 1
    frame_length: int = 1


@dataclass
class AnimationFrameData(DataClassSaveLoadMixin):
    index_increment: int = 1
    frame_delay: int = 1


DEFAULT_PROC_ORDER = (ProcessStep.TRANSPOSE, ProcessStep.CROP, ProcessStep.SCALE, ProcessStep.ROTATE)


class CursorElement:

    def __init__(self,
                 name: str,
                 frames: list[Image.Image],
                 source_infos: list[AssetSourceInfo] = None,
                 position: Position = None,
                 scale: Scale2D = None,
                 rotation: float = 0,
                 crop_margins: Margins = None,
                 reverse_x: bool = False,
                 reverse_y: bool = False,
                 resample: Image.Resampling = Image.Resampling.NEAREST,
                 scale_resample: Image.Resampling = Image.Resampling.NEAREST):
        if source_infos is None:
            source_infos = []
        self.name: str = name
        self.frames: list[Image.Image] = frames
        self.source_infos: list[AssetSourceInfo] = source_infos
        self.position: Position = position if position else Position(0, 0)
        self.scale: Scale2D = scale if scale else Scale2D(1.0, 1.0)
        self.rotation: float = rotation
        self.crop_margins: Margins = crop_margins if crop_margins else Margins(0, 0, 0, 0)
        self.reverse_x: bool = reverse_x
        self.reverse_y: bool = reverse_y
        self.reverse_way: ReverseWay = ReverseWay.BOTH
        self.scale_resample: Image.Resampling = scale_resample
        self.resample: Image.Resampling = resample
        self.mask: Image.Image | None = None
        self.mask_color: tuple[int, int, int] | None = None

        self.enable_key_ani: bool = False
        self.animation_key_data: AnimationKeyData = AnimationKeyData()
        self.animation_start_offset: int = 0  # 元素在XX帧开始显示并播放播放
        self.loop_animation: bool = True
        self.reverse_animation: bool = False
        self.animation_data: list[AnimationFrameData] = [AnimationFrameData() for _ in range(len(frames))]
        self.animation_data_index: list[int] = []
        self.proc_step = DEFAULT_PROC_ORDER
        self.final_rect = (0, 0, 16, 16)
        self.final_image = Image.new("RGBA", (16, 16))
        self.sub_project: CursorProject | None = None
        self.id = int.from_bytes(random.randbytes(4), "big")

        self.animation_key_data.frame_length = len(self.frames)
        self.build_animation_index()

    def update_ani_data_by_key_data(self):
        self.animation_data.clear()
        key_data = self.animation_key_data
        for i in range(0, key_data.frame_length, key_data.frame_inv):
            self.animation_data.append(AnimationFrameData(key_data.frame_inv, 1))
        self.build_animation_index()

    def build_animation_index(self):
        index = 0
        self.animation_data_index.clear()
        for data in self.animation_data:
            for _ in range(data.frame_delay):
                self.animation_data_index.append(index)
            index += data.index_increment

    def get_frame_index(self, target_frame: int) -> int:
        target_frame -= self.animation_start_offset

        timer_frame = 0
        frame = 0
        if target_frame == 0:
            return 0
        index = 0
        clac_cnt = 0
        while True:
            data = self.animation_data[index]
            timer_frame += data.frame_delay
            index += 1
            if index >= len(self.animation_data):
                index = 0
            if timer_frame > target_frame:
                return frame
            frame += data.index_increment
            clac_cnt += 1
            if clac_cnt > 1000:
                raise RuntimeError("动画帧查找次数过多")

    def to_dict(self):
        data = {
            "name": self.name,
            "source_infos": [source_info.to_dict() for source_info in self.source_infos],
            "position": self.position.save(),
            "scale": self.scale.save(),
            "rotation": self.rotation,
            "crop_margins": self.crop_margins.save(),
            "reverse_x": self.reverse_x,
            "reverse_y": self.reverse_y,
            "reverse_way": self.reverse_way.value,
            "scale_resample": self.scale_resample.value,
            "resample": self.resample.value,
            "animation_start_offset": self.animation_start_offset,
            "loop_animation": self.loop_animation,
            "reverse_animation": self.reverse_animation,
            "animation_key_data": self.animation_key_data.save(),
            "animation_data": [data.save() for data in self.animation_data],
            "proc_step": [step.value for step in self.proc_step],
        }
        if self.mask:
            data["mask"] = (self.mask.size, b64encode(self.mask.tobytes()).decode("utf-8"))
        if self.mask_color:
            data["mask_color"] = list(self.mask_color)
        if self.sub_project:
            data["sub_project"] = self.sub_project.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict) -> 'CursorElement':
        element = CursorElement(
            name=data["name"],
            frames=[],
            source_infos=[AssetSourceInfo.from_dict(source_info) for source_info in data["source_infos"]],
            position=Position.load(data["position"]),
            scale=Scale2D.load(data["scale"]),
            rotation=data["rotation"],
            crop_margins=Margins.load(data["crop_margins"]),
            reverse_x=data["reverse_x"],
            reverse_y=data["reverse_y"],
            resample=Image.Resampling(data["resample"]),
            scale_resample=Image.Resampling(data.get("scale_resample", Image.Resampling.NEAREST)),
        )
        if "mask" in data:
            if isinstance(data["mask"][1], bytes):
                element.mask = Image.frombytes("L", data["mask"][0], data["mask"][1])
            else:
                element.mask = Image.frombytes("L", data["mask"][0], b64decode(data["mask"][1]))
        element.mask_color = tuple(data.get("mask_color")) if data.get("mask_color") else None
        element.animation_start_offset = data.get("animation_start_offset", element.animation_start_offset)
        element.loop_animation = data.get("loop_animation", element.loop_animation)
        element.reverse_animation = data.get("reverse_animation", element.reverse_animation)
        element.animation_key_data = AnimationKeyData.load(data["animation_key_data"])
        element.animation_data = [AnimationFrameData.load(data) for data in data["animation_data"]]
        element.proc_step = [ProcessStep(step) for step in data["proc_step"]]
        element.reverse_way = ReverseWay(data.get("reverse_way", ReverseWay.BOTH.value))
        if data.get("sub_project"):
            element.sub_project = CursorProject.from_dict(data["sub_project"])

        for source_info in element.source_infos:
            frame = source_info.load_frame()
            element.frames.append(frame)

        element.build_animation_index()

        if element.sub_project:
            element.frames = SubProjectFrames(element.sub_project)

        return element

    def create_sub_project(self, name: str = "新子项目", size: tuple[int, int] = (16, 16),
                           elements: list['CursorElement'] | None = None):
        """根据参数为本元素创建一个子项目"""
        frame_count = 20
        min_index = 0
        if elements:
            min_index = 114514
            max_index = -114514
            for element in elements:
                min_index = min(min_index, element.animation_start_offset)
                max_index = max(max_index, element.animation_start_offset)
            frame_count = max_index - min_index

        sub_project = CursorProject(name, size)
        sub_project.scale = 1.0
        sub_project.is_ani_cursor = True
        sub_project.frame_count = frame_count
        for element in elements:
            warp_element = element.copy()
            warp_element.animation_start_offset -= min_index
            sub_project.elements.append(warp_element)
        self.sub_project = sub_project
        self.frames = SubProjectFrames(sub_project)

    def copy(self) -> 'CursorElement':
        return CursorElement.from_dict(self.to_dict())

    def __hash__(self):
        return self.id

    def __str__(self):
        return f"<Element:{self.name} at {self.position}>"


class CursorProject:
    def __init__(self, name: str, canvas_size: tuple[int, int]):
        self.name: str | None = name
        self.raw_canvas_size = canvas_size
        self.external_name: str | None = None
        self.kind: CursorKind = CursorKind.ARROW
        self.elements: list[CursorElement] = []
        self.center_pos = Position(0, 0)
        self.scale = 2.0
        self.resample: Image.Resampling = Image.Resampling.NEAREST
        self.is_ani_cursor = False
        self.frame_count = 20
        self.ani_rate: int = 6
        self.ani_rates: list[int] | None = None

        self.own_note: str | None = None
        self.own_license_info: str | None = None
        self.create_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.make_time: float = 0.0

        self.id: str = generate_id(4)

    @property
    def frame_delay(self) -> int:
        return self.ani_rate * 1000 // 60

    @property
    def canvas_size(self) -> tuple[int, int]:
        return int(self.raw_canvas_size[0] * self.scale), int(self.raw_canvas_size[1] * self.scale)

    def add_element(self, element: CursorElement):
        self.elements.insert(0, element)

    def __str__(self):
        return f"<Project:[{self.name}{',' + self.external_name if self.external_name else ''}]>"

    def to_dict(self):
        data = {
            "name": self.name,
            "raw_canvas_size": list(self.raw_canvas_size),
            "external_name": self.external_name,
            "kind": self.kind.value,
            "elements": [element.to_dict() for element in self.elements],
            "center_pos": self.center_pos.save(),
            "scale": self.scale,
            "resample": self.resample.value,
            "is_ani_cursor": self.is_ani_cursor,
            "frame_count": self.frame_count,
            "ani_rate": self.ani_rate,
            "ani_rates": self.ani_rates,

            "make_time": self.make_time
        }
        if self.own_note:
            data["own_note"] = self.own_note
        if self.own_license_info:
            data["license_info"] = self.own_license_info
        return data

    @staticmethod
    def from_dict(data: dict) -> 'CursorProject':
        project = CursorProject(
            name=data["name"],
            canvas_size=cast(tuple[int, int], tuple(data["raw_canvas_size"])),
        )
        project.external_name = data["external_name"]
        project.kind = CursorKind(data["kind"])
        project.elements = [CursorElement.from_dict(element) for element in data["elements"]]
        project.center_pos = Position.load(data["center_pos"])
        project.scale = data["scale"]
        project.resample = Image.Resampling(data["resample"])
        project.is_ani_cursor = data["is_ani_cursor"]
        project.frame_count = data["frame_count"]
        project.ani_rate = data["ani_rate"]
        project.ani_rates = data.get("ani_rates")
        project.make_time = data.get("make_time", 0)
        project.own_note = data.get("own_note")
        project.own_license_info = data.get("license_info")
        return project

    def copy(self) -> 'CursorProject':
        return CursorProject.from_dict(self.to_dict())

    def find_element(self, element_id: str):
        for element in self.elements:
            if element.id == element_id:
                return element
        return None


DEFAULT_NOTE = """这个人或许不想写备注"""

DEFAULT_LICENSE_INFO = """\
主题提供协议 - CC BY-NC-SA 4.0:
https://creativecommons.org/licenses/by-nc-sa/4.0/

此主题使用的部分游戏资源, 遵循此条款:
https://www.minecraft.net/usage-guidelines
"""


@dataclass
class CursorTheme:
    name: str
    base_size: int = 32
    author: str = "Unknow"
    description: str = "None"
    type: ThemeType = ThemeType.NORMAL
    projects: list[CursorProject] = field(default_factory=list)

    id: str = field(default_factory=generate_id)

    note: str = DEFAULT_NOTE
    license_info: str = DEFAULT_LICENSE_INFO
    create_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return f"<Theme:[{self.name}],{self.base_size}px,{len(self.projects)}-curs>"

    def to_dict(self):
        data = {
            "name": self.name,
            "type": self.type.value,
            "id": self.id,
            "base_size": self.base_size,
            "author": self.author,
            "description": self.description,
            "projects": [project.to_dict() for project in self.projects],
            "create_time": self.create_time,
        }
        if self.note:
            data["note"] = self.note
        if self.license_info:
            data["license_info"] = self.license_info
        return data

    @staticmethod
    def from_dict(data: dict) -> 'CursorTheme':
        return CursorTheme(
            name=data["name"],
            type=ThemeType(data.get("type", ThemeType.NORMAL)),
            id=data["id"],
            base_size=data["base_size"],
            author=data["author"],
            description=data["description"],
            projects=[CursorProject.from_dict(project) for project in data["projects"]],
            note=data.get("note", ""),
            license_info=data.get("license_info", ""),
            create_time=data.get("create_time", "Unknow")
        )

    def copy(self):
        data = self.to_dict()
        data["id"] = generate_id()
        return self.from_dict(data)

    @property
    def make_time(self):
        return sum(project.make_time for project in self.projects)


@dataclass
class AssetSource:
    name: str
    id: str
    textures_zip: str
    recommend_file: str | None = None


class AssetSources(Enum):
    # MINECRAFT_1_21_5 = AssetSource("Minecraft 1.21.5",
    #                                "minecraft-textures-1.21.5",
    #                                r"assets/sources/1.21.5/textures.zip")
    MINECRAFT_25W32A = AssetSource("Minecraft 25w32a (1.21.9)",
                                   "minecraft-textures-25w32a",
                                   r"assets/sources/25w32a/textures.zip")

    DEFAULT = MINECRAFT_25W32A

    @staticmethod
    def get_source_by_id(target_id: str) -> AssetSource | None:
        for source_member in AssetSources.members().values():
            source = source_member.value
            assert isinstance(source, AssetSource)
            if target_id == source.id:
                return source
        raise ValueError(f"未找到id为 [{target_id}] 的素材源")

    @staticmethod
    def members() -> dict[str, 'AssetSources']:
        """这个函数过滤了DEFAULT项"""
        mem_iter = iter(AssetSources.__members__.items())
        result = {}
        while True:
            try:
                name, source = next(mem_iter)
            except StopIteration:
                break
            if name == "DEFAULT":
                continue
            result[name] = source
        return result

    @staticmethod
    def get_sources() -> list[AssetSource]:
        members = AssetSources.members()
        sources = list(member.value for member in members.values())
        return sources


@dataclass
class AssetsChoicerAssetInfo:
    frames: list[tuple[Image.Image, str]]
    source_id: str


source_load_manager = SourceLoadManager()

main_dir = DataDir(os.path.abspath(expandvars(config.data_dir)))
path_theme_cursors = main_dir.make_sub_dir("Theme Cursors")
path_theme_data = main_dir.make_sub_dir(r"Theme Data")
path_deleted_theme_data = main_dir.make_sub_dir(r"Deleted Theme Backup")
