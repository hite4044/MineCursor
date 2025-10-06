import random
import re
from dataclasses import dataclass as dataclass_t
from enum import Enum
from typing import Any

INVALID_FILENAME_CHAR = re.compile(r'[<>:"/\\|?*]')


def generate_id(length: int = 4):
    return hex(int.from_bytes(random.randbytes(length), "big"))[2:]


class DataClassStructMixin:
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
    def load(cls, data: list | dict[str, Any]):
        if isinstance(data, dict):
            return cls(**data)
        else:
            return cls(*data)

    def __getitem__(self, item):
        field_names = list(getattr(self, "__dataclass_fields__").keys())
        return getattr(self, field_names[item])


class ThemeType(Enum):
    """主题类型"""
    NORMAL = 0  # 普通
    PRE_DEFINE = 1  # 用作选配
    TEMPLATE = 2  # 用作模版


class AssetType(Enum):
    """源信息类型"""
    ZIP_FILE = 0  # 素材源里的文件
    RECT = 1  # 矩形
    IMAGE = 2  # 图像
    # tip: 子项目类型将不会使用源信息


@dataclass_t
class Position(DataClassStructMixin):
    x: int
    y: int


@dataclass_t
class Scale2D(DataClassStructMixin):
    x: float
    y: float


@dataclass_t
class Margins(DataClassStructMixin):
    left: int
    right: int
    up: int
    down: int


@dataclass_t
class AnimationKeyData(DataClassStructMixin):
    frame_start: int = 0
    frame_inv: int = 1
    frame_length: int = 1


@dataclass_t
class AnimationFrameData(DataClassStructMixin):
    index_increment: int = 1
    frame_delay: int = 1


class ProcessStep(Enum):
    TRANSPOSE = 1
    CROP = 2
    SCALE = 3
    ROTATE = 4


class ReverseWay(Enum):
    X_FIRST = 0
    Y_FIRST = 1
    BOTH = 2


DEFAULT_PROC_ORDER = (ProcessStep.TRANSPOSE, ProcessStep.CROP, ProcessStep.SCALE, ProcessStep.ROTATE)
