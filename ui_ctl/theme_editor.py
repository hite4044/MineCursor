import os
import re
from enum import Enum
from os import makedirs
from os.path import join, isfile
from os.path import join as path_join
from shutil import rmtree
from threading import Thread
from typing import cast

import wx

from lib.cursor.inst_ini_gen import CursorInstINIGenerator
from lib.cursor.setter import CURSOR_KIND_NAME_OFFICIAL, CursorKind, CursorsInfo, set_cursors_progress, SchemesType, \
    CR_INFO_FIELD_MAP, CursorData
from lib.cursor.writer import write_cursor_progress
from lib.data import CursorTheme, cursors_file_manager, data_file_manager, INVALID_FILENAME_CHAR, ThemeType
from lib.log import logger
from lib.render import render_project
from lib.resources import theme_manager, ThemeAction
from ui.theme_editor import ThemeEditorUI
from ui_ctl.public_list_ctl import PublicThemeCursorList, PublicThemeSelector, EVT_THEME_SELECTED
from ui_ctl.theme_creator import ThemeCreator
from widget.adv_progress_dialog import AdvancedProgressDialog
from widget.data_dialog import DataDialog, DataLineParam, DataLineType
from widget.ect_menu import EtcMenu
from widget.win_icon import set_multi_size_icon


def get_user_name() -> str:
    import getpass
    return getpass.getuser()


USER_NAME = get_user_name()


class CursorLostType(Enum):
    USE_IDC_RES = 0
    USE_AERO = 1
    # DONT_REPLACE = 2


class ThemeApplyDialog(DataDialog):
    def __init__(self, parent: wx.Window | None, theme: CursorTheme):
        super().__init__(parent, f"应用主题 {theme.name}",
                         DataLineParam("target", "应用目标", DataLineType.CHOICE, SchemesType.USER,
                                       enum_names={SchemesType.SYSTEM: "系统", SchemesType.USER: "用户"}),
                         DataLineParam("lost_type", "如何处理缺失光标", DataLineType.CHOICE, CursorLostType.USE_AERO,
                                       enum_names={CursorLostType.USE_IDC_RES: "使用IDC资源",
                                                   CursorLostType.USE_AERO: "使用Aero光标"}),
                         DataLineParam("raw_size", "使用输出原大小", DataLineType.BOOL, False,
                                       "可能会导致重启后光标大小改变\n"
                                       "除非系统设置里光标大小为1, 而且鼠标指针的大小为32的倍数\n"
                                       "如果鼠标指针太小, 请到系统设置中设置大小后, 再到MineCursor里应用"))
        self.set_icon("theme/apply.png")

    def get_result(self) -> tuple[SchemesType, CursorLostType, bool]:
        datas = self.datas
        result = (datas["target"], datas["lost_type"], datas["raw_size"])
        return cast(tuple[SchemesType, CursorLostType, bool], result)


class ThemeDataDialog(DataDialog):
    def __init__(self, parent: wx.Window | None, is_create,
                 name: str = "Cursor Theme", base_size: int = 32,
                 author: str = USER_NAME, description: str = "None",
                 theme_type: ThemeType = ThemeType.NORMAL):
        super().__init__(parent, "创建主题" if is_create else "编辑主题",
                         DataLineParam("name", "主题名称", DataLineType.STRING, name),
                         DataLineParam("base_size", "基础尺寸", DataLineType.INT, base_size),
                         DataLineParam("author", "作者", DataLineType.STRING, author),
                         DataLineParam("description", "描述", DataLineType.STRING, description),
                         DataLineParam("type", "主题类型", DataLineType.CHOICE, theme_type,
                                       enum_names={
                                           ThemeType.NORMAL: "普通",
                                           ThemeType.FOR_CHOOSE: "预设",
                                           ThemeType.FOR_TEMP: "模版",
                                       }),
                         )
        if is_create:
            self.set_icon("theme/add.png")
        else:
            self.set_icon("theme/edit_info.png")

    def get_result(self) -> tuple[str, int, str, str, ThemeType]:
        datas = self.datas
        return datas["name"], datas["base_size"], datas["author"], datas["description"], ThemeType(datas["type"])


class ThemeEditor(ThemeEditorUI):
    theme_selector: 'ThemeSelector'
    cursor_list: 'ThemeCursorList'

    def __init__(self, parent: wx.Window | None):
        super().__init__(parent)
        set_multi_size_icon(self, r"assets\icon.png")
        self.Bind(EVT_THEME_SELECTED, lambda e: self.cursor_list.load_theme(e.theme))
        self.Bind(wx.EVT_CLOSE, self.on_close)

    @staticmethod
    def on_close(event: wx.CloseEvent):
        theme_manager.save()
        event.Skip()


