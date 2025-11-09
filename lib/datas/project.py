from base64 import b64encode, b64decode
from datetime import datetime
from io import BytesIO
from typing import cast

from PIL import Image

from lib.cursor.setter import CursorKind
from lib.datas.base_struct import *
from lib.datas.source import AssetSourceInfo


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
        self.allow_mask_scale = False
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
        if self.allow_mask_scale:
            data["allow_mask_scale"] = self.allow_mask_scale
        if self.mask:
            mask_io = BytesIO()
            self.mask.save(mask_io, format="PNG")
            data["mask"] = (self.mask.size, b64encode(mask_io.getbuffer()).decode("utf-8"))
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
                mask_io = BytesIO(b64decode(data["mask"][1]))
                if mask_io.read(8) == b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A":
                    mask_io.seek(0)
                    element.mask = Image.open(mask_io)
                else:
                    mask_io.seek(0)
                    element.mask = Image.frombytes("L", data["mask"][0], mask_io.getvalue())
        element.mask_color = tuple(data.get("mask_color")) if data.get("mask_color") else None
        element.animation_start_offset = data.get("animation_start_offset", element.animation_start_offset)
        element.loop_animation = data.get("loop_animation", element.loop_animation)
        element.reverse_animation = data.get("reverse_animation", element.reverse_animation)
        element.animation_key_data = AnimationKeyData.load(data["animation_key_data"])
        element.animation_data = [AnimationFrameData.load(data) for data in data["animation_data"]]
        element.proc_step = [ProcessStep(step) for step in data["proc_step"]]
        element.reverse_way = ReverseWay(data.get("reverse_way", ReverseWay.BOTH.value))
        element.allow_mask_scale = data.get("allow_mask_scale", False)
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
    def real_ani_rates(self) -> list[int]:
        if not self.ani_rates:
            return [self.ani_rate for _ in range(self.frame_count)]
        ani_rates = self.ani_rates.copy()
        if len(ani_rates) > self.frame_count:
            for _ in range(len(ani_rates) - self.frame_count):
                ani_rates.pop(-1)
        elif len(ani_rates) < self.frame_count:
            ani_rates.extend(([self.ani_rate] * (self.frame_count - len(ani_rates))))
        assert len(ani_rates) == self.frame_count
        return ani_rates

    @property
    def frame_delay(self) -> int:
        return self.ani_rate * 1000 // 60

    @property
    def canvas_size(self) -> tuple[int, int]:
        return int(self.raw_canvas_size[0] * self.scale), int(self.raw_canvas_size[1] * self.scale)

    def add_element(self, element: CursorElement):
        self.elements.insert(0, element)

    @property
    def friendly_name(self) -> str:
        return self.name if self.name else (self.external_name if self.external_name else self.kind.kind_name)

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
