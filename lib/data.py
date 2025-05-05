import random
from collections import namedtuple
from dataclasses import dataclass

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
    source_path: str
    source_name: str
    frames: list[Image.Image]
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