class ThemeFileDropTarget(wx.FileDropTarget):
    def __init__(self):
        super().__init__()
        self.on_drop_theme = None

    def OnDropFiles(self, x: int, y: int, filenames: list[str]):
        if self.on_drop_theme:
            self.on_drop_theme(x, y, filenames)
        return True


class ThemeSelector(PublicThemeSelector):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)

        self.themes_has_deleted: list[list[tuple[int, CursorTheme]]] = [[(0, theme)] for theme in
                                                                        theme_manager.deleted_themes]
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_menu)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.load_all_theme()
        target = ThemeFileDropTarget()
        target.on_drop_theme = self.on_drop_theme
        self.SetDropTarget(target)

    def on_key_down(self, event: wx.KeyEvent):
        if event.GetKeyCode() == ord("Z") and event.GetModifiers() == wx.MOD_CONTROL:
            self.undo()
        else:
            event.Skip()

    def undo(self):
        if len(self.themes_has_deleted) == 0:
            return
        stacks = self.themes_has_deleted.pop(-1)
        for index, theme in stacks[::-1]:
            theme_manager.themes.insert(index, theme)
            theme_manager.deleted_themes.remove(theme)
            try:
                os.remove(theme_manager.theme_file_mapping.pop(theme))
            except FileNotFoundError:
                pass
        self.reload_themes()

    def on_item_menu(self, event: wx.ListEvent):
        theme = self.line_theme_mapping[event.GetIndex()]
        menu = EtcMenu()
        menu.Append("添加 (&A)", self.on_add_theme, icon="theme/add.png")
        menu.Append("合成主题 (&M)", self.on_create_theme, icon="theme/merge.png")
        menu.AppendSeparator()
        menu.Append("编辑主题信息 (&E)", self.on_edit_theme, theme, icon="theme/edit_info.png")
        menu.AppendSeparator()
        menu.Append("导入主题 (&I)", self.on_import_theme, icon="theme/import.png")
        menu.Append("导出主题 (&O)", self.on_export_theme, theme, icon="theme/export.png")
        menu.AppendSeparator()
        menu.Append("导出指针 (&C)", self.on_export_theme_cursors, theme, icon="theme/export_cursor.png")
        if len(self.themes_has_deleted) != 0:
            menu.AppendSeparator()
            menu.Append("撤销 (&Z)", self.undo, icon="action/undo.png")
        menu.AppendSeparator()
        menu.Append("删除 (&D)", self.on_delete_theme, theme, icon="action/delete.png")
        self.PopupMenu(menu)

    def on_menu(self, event: wx.MouseEvent):
        index = cast(tuple[int, int], self.HitTest(event.GetPosition()))[0]
        if index != -1:
            event.Skip()
            return

        menu = EtcMenu()
        menu.Append("添加 (&A)", self.on_add_theme, icon="theme/add.png")
        menu.Append("合成主题 (&M)", self.on_create_theme, icon="theme/merge.png")
        menu.AppendSeparator()
        menu.Append("导入主题 (&I)", self.on_import_theme, icon="theme/import.png")
        if len(self.themes_has_deleted) != 0:
            menu.AppendSeparator()
            menu.Append("撤销 (&Z)", self.undo, icon="action/undo.png")
        menu.AppendSeparator()
        menu.Append("打开主题文件夹 (&O)", self.on_open_theme_folder, icon="action/open_data_dir.png")
        menu.Append("清空所有主题 (&D)", self.on_clear_all_theme, icon="action/delete.png")

        self.PopupMenu(menu)

    def exchange_item(self, index: int, offset: int):
        if not (0 <= index + offset < self.GetItemCount()):
            return
        project = theme_manager.themes[index]
        theme_manager.themes.pop(index)
        theme_manager.themes.insert(index + offset, project)
        self.reload_themes()
        self.Select(index + offset)

    def on_create_theme(self):
        dialog = ThemeCreator(self)
        if dialog.ShowModal() == wx.ID_OK:
            self.reload_themes()

    def on_add_theme(self):
        dialog = ThemeDataDialog(self, True, self.get_theme_default_name())
        if dialog.ShowModal() == wx.ID_OK:
            name, base_size, author, description, theme_type = dialog.get_result()
            if re.findall(INVALID_FILENAME_CHAR, name):
                wx.MessageBox(f"主题名 [{name}] 中的非法字符已替换为下划线\n(为了保存主题文件)", "主题名中的非法字符",
                              wx.OK | wx.ICON_WARNING)
            name = re.sub(INVALID_FILENAME_CHAR, "_", name)
            theme = CursorTheme(name, base_size, author, description, theme_type)
            theme_manager.add_theme(theme)
            self.reload_themes()
            self.Select(self.GetItemCount() - 1)

    def on_edit_theme(self, theme: CursorTheme):
        dialog = ThemeDataDialog(self, False, theme.name, theme.base_size, theme.author, theme.description, theme.type)
        if dialog.ShowModal() == wx.ID_OK:
            name, base_size, author, description, theme_type = dialog.get_result()
            if re.findall(INVALID_FILENAME_CHAR, name):
                wx.MessageBox(f"主题名 [{name}] 中的非法字符已替换为下划线\n(为了保存主题文件)", "主题名中的非法字符",
                              wx.OK | wx.ICON_WARNING)
            theme.name = re.sub(INVALID_FILENAME_CHAR, "_", name)
            theme.base_size = base_size
            theme.author = author
            theme.description = description
            theme.type = theme_type
            self.reload_themes()
            theme_manager.renew_theme(theme)

    def on_delete_theme(self, first_theme: CursorTheme):
        logger.info(f"删除主题: {first_theme}")
        indexes: list[int] = [{v: k for k, v in self.line_theme_mapping.items()}[theme] for theme in [first_theme]]
        self.themes_has_deleted.append([(line, element) for line, element in zip(indexes[::-1], [first_theme][::-1])])
        theme_manager.deleted_themes.append(first_theme)
        theme_manager.remove_theme(first_theme)
        self.reload_themes()

    def on_drop_theme(self, _, __, filenames: list[str]):
        for file_path in filenames:
            if isfile(file_path):
                theme_manager.load_theme(file_path)
        self.reload_themes()

    def on_export_theme(self, theme: CursorTheme):
        dialog = wx.FileDialog(self, "导出主题",
                               wildcard="MineCursor 主题文件 (*.mctheme)|*.mctheme|MineCursor 主题文件 (*json)|*json",
                               style=wx.FD_SAVE)
        if dialog.ShowModal() == wx.ID_OK:
            file_path = dialog.GetPath()
            theme_manager.save_theme_file(file_path, theme)

    def on_export_theme_cursors(self, theme: CursorTheme):
        dialog = wx.DirDialog(self, "导出主题指针", defaultPath=theme.name)
        if dialog.ShowModal() == wx.ID_OK:
            dir_path = dialog.GetPath()
            makedirs(dir_path, exist_ok=True)
            file_map: dict[CursorKind, str] = {}
            for project in theme.projects:
                file_name = f"{CURSOR_KIND_NAME_OFFICIAL[project.kind]}" + (".ani" if project.is_ani_cursor else ".cur")
                fp = path_join(dir_path, file_name)
                frames = render_project(project)
                list(write_cursor_progress(fp, frames, project))
                file_map[project.kind] = file_name
            ini = CursorInstINIGenerator.generate(theme, file_map)
            with open(path_join(dir_path, "~右键安装.inf"), "w", encoding="gbk") as f:
                f.write(ini)

    def on_import_theme(self):
        dialog = wx.FileDialog(self, "导入主题",
                               wildcard="MineCursor 主题文件 (*.mctheme)|*.mctheme|所有文件 (*.*)|*.*",
                               style=wx.FD_OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            file_path = dialog.GetPath()
            theme_manager.load_theme(file_path)
            self.reload_themes()

    @staticmethod
    def on_open_theme_folder():
        dir_path = data_file_manager.work_dir
        wx.LaunchDefaultApplication(dir_path)

    def on_clear_all_theme(self):
        logger.info(f"清空所有主题")
        ret = wx.MessageBox("真的要清空所有主题吗?", "清理确认", wx.ICON_WARNING | wx.YES_NO)
        if ret != wx.YES:
            return
        theme_manager.clear_all_theme()
        self.reload_themes()

    def get_theme_default_name(self) -> str:
        DEFAULT_NAME = "鼠标主题"
        names = [self.GetItemText(line) for line in range(self.GetItemCount())]
        line = 0
        if not names:
            return DEFAULT_NAME
        for line in range(self.GetItemCount()):
            target_name = f"{DEFAULT_NAME} ({line + 1})" if line != 0 else DEFAULT_NAME
            if target_name not in names:
                return target_name
        return f"{DEFAULT_NAME} ({line + 1})"


def get_all_theme_ids() -> dict[str, str]:
    _, dirs, _ = next(os.walk(cursors_file_manager.work_dir))
    themes_ids = {}
    for dir_name in dirs:
        if not dir_name.startswith("Theme_"):
            continue
        parts = dir_name.split("_")
        theme_id = parts[1]
        themes_ids[theme_id] = join(cursors_file_manager.work_dir, dir_name)
    return themes_ids


def apply_theme(theme: CursorTheme, target: SchemesType, raw_size: bool,
                lost_type: CursorLostType, dialog: AdvancedProgressDialog):
    # 删除之前同主题的文件夹
    dialog.set_panels_num(1)
    dialog.update(0, 0, "获取所有主题文件夹")
    theme_ids = get_all_theme_ids()
    if theme.id in theme_ids:
        dialog.update(0, 0, "删除旧主题")
        rmtree(theme_ids[theme.id])

    cursor_paths = CursorsInfo(use_aero=lost_type == CursorLostType.USE_AERO)
    work_dir = cursors_file_manager.make_work_dir(f"Theme_{theme.id}_{theme.name}")
    dialog.set_panels_num(2)
    dialog.update(0, 0, range_=len(theme.projects))
    for i, project in enumerate(theme.projects):
        dialog.update(0, i, f"导出项目: {project}")
        dialog.update(1, 0, "...")
        frames = render_project(project)
        file_name = f"Cursor_{project.id}_{project.name}" + (".ani" if project.is_ani_cursor else ".cur")
        file_path = join(work_dir, file_name)
        logger.info(f"渲染指针项目: {project}")
        frames_num = len(frames)
        dialog.update(1, 0, f"写入帧 (0/{frames_num})", frames_num)
        gen = write_cursor_progress(file_path, frames, project)
        for msg, index in gen:
            real_msg = f"{msg} ({index}/{frames_num})" if index != -1 else msg
            dialog.update(1, index, real_msg)

        attr_name = CR_INFO_FIELD_MAP[project.kind]
        cursor_data: CursorData = getattr(cursor_paths, attr_name)
        cursor_data.set_path(file_path)

    dialog.set_panels_num(1)
    gen = set_cursors_progress(cursor_paths, target, theme.name, theme.id, theme.base_size, raw_size)
    msg = ""
    for msg, index in gen:
        if isinstance(msg, bool):
            break
        dialog.update(0, index, msg)
    if not msg:
        wx.MessageBox("设置注册表失败", "主题应用错误", wx.ICON_ERROR)


class ThemeCursorList(PublicThemeCursorList):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        theme_manager.register_theme_change_callback(ThemeAction.DELETE, self.on_delete_theme)
        self.apply_theme_btn.Bind(wx.EVT_BUTTON, self.on_apply_theme)

    def on_apply_theme(self, _):
        if self.active_theme is None:
            return
        theme = self.active_theme
        info_dialog = ThemeApplyDialog(self, theme)
        if info_dialog.ShowModal() != wx.ID_OK:
            return
        target, lost_type, raw_size = info_dialog.get_result()

        dialog = AdvancedProgressDialog(self, "应用主题", 2)
        self.apply_theme_btn.Disable()
        Thread(target=self.real_apply_theme, args=(theme, target, raw_size, lost_type, dialog), daemon=True).start()
        dialog.ShowModal()
        dialog.Destroy()

    def real_apply_theme(self, theme: CursorTheme, target: SchemesType, raw_size: bool,
                         lost_type: CursorLostType, dialog: AdvancedProgressDialog):
        try:
            apply_theme(theme, target, raw_size, lost_type, dialog)
        except RuntimeError:
            ""
            logger.info("用户终止应用主题")
            wx.CallAfter(self.apply_theme_btn.Enable)
            return
        except Exception as e:
            logger.error(f"应用主题失败: {e}")
            wx.MessageBox(f"应用主题失败: {e}", "错误", wx.ICON_ERROR)
        wx.CallAfter(dialog.EndModal, wx.ID_OK)
        wx.CallAfter(self.apply_theme_btn.Enable)

    def on_delete_theme(self, delete_theme: CursorTheme):
        if delete_theme is self.active_theme:
            self.load_theme(None)


def test_editor():
    app = wx.App()
    frame = ThemeEditor(None)
    frame.Show()

    # theme = CursorTheme("Test Theme")
    # project = CursorProject("Sword Loading", (32, 32))
    # project.is_ani_cursor = True
    # project.frame_count = 64
    # project.ani_rate = 50
    # project.add_element(
    #     CursorElement("Diamond Sword", [Image.open("diamond_sword.png").convert("RGBA")], scale=Scale2D(2.0, 2.0),
    #                   reverse_x=True))
    #
    # element = CursorElement("Clock", [])
    # element.position = Position(17, 0)
    # for f_index in range(64):
    #     fp = rf"assets_test\clock_{str(f_index).zfill(2)}.png"
    #     element.frames.append(Image.open(fp).convert("RGBA"))
    # element.animation_key_data.frame_length = 64
    # element.update_ani_data_by_key_data()
    # project.add_element(element)
    #
    # for member in CursorKind:
    #     project.kind = member
    #     theme.active_projects.append(deepcopy(project))
    # theme_manager.add_theme(theme)
    # frame.theme_selector.reload_themes()

    app.MainLoop()


if __name__ == "__main__":
    test_editor()
