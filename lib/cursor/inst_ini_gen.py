from lib.cursor.setter import CursorKind, CURSOR_KIND_NAME_OFFICIAL
from lib.data import CursorTheme


def pri_tuple_fmt_time(seconds: float) -> tuple[int, int, int, int]:
    """转化时间戳至时间元组"""
    return int(seconds // 3600 // 24), int(seconds // 3600 % 24), int(seconds % 3600 // 60), int(seconds % 60)


def pri_string_fmt_time(seconds: float) -> str:
    """格式化时间戳至字符串"""
    time_str = ""
    time_tuple = pri_tuple_fmt_time(seconds)
    if time_tuple[0] > 0:
        time_str += f"{time_tuple[0]}d "
    if time_tuple[1] > 0:
        time_str += f"{time_tuple[1]}h "
    if time_tuple[2] > 0:
        time_str += f"{time_tuple[2]}m "
    if time_tuple[3] > 0:
        time_str += f"{time_tuple[3]}s"
    if time_str:
        return time_str
    return "无"


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


class PartInfo(INIPart):
    @staticmethod
    def get_text(theme: CursorTheme) -> str:
        lines = []
        lines.extend([
            "; Cursor theme install script generate by MineCursor",
            "",
            "Theme Info: ",
            f"- Theme ID: {theme.id}",
            f"- Theme Name: {theme.name}",
            f"- Theme Anchor: {theme.author}",
            f"- Theme Description: {theme.description}",
            f"- Theme Base Size: {theme.base_size}",
            f"- Make Time: {pri_string_fmt_time(theme.make_time)}",
            f"- Note: {theme.note}",
            f"- License Info: {theme.license_info}"
            "",
            f"Projects: "
        ])
        for project in theme.projects:
            sub_lines = [
                f"- {project.kind.off_name}",
                f"- - Name: {project.name}"
            ]
            if project.external_name:
                sub_lines.append(f"- - External Name: {project.external_name}")
            sub_lines.append(f"- - Hotspot: {project.center_pos}")
            sub_lines.append(f"- - Size: {project.canvas_size}")
            if project.is_ani_cursor:
                sub_lines.append(f"- - Animation Cursor")
            sub_lines.append(f"- - Make Time: {pri_string_fmt_time(project.make_time)}")
            if project.own_note:
                sub_lines.append(f"- - Note: {project.own_note}")
            if project.own_license_info:
                sub_lines.append(f"- - License Info: {project.own_license_info}")

            lines.extend(sub_lines)
            lines.append("")

        real_lines = []
        for line in lines:
            real_lines.extend(line.split("\n"))
        return "\n; ".join(real_lines)


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
            *[f'"{filename}"     ; {kind.off_name}' for kind, filename in file_map.items()]
        ])


class PartString(INIPart):
    @staticmethod
    def get_text(theme: CursorTheme, file_map: dict[CursorKind, str]):
        return "\n".join([
            '[Strings]',
            rf'CUR_DIR = "Cursors\{theme.name}"',
            f"SCHEME_NAME = {theme.name}",
            *[f'{VAR_NAME_MAP[kind]} = "{filename}"     ; {kind.off_name}' for kind, filename in
              file_map.items()]
        ])


class CursorInstINIGenerator:
    @staticmethod
    def generate(theme: CursorTheme, file_map: dict[CursorKind, str]):
        return "\n\n".join([
            PartInfo.get_text(theme),
            PartVersion.get_text(),
            PartDefaultInstall.get_text(),
            PartDestinationDirs.get_text(),
            PartSchemeReg.get_text(list(file_map.keys())),
            PartSchemeCur.get_text(file_map),
            PartString.get_text(theme, file_map)
        ])
