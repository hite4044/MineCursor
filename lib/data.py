import os.path
import random
from base64 import b64encode, b64decode
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from os import makedirs
from os.path import expandvars, join
from typing import Any, cast
from zipfile import ZipFile

from PIL import Image

from lib.cursor.setter import CursorKind


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


class WorkFileManager:
    def __init__(self, path: str):
        app_data_roaming = expandvars("%APPDATA%")
        app_data, _ = os.path.split(app_data_roaming)
        self.work_dir = join(app_data, path)
        makedirs(self.work_dir, exist_ok=True)

    def make_work_dir(self, name: str) -> str:
        makedirs(join(self.work_dir, name))
        return join(self.work_dir, name)


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


class AssetSourceInfo:
    def __init__(self, type_: AssetType,
                 source_id: str | None = None,
                 source_path: str | None = None,

                 size: tuple[int, int] | None = None,
                 color: tuple[int, int, int] | tuple[int, int, int, int] | None = None, ):
        self.type: AssetType = type_
        self.source_id: str = source_id
        self.source_path: str = source_path

        self.size = size
        self.color = color

    def to_dict(self):
        return {
            "type": self.type.value,
            "source_id": self.source_id,
            "source_path": self.source_path,
            **({"size": self.size, "color": self.color} if self.size else {})
        }

    @staticmethod
    def from_dict(data: dict):
        return AssetSourceInfo(
            type_=AssetType(data["type"]),
            source_id=data["source_id"],
            source_path=data["source_path"],
            **({"size": data["size"], "color": data["color"]} if "size" in data else {})
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
                 resample: Image.Resampling = Image.Resampling.NEAREST):
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
        self.resample: Image.Resampling = resample
        self.mask: Image.Image | None = None

        self.enable_key_ani: bool = False
        self.animation_key_data: AnimationKeyData = AnimationKeyData()
        self.animation_start_offset: int = 0  # 元素在XX帧开始显示并播放播放
        self.loop_animation: bool = True
        self.reverse_animation: bool = False
        self.animation_data: list[AnimationFrameData] = [AnimationFrameData() for _ in range(len(frames))]
        self.animation_data_index: list[int] = []
        self.proc_step = DEFAULT_PROC_ORDER
        self.final_rect = (0, 0, 16, 16)
        self.final_image = None
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
        last_frame = 0
        while True:
            data = self.animation_data[index]
            timer_frame += data.frame_delay
            index += 1
            if index >= len(self.animation_data):
                index = 0
                if frame == last_frame:
                    raise RuntimeError("不对劲, 动画无限循环了")
                last_frame = frame
            if timer_frame > target_frame:
                return frame
            frame += data.index_increment

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
            resample=Image.Resampling(data["resample"])
        )
        if "mask" in data:
            if isinstance(data["mask"][1], bytes):
                element.mask = Image.frombytes("L", data["mask"][0], data["mask"][1])
            else:
                element.mask = Image.frombytes("L", data["mask"][0], b64decode(data["mask"][1]))
        element.animation_start_offset = data.get("animation_start_offset", element.animation_start_offset)
        element.loop_animation = data.get("loop_animation", element.loop_animation)
        element.reverse_animation = data.get("reverse_animation", element.reverse_animation)
        element.animation_key_data = AnimationKeyData.load(data["animation_key_data"])
        element.animation_data = [AnimationFrameData.load(data) for data in data["animation_data"]]
        element.proc_step = [ProcessStep(step) for step in data["proc_step"]]
        element.reverse_way = ReverseWay(data.get("reverse_way", ReverseWay.BOTH.value))

        for source_info in element.source_infos:
            frame = source_info.load_frame()
            element.frames.append(frame)

        element.build_animation_index()
        return element

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
        self.scale = 1.0
        self.resample: Image.Resampling = Image.Resampling.NEAREST
        self.is_ani_cursor = False
        self.frame_count = 20
        self.ani_rate: int = 6
        self.ani_rates: list[int] | None = None

        self.id: str = generate_id(2)

    @property
    def frame_delay(self) -> int:
        return self.ani_rate * 1000 // 60

    @property
    def canvas_size(self) -> tuple[int, int]:
        return int(self.raw_canvas_size[0] * self.scale), int(self.raw_canvas_size[1] * self.scale)

    def add_element(self, element: CursorElement):
        self.elements.insert(0, element)

    def __str__(self):
        return f"<Project:[{self.name}]>"

    def to_dict(self):
        return {
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
        }

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
        return project

    def copy(self) -> 'CursorProject':
        return CursorProject.from_dict(self.to_dict())


@dataclass()
class CursorTheme:
    name: str
    base_size: int = 32
    author: str = "Unknow"
    description: str = "None"
    projects: list[CursorProject] = field(default_factory=list)

    id: str = field(default_factory=generate_id)

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return f"<Theme:[{self.name}],{self.base_size}px,{len(self.projects)}-curs>"

    def to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "base_size": self.base_size,
            "author": self.author,
            "description": self.description,
            "projects": [project.to_dict() for project in self.projects],
        }

    @staticmethod
    def from_dict(data: dict) -> 'CursorTheme':
        return CursorTheme(
            name=data["name"],
            id=data["id"],
            base_size=data["base_size"],
            author=data["author"],
            description=data["description"],
            projects=[CursorProject.from_dict(project) for project in data["projects"]],
        )


@dataclass
class AssetSource:
    name: str
    id: str
    recommend_file: str
    textures_zip: str


class AssetSources(Enum):
    MINECRAFT_1_21_5 = AssetSource("Minecraft 1.21.5",
                                   "minecraft-textures-1.21.5",
                                   r"assets/sources/1.21.5/recommend.json",
                                   r"assets/sources/1.21.5/textures.zip")

    @staticmethod
    def get_source_by_id(target_id: str) -> AssetSource | None:
        for source in AssetSources.__members__.values():
            assert isinstance(source, AssetSources)
            if target_id == source.value.id:
                return source.value
        raise ValueError(f"未找到id为{target_id}的素材源")


@dataclass
class AssetsChoicerAssetInfo:
    frames: list[tuple[Image.Image, str]]
    source_id: str


source_load_manager = SourceLoadManager()
cursors_file_manager = WorkFileManager(r"Mine Cursor\Theme Cursors")
data_file_manager = WorkFileManager(r"Mine Cursor\Theme Data")
