import random
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from typing import Any
from zipfile import ZipFile

from PIL import Image

from lib.cursor_setter import CursorKind


class DataClassSaveLoadMixin:
    def save(self) -> list[Any]:
        field_names = getattr(self, "__dataclass_fields__").keys()
        fields = []
        for field_name in field_names:
            fields.append(getattr(self, field_name))
        return fields

    # noinspection PyArgumentList
    @classmethod
    def load(cls, data: list[Any]):
        return cls(*data)

    def __getitem__(self, item):
        field_names = list(getattr(self, "__dataclass_fields__").keys())
        return getattr(self, field_names[item])


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
                 source_id: str,
                 source_path: str,

                 size: tuple[int, int] | None = None,
                 color: tuple[int, int, int] | tuple[float, float, float] | None = None, ):
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


class ProcessStep(Enum):
    TRANSPOSE = 1
    CROP = 2
    SCALE = 3
    ROTATE = 4


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
                 position: Position = Position(0, 0),
                 scale: Scale2D = Scale2D(1.0, 1.0),
                 rotation: float = 0,
                 crop_margins: Margins = Margins(0, 0, 0, 0),
                 reverse_x: bool = False,
                 reverse_y: bool = False,
                 resample: Image.Resampling = Image.Resampling.NEAREST):
        if source_infos is None:
            source_infos = []
        self.name: str = name
        self.frames: list[Image.Image] = frames
        self.source_infos: list[AssetSourceInfo] = source_infos
        self.position: Position = position
        self.scale: Scale2D = scale
        self.rotation: float = rotation
        self.crop_margins: Margins = crop_margins
        self.reverse_x: bool = reverse_x
        self.reverse_y: bool = reverse_y
        self.resample: Image.Resampling = resample

        self.enable_key_ani: bool = False
        self.animation_key_data: AnimationKeyData = AnimationKeyData()
        self.animation_start_offset: int = 0
        self.animation_data: list[AnimationFrameData] = [AnimationFrameData() for _ in range(len(frames))]
        self.animation_data_index: list[int] = []
        self.proc_step = DEFAULT_PROC_ORDER
        self.final_rect = (0, 0, 0, 0)
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

    def to_dict(self):
        return {
            "name": self.name,
            "source_infos": [source_info.to_dict() for source_info in self.source_infos],
            "position": self.position.save(),
            "scale": self.scale.save(),
            "rotation": self.rotation,
            "crop_margins": self.crop_margins.save(),
            "reverse_x": self.reverse_x,
            "reverse_y": self.reverse_y,
            "resample": self.resample.value,
            "animation_start_offset": self.animation_start_offset,
            "animation_key_data": self.animation_key_data.save(),
            "animation_data": [data.save() for data in self.animation_data],
            "proc_step": [step.value for step in self.proc_step],
        }

    @staticmethod
    def from_dict(data: dict):
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
        element.animation_key_data = AnimationKeyData.load(data["animation_key_data"])
        element.animation_data = [AnimationFrameData.load(data) for data in data["animation_data"]]
        element.proc_step = [ProcessStep(step) for step in data["proc_step"]]

        active_sources: dict[str, ZipFile] = {}
        print(element.source_infos)
        for source_info in element.source_infos:
            if source_info.type == AssetType.ZIP_FILE:
                if source_info.source_id not in active_sources:
                    source = AssetSources.get_source_by_id(source_info.source_id)
                    active_sources[source_info.source_id] = ZipFile(source.textures_zip)
                current_source = active_sources[source_info.source_id]
                image_bytes = current_source.read(source_info.source_path)
                image_io = BytesIO(image_bytes)
                frame = Image.open(image_io)

            elif source_info.type == AssetType.RECT:
                frame = Image.new("RGBA", source_info.size, source_info.color)

            else:
                raise NotImplementedError
            element.frames.append(frame)

        element.build_animation_index()
        return element

    def __hash__(self):
        return self.id

    def __str__(self):
        return f"<Element:{self.name} at {self.position}>"


class CursorProject:
    def __init__(self, name: str, canvas_size: tuple[int, int]):
        self.name = name
        self.raw_canvas_size = canvas_size
        self.external_name: str | None = None
        self.kind: CursorKind = CursorKind.ARROW
        self.elements: list[CursorElement] = []
        self.center_pos = Position(0, 0)
        self.scale = 1.0
        self.resample: Image.Resampling = Image.Resampling.NEAREST
        self.is_ani_cursor = False
        self.frame_count = 20
        self.ani_rate: int = 50

    @property
    def canvas_size(self):
        return int(self.raw_canvas_size[0] * self.scale), int(self.raw_canvas_size[1] * self.scale)

    def add_element(self, element: CursorElement):
        self.elements.insert(0, element)

    def __str__(self):
        return f"<Project:{self.name}>"


@dataclass()
class CursorTheme:
    name: str
    base_size: int = 32
    author: str = "Unknow"
    description: str = "None"
    projects: list[CursorProject] = field(default_factory=list)

    rt_id: str = field(default_factory=lambda: int.from_bytes(random.randbytes(4), "big"))

    def __hash__(self):
        return self.rt_id


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
