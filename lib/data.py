from lib.datas.data_dir import *
from lib.datas.project import *
from lib.datas.source import *
from lib.datas.theme import *

pass  # 占位置让IDE不重新排序

from lib.datas.base_struct import *


@dataclass
class AssetsChoicerAssetInfo:
    frames: list[tuple[Image.Image, str]]
    source_id: str


just_keep_import = [
    CursorProject,
    CursorElement,
    AssetSource,
    Position,
    main_dir
]
