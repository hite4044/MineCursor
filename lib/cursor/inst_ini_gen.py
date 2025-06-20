from lib.cursor.setter import CursorKind, CURSOR_KIND_NAME_OFFICIAL
from lib.data import CursorTheme

VAR_NAME_MAP: dict[CursorKind, str] = {
    CursorKind.ARROW: "pointer",
    CursorKind.HELP: "help",
    CursorKind.APP_STARTING: "work",
    CursorKind.WAIT: "busy",
    CursorKind.CROSS_HAIR: "cross",
    CursorKind.TEXT: "text",
    CursorKind.PEN: "hand",
    CursorKind.NO: "unavailable",
    CursorKind.SIZE_SN: "vert",
    CursorKind.SIZE_WE: "horz",
    CursorKind.SIZE_NW_SE: "dgn1",
    CursorKind.SIZE_NE_SW: "dgn2",
    CursorKind.SIZE_ALL: "move",
    CursorKind.UP_ARROW: "alternate",
    CursorKind.LINK: "link",
    CursorKind.PIN: "loc",
    CursorKind.PERSON: "person"
}


class INIPart:
    @staticmethod
    def get_text(*args) -> str:
        pass


class PartVersion(INIPart):
    @staticmethod
    def get_text() -> str:
        return "\n".join([
            '[Version]',
            'signature="$CHICAGO$"'
        ])


class PartDefaultInstall(INIPart):
    @staticmethod
    def get_text() -> str:
        return "\n".join([
            '[DefaultInstall]',
            'CopyFiles = Scheme.Cur, Scheme.Txt',
            'AddReg    = Scheme.Reg'
        ])


class PartDestinationDirs(INIPart):
    @staticmethod
    def get_text() -> str:
        return "\n".join([
            '[DestinationDirs]',
            'Scheme.Cur = 10,%CUR_DIR%',
            'Scheme.Txt = 10,%CUR_DIR%'
        ])


class PartSchemeReg(INIPart):
    @staticmethod
    def get_text(available_kinds: list[CursorKind]):
        scheme_paths = []
        for kind in CursorKind:
            if kind in available_kinds:
                scheme_paths.append(f"%10%\%CUR_DIR%\%{VAR_NAME_MAP[kind]}%")
            else:
                scheme_paths.append('')
        return "\n".join(
            [
                '[Scheme.Reg]',
                'HKCU,"Control Panel\Cursors\Schemes","%SCHEME_NAME%",,' + \
                ('"' + (",".join(scheme_paths)) + '"'),

                r'HKLM,"SOFTWARE\Microsoft\Windows\CurrentVersion\Runonce\Setup\","",,"rundll32.exe shell32.dll,Control_RunDLL main.cpl,,1"'
            ]
        )

class PartSchemeCur(INIPart):
    @staticmethod
    def get_text(file_map: dict[CursorKind, str]):
        return "\n".join([
            '[Scheme.Cur]',
            *[f'"{filename}"     ; {CURSOR_KIND_NAME_OFFICIAL[kind]}' for kind, filename in file_map.items()]
        ])


class PartString(INIPart):
    @staticmethod
    def get_text(theme: CursorTheme, file_map: dict[CursorKind, str]):
        return "\n".join([
            '[Strings]',
            rf'CUR_DIR = "Cursors\{theme.name}"',
            f"SCHEME_NAME = {theme.name}",
            *[f'{VAR_NAME_MAP[kind]} = "{filename}"     ; {CURSOR_KIND_NAME_OFFICIAL[kind]}' for kind, filename in file_map.items()]
        ])

class CursorInstINIGenerator:
    @staticmethod
    def generate(theme: CursorTheme, file_map: dict[CursorKind, str]):
        return "\n\n".join([
            PartVersion.get_text(),
            PartDefaultInstall.get_text(),
            PartDestinationDirs.get_text(),
            PartSchemeReg.get_text(list(file_map.keys())),
            PartSchemeCur.get_text(file_map),
            PartString.get_text(theme, file_map)
        ])

