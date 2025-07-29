import winreg
from ctypes import windll
from dataclasses import dataclass
from enum import Enum
from os.path import expandvars, basename
from winreg import HKEYType

from win32con import IMAGE_CURSOR, LR_LOADFROMFILE, OCR_NORMAL, OCR_APPSTARTING, OCR_WAIT, OCR_CROSS, OCR_IBEAM, OCR_NO, \
    OCR_SIZENS, OCR_SIZEWE, OCR_SIZENWSE, OCR_SIZENESW, OCR_UP, OCR_HAND, OCR_SIZEALL, IDC_ARROW, IDC_HELP, \
    IDC_APPSTARTING, IDC_WAIT, IDC_CROSS, IDC_IBEAM, IDC_SIZENS, IDC_NO, IDC_HAND, IDC_UPARROW, IDC_SIZEWE, \
    IDC_SIZENESW, IDC_SIZEALL
from win32gui import LoadImage, LoadCursor, CopyIcon, LR_DEFAULTSIZE

from lib.log import logger

OCR_HELP = 32651
OCR_PIN = 32671
OCR_PERSON = 32672
SetSystemCursor = windll.user32.SetSystemCursor
SYS_CUR_ROOT = expandvars(r"%SystemRoot%\cursors\aero_")


@dataclass
class RegPath:
    h_key: int
    path: str


