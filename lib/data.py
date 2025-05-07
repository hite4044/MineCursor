import random
from collections import namedtuple
from dataclasses import dataclass, field
from enum import Enum

from PIL import Image

_Position = namedtuple("Position", ["x", "y"])
_Scale = namedtuple("Scale", ["x", "y"])
_Margins = namedtuple("Margins", ["left", "right", "up", "down"])


class Position(_Position):
    pass


class Scale2D(_Scale):
    pass


class Margins(_Margins):
    pass


@dataclass
class CursorElement:
    name: str
    frames: list[Image.Image]
    source_id: str = ""
    source_paths: list[str] = field(default_factory=list)
    position: Position = Position(0, 0)
    scale: Scale2D = Scale2D(1.0, 1.0)
    rotation: float = 0
    crop_margins: Margins = Margins(0, 0, 0, 0)
    reverse_x: bool = False
    reverse_y: bool = False
    resample: Image.Resampling = Image.Resampling.NEAREST
    animation_start: int = 0
    animation_length: int = 0
    final_rect: tuple[int, int, int, int] = (0, 0, 0, 0)

    # noinspection PyAttributeOutsideInit
    @property
    def id(self):
        if not hasattr(self, "id_raw"):
            self.id_raw = int.from_bytes(random.randbytes(4), "big")
        return self.id_raw

    def __hash__(self):
        return self.id

    def __str__(self):
        return f"<Element:{self.name} on {self.position}>"


class CursorProject:
    def __init__(self, name: str, canvas_size: tuple[int, int]):
        self.name = name
        self.elements: list[CursorElement] = []
        self.raw_canvas_size = canvas_size
        self.center_pos = Position(0, 0)
        self.scale = 1.0
        self.frame_count = -1
        self.ani_rate: int = 50
        self.resample: Image.Resampling = Image.Resampling.NEAREST

    @property
    def canvas_size(self):
        return int(self.raw_canvas_size[0] * self.scale), int(self.raw_canvas_size[1] * self.scale)

    def add_element(self, element: CursorElement):
        self.elements.insert(0, element)

@dataclass
class AssetSource:
    name: str
    id: str
    recommend_file: str
    textures_zip: str



class AssetSources(Enum):
    MINECRAFT_1_21_5 = AssetSource("Minecraft 1.21.5",
                                   "minecraft-textures-1.12.5",
                                   r"assets/sources/1.21.5/recommend.json",
                                   r"assets/sources/1.21.5/textures.zip")

@dataclass
class AssetInfo:
    frames: list[tuple[Image.Image, str]]
    source_id: str
