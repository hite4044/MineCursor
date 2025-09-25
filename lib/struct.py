# 我真的服了, 循环导入太难解决了
from enum import Enum


class ThemeType(Enum):
    NORMAL = 0  # 普通
    PRE_DEFINE = 1  # 用作选配
    TEMPLATE = 2  # 用作模版