SYSTEM_SCHEMES = RegPath(winreg.HKEY_LOCAL_MACHINE,
                         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Control Panel\Cursors\Default")

USER_SCHEMES = RegPath(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors")


class SchemesType(Enum):
    SYSTEM = SYSTEM_SCHEMES
    USER = USER_SCHEMES


class CursorKind(Enum):
    ARROW = "Arrow"
    HELP = "Help"
    APP_STARTING = "AppStarting"
    WAIT = "Wait"
    CROSS_HAIR = "Crosshair"
    TEXT = "IBeam"
    PEN = "NWPen"
    NO = "No"
    SIZE_SN = "SizeNS"
    SIZE_WE = "SizeWE"
    SIZE_NW_SE = "SizeNWSE"
    SIZE_NE_SW = "SizeNESW"
    SIZE_ALL = "SizeAll"
    UP_ARROW = "UpArrow"
    LINK = "Hand"
    PIN = "Pin"
    PERSON = "Person"

    @property
    def kind_name(self):
        return CURSOR_KIND_NAME_OFFICIAL[self]


CURSOR_KIND_NAME_OFFICIAL: dict[CursorKind, str] = {
    CursorKind.ARROW: "正常选择",
    CursorKind.HELP: "帮助选择",
    CursorKind.APP_STARTING: "后台运行",
    CursorKind.WAIT: "忙",
    CursorKind.CROSS_HAIR: "精确选择",
    CursorKind.TEXT: "文本选择",
    CursorKind.PEN: "手写",
    CursorKind.NO: "不可用",
    CursorKind.SIZE_SN: "垂直调整大小",
    CursorKind.SIZE_WE: "水平调整大小",
    CursorKind.SIZE_NW_SE: "沿对角线调整大小 1",
    CursorKind.SIZE_NE_SW: "沿对角线调整大小 2",
    CursorKind.SIZE_ALL: "移动",
    CursorKind.UP_ARROW: "候选",
    CursorKind.LINK: "链接选择",
    CursorKind.PIN: "位置选择",
    CursorKind.PERSON: "个人选择"
}
CURSOR_KIND_NAME_CUTE: dict[CursorKind, str] = {
    CursorKind.ARROW: "正常",
    CursorKind.HELP: "帮助",
    CursorKind.APP_STARTING: "悄悄运行",
    CursorKind.WAIT: "卡了",
    CursorKind.CROSS_HAIR: "盯帧选择",
    CursorKind.TEXT: "请输入文本",
    CursorKind.PEN: "不用手的手写",
    CursorKind.NO: "哒咩",
    CursorKind.SIZE_SN: "变高",
    CursorKind.SIZE_WE: "变长",
    CursorKind.SIZE_NW_SE: "↖向左变大变高",
    CursorKind.SIZE_NE_SW: "↗向右变大变高",
    CursorKind.SIZE_ALL: "瞬移",
    CursorKind.UP_ARROW: "举起手来！",
    CursorKind.LINK: "戳一下",
    CursorKind.PIN: "在哪里?",
    CursorKind.PERSON: "你自己"
}
CURSOR_IDC_MAP: dict[CursorKind, int] = {
    CursorKind.ARROW: IDC_ARROW,
    CursorKind.HELP: IDC_HELP,
    CursorKind.APP_STARTING: IDC_APPSTARTING,
    CursorKind.WAIT: IDC_WAIT,
    CursorKind.CROSS_HAIR: IDC_CROSS,
    CursorKind.TEXT: IDC_IBEAM,
    CursorKind.NO: IDC_NO,
    CursorKind.SIZE_SN: IDC_SIZENS,
    CursorKind.SIZE_WE: IDC_SIZEWE,
    CursorKind.SIZE_NW_SE: IDC_SIZENESW,
    CursorKind.SIZE_NE_SW: IDC_SIZENESW,
    CursorKind.SIZE_ALL: IDC_SIZEALL,
    CursorKind.UP_ARROW: IDC_UPARROW,
    CursorKind.LINK: IDC_HAND,
}


class CursorData:
    def __init__(self, system_default: str, kind: CursorKind, cursor_kind: int):
        if system_default == "":
            self.cursor_path = ""
        else:
            self.cursor_path = SYS_CUR_ROOT + system_default
        self.is_default = True
        self.kind = kind
        self.ocr_con = cursor_kind

    def set_path(self, path: str):
        self.cursor_path = path
        self.is_default = False


# noinspection SpellCheckingInspection
@dataclass
class CursorsInfo:
    def __init__(self, use_aero: bool = True):
        self.use_aero = use_aero

        self.arrow: CursorData = CursorData("arrow.cur", CursorKind.ARROW, OCR_NORMAL)
        self.help: CursorData = CursorData("helpsel.cur", CursorKind.HELP, OCR_HELP)
        self.app_starting: CursorData = CursorData("working.ani", CursorKind.APP_STARTING, OCR_APPSTARTING)
        self.wait: CursorData = CursorData("busy.ani", CursorKind.WAIT, OCR_WAIT)
        self.cross_hair: CursorData = CursorData("", CursorKind.CROSS_HAIR, OCR_CROSS)
        self.text: CursorData = CursorData("", CursorKind.TEXT, OCR_IBEAM)  # 注册表名称: IBeam
        self.pen: CursorData = CursorData("pen.cur", CursorKind.PEN, -1)
        self.no: CursorData = CursorData("unavail.cur", CursorKind.NO, OCR_NO)
        self.size_sn: CursorData = CursorData("ns.cur", CursorKind.SIZE_SN, OCR_SIZENS)
        self.size_we: CursorData = CursorData("ew.cur", CursorKind.SIZE_WE, OCR_SIZEWE)
        self.size_nw_se: CursorData = CursorData("nwse.cur", CursorKind.SIZE_NW_SE, OCR_SIZENWSE)
        self.size_ne_sw: CursorData = CursorData("nesw.cur", CursorKind.SIZE_NE_SW, OCR_SIZENESW)
        self.size_all: CursorData = CursorData("move.cur", CursorKind.SIZE_ALL, OCR_SIZEALL)
        self.up_arrow: CursorData = CursorData("up.cur", CursorKind.UP_ARROW, OCR_UP)
        self.hand: CursorData = CursorData("link.cur", CursorKind.LINK, OCR_HAND)  # 链接选择
        self.pin: CursorData = CursorData("pin.cur", CursorKind.PIN, OCR_PIN)  # 位置选择
        self.person: CursorData = CursorData("person.cur", CursorKind.PERSON, OCR_PERSON)  # 个人选择
        self.field_names = [
            "arrow",
            "help",
            "app_starting",
            "wait",
            "cross_hair",
            "text",
            "pen",
            "no",
            "size_sn",
            "size_we",
            "size_nw_se",
            "size_ne_sw",
            "size_all",
            "up_arrow",
            "hand",
            "pin",
            "person",
        ]


CR_INFO_FIELD_MAP = {
    CursorKind.ARROW: "arrow",
    CursorKind.HELP: "help",
    CursorKind.APP_STARTING: "app_starting",
    CursorKind.WAIT: "wait",
    CursorKind.CROSS_HAIR: "cross_hair",
    CursorKind.TEXT: "text",
    CursorKind.PEN: "pen",
    CursorKind.NO: "no",
    CursorKind.SIZE_SN: "size_sn",
    CursorKind.SIZE_WE: "size_we",
    CursorKind.SIZE_NW_SE: "size_nw_se",
    CursorKind.SIZE_NE_SW: "size_ne_sw",
    CursorKind.SIZE_ALL: "size_all",
    CursorKind.UP_ARROW: "up_arrow",
    CursorKind.LINK: "hand",
    CursorKind.PIN: "pin",
    CursorKind.PERSON: "person",
}


def set_cursors_progress(cursors_info: CursorsInfo, scheme_type: SchemesType, scheme_name: str, scheme_id: str,
                         cursor_size: int, raw_size: bool):
    cursor_root = scheme_type.value
    full_name = f"&MineCursor_{scheme_id}_{scheme_name}"
    try:
        global_set = winreg.OpenKey(cursor_root.h_key, cursor_root.path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
        schemes_set = winreg.CreateKeyEx(cursor_root.h_key, cursor_root.path + r"\Schemes", 0,
                                         winreg.KEY_READ | winreg.KEY_WRITE)

        now_schemes = get_schemes(schemes_set)
        if scheme_id in now_schemes:
            winreg.DeleteValue(schemes_set, now_schemes[scheme_id])

        # 设置 鼠标指针文件 的路径
        cursor_datas: list[CursorData] = [getattr(cursors_info, field_name) for field_name in cursors_info.field_names]

        # 设置 鼠标主题 包含的鼠标指针 的路径
        path_text = ",".join([data.cursor_path for data in cursor_datas])
        winreg.SetValueEx(schemes_set, full_name, 0, winreg.REG_EXPAND_SZ, path_text)

        # 设置当前使用主题
        winreg.SetValueEx(global_set, None, 0, winreg.REG_SZ, full_name)

        # 设置鼠标大小
        winreg.SetValueEx(global_set, "CursorBaseSize", 0, winreg.REG_DWORD, cursor_size)
        winreg.SetValueEx(global_set, "Scheme Source", 0, winreg.REG_DWORD, 1)

        for i, cursor_data in enumerate(cursor_datas):
            yield f"设置指针 [{cursor_data.kind.name}]", i
            logger.info(f"设置 {cursor_data.kind.value} 为 {basename(cursor_data.cursor_path)}")
            if cursor_data.ocr_con == -1:
                continue
            if not cursors_info.use_aero and cursor_data.is_default:
                cursor = LoadCursor(None, CURSOR_IDC_MAP.get(cursor_data.kind, IDC_ARROW))
                CopyIcon(cursor)
                path = ""
            else:
                if raw_size:
                    cursor = LoadImage(None, cursor_data.cursor_path, IMAGE_CURSOR, cursor_size, cursor_size, LR_LOADFROMFILE)
                else:
                    cursor = LoadImage(None, cursor_data.cursor_path, IMAGE_CURSOR, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
                path = cursor_data.cursor_path
            winreg.SetValueEx(global_set, cursor_data.kind.value, 0, winreg.REG_EXPAND_SZ, path)
            logger.debug(f"指针句柄: {cursor}")
            ret = SetSystemCursor(cursor, cursor_data.ocr_con)
            if ret == 0:
                logger.error(f"设置 {cursor_data.kind.value} 失败")
    except OSError:
        yield False, -1
    yield True, -1


def get_schemes(reg_key: HKEYType | int) -> dict[str, str]:
    schemes: dict[str, str] = {}
    index = 0
    first_name = None
    while True:
        try:
            value_name, value, _ = winreg.EnumValue(reg_key, index)
            if first_name is None:
                first_name = value_name
            if value_name == first_name:
                break
            if not value_name.startswith("&MineCursor_"):
                continue
            if not len(value_name.split("_")) == 3:
                continue
            parts = value_name.split("_")
            theme_id = parts[1]
            theme_name = value_name
            schemes[theme_id] = theme_name
            index += 1
        except OSError:
            break
    return schemes
