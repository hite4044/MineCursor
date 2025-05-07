import winreg
from ctypes import windll
from dataclasses import dataclass
from enum import Enum

from win32con import IMAGE_CURSOR, LR_LOADFROMFILE, OCR_NORMAL, OCR_APPSTARTING, OCR_WAIT, OCR_CROSS, OCR_IBEAM, OCR_NO, \
    OCR_SIZENS, OCR_SIZEWE, OCR_SIZENWSE, OCR_SIZENESW, OCR_UP, OCR_HAND
from win32gui import LoadImage

OCR_HELP = 32651
OCR_PIN = 32671
OCR_PERSON = 32672
SetSystemCursor = windll.user32.SetSystemCursor
SYS_CUR_ROOT = r"%SystemRoot%\cursors\aero_"

@dataclass
class RegPath:
    h_key: int
    path: str


SYSTEM_SCHEMES = RegPath(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Control Panel\Cursors")
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
    TEXT = "IBean"
    PEN = "NWPen"
    NO = "No"
    SIZE_SN = "SizeSN"
    SIZE_WE = "SizeWE"
    SIZE_NW_SE = "SizeNWSE"
    SIZE_NE_SW = "SizeNESW"
    UP_ARROW = "UpArrow"
    HAND = "Hand"
    PIN = "Pin"
    PERSON = "Person"


class CursorData:
    def __init__(self, system_default: str, reg_key: CursorKind, cursor_kind: int):
        if system_default == "":
            self.cursor_path = ""
        else:
            self.cursor_path = SYS_CUR_ROOT + system_default
        self.reg_key = reg_key
        self.cursor_kind = cursor_kind

    def set_path(self, path: str):
        self.cursor_path = path



@dataclass
class CursorPaths:
    arrow: CursorData = CursorData("arrow.cur", CursorKind.ARROW, OCR_NORMAL)
    help: CursorData = CursorData("helpsel.cur", CursorKind.HELP, OCR_HELP)
    app_starting: CursorData = CursorData("working.ani", CursorKind.APP_STARTING, OCR_APPSTARTING)
    wait: CursorData = CursorData("busy.ani", CursorKind.WAIT, OCR_WAIT)
    cross_hair: CursorData = CursorData("", CursorKind.CROSS_HAIR, OCR_CROSS)
    text: CursorData = CursorData("", CursorKind.TEXT, OCR_IBEAM)  # 注册表名称: IBean
    pen: CursorData = CursorData("pen.cur", CursorKind.PEN, -1)
    no: CursorData = CursorData("unavail.cur", CursorKind.NO, OCR_NO)
    size_sn: CursorData = CursorData("ns.cur", CursorKind.SIZE_SN, OCR_SIZENS)
    size_we: CursorData = CursorData("ew.cur", CursorKind.SIZE_WE, OCR_SIZEWE)
    size_nw_se: CursorData = CursorData("nwse.cur", CursorKind.SIZE_NW_SE, OCR_SIZENWSE)
    size_ne_sw: CursorData = CursorData("nesw.cur", CursorKind.SIZE_NE_SW, OCR_SIZENESW)
    up_arrow: CursorData = CursorData("up.cur", CursorKind.UP_ARROW, OCR_UP)
    hand: CursorData = CursorData("link.cur", CursorKind.HAND, OCR_HAND)  # 链接选择
    pin: CursorData = CursorData("pin.cur", CursorKind.PIN, OCR_PIN)  # 位置选择
    person: CursorData = CursorData("person.cur", CursorKind.PERSON, OCR_PERSON)  # 个人选择


def set_cursor(cursor_paths: CursorPaths, scheme_type: SchemesType, scheme_name: str, cursor_size: int) -> bool:
    cursor_root = scheme_type.value
    try:
        global_set = winreg.OpenKey(cursor_root.h_key, cursor_root.path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
        schemes_set = winreg.OpenKey(cursor_root.h_key, cursor_root.path + r"\Schemes", 0,
                                     winreg.KEY_READ | winreg.KEY_WRITE)

        # 设置 鼠标指针文件 的路径
        cursor_datas: list[CursorData] = list(getattr(cursor_paths, "__dataclass_fields__").values())
        for cursor_data in cursor_datas:
            winreg.SetValueEx(global_set, cursor_data.reg_key.value, 0, winreg.REG_SZ, cursor_data.cursor_path)

        # 设置 鼠标主题 包含的鼠标指针 的路径
        if winreg.QueryValueEx(schemes_set, scheme_name) != (scheme_name, None):
            winreg.DeleteValue(schemes_set, scheme_name)
        path_text = ",".join([data.cursor_path for data in cursor_datas])
        winreg.SetValueEx(schemes_set, scheme_name, 0, winreg.REG_EXPAND_SZ, path_text)

        # 设置当前使用主题
        winreg.SetValueEx(global_set, None, 0, winreg.REG_SZ, scheme_name)

        # 设置鼠标大小
        winreg.SetValueEx(global_set, "CursorBaseSize", 0, winreg.REG_DWORD, cursor_size)

        for cursor_data in cursor_datas:
            cursor = LoadImage(None, cursor_data.cursor_path, IMAGE_CURSOR, 32, 32, LR_LOADFROMFILE)
            SetSystemCursor(cursor, cursor_data.cursor_kind)
    except OSError:
        return False
    return True
