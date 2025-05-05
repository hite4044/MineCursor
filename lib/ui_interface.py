import inspect
from typing import Type, TypeVar

_T = TypeVar("_T")


def ui_class(cls: Type[_T]) -> Type[_T]:
    """
    寻找UI类对应的逻辑实现类, 找到即返回, 否则使用UI类

    例如:
    参数为 WindowUI 类, 如果任何调用者里有 Window 类, 则替换为该类
    """
    frame = inspect.currentframe()
    cls_name = cls.__name__.rstrip("UI")
    while True:
        frame = frame.f_back
        if frame is None:
            return cls
        if "__class__" in frame.f_locals and cls_name in frame.f_globals:
            return frame.f_globals[cls_name]
