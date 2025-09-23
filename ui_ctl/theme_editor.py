import json
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

from lib.config import config
from lib.cursor.inst_ini_gen import CursorInstINIGenerator
from lib.cursor.setter import CURSOR_KIND_NAME_OFFICIAL, CursorKind, CursorsInfo, set_cursors_progress, SchemesType, \
    CR_INFO_FIELD_MAP, CursorData
from lib.cursor.writer import write_cursor_progress
from lib.data import CursorTheme, path_theme_cursors, path_theme_data, INVALID_FILENAME_CHAR, ThemeType, generate_id
from lib.log import logger
from lib.render import render_project
from lib.resources import theme_manager, ThemeAction, deleted_theme_manager, ThemeFileType
from ui.select import select_all
from ui.theme_editor import ThemeEditorUI
from ui_ctl.about_dialog import AboutDialog
from ui_ctl.public_list_ctl import PublicThemeCursorList, PublicThemeSelector, EVT_THEME_SELECTED, string_fmt_time
from ui_ctl.theme_creator import ThemeCreator
from widget.adv_progress_dialog import AdvancedProgressDialog
from widget.data_dialog import DataDialog, DataLineParam, DataLineType
from widget.ect_menu import EtcMenu
from widget.win_icon import set_multi_size_icon


class CursorLostType(Enum):
    USE_IDC_RES = 0
    USE_AERO = 1
    # DONT_REPLACE = 2


class ThemeApplyDialog(DataDialog):
    def __init__(self, parent: wx.Window | None, theme: CursorTheme):
        super().__init__(parent, f"应用主题 {theme.name}",
                         # DataLineParam("target", "应用目标", DataLineType.CHOICE, SchemesType.USER,
                         #               enum_names={SchemesType.SYSTEM: "系统", SchemesType.USER: "用户"}),
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
        result = (SchemesType.USER, datas["lost_type"], datas["raw_size"])
        return cast(tuple[SchemesType, CursorLostType, bool], result)


class ThemeDataDialog(DataDialog):
    def __init__(self, parent: wx.Window | None, is_create: bool, theme: CursorTheme | None = None):
        if theme is None:
            theme = CursorTheme("新指针主题", 32, config.default_author)
        params = [
            DataLineParam("name", "主题名称", DataLineType.STRING, theme.name),
            DataLineParam("base_size", "基础尺寸", DataLineType.INT, theme.base_size),
            DataLineParam("author", "作者", DataLineType.STRING, theme.author),
            DataLineParam("description", "描述", DataLineType.STRING, theme.description),
            DataLineParam("type", "主题类型", DataLineType.CHOICE, theme.type,
                          enum_names={
                              ThemeType.NORMAL: "普通",
                              ThemeType.PRE_DEFINE: "预设",
                              ThemeType.TEMPLATE: "模版",
                          })]
        if not is_create:
            params.append(DataLineParam("Explorers - Hinkik", "制作时间", DataLineType.STRING,
                                        string_fmt_time(theme.make_time), disabled=True))
            params.append(DataLineParam("Special Ability - Empty", "创建时间", DataLineType.STRING,
                                        theme.create_time, disabled=True))
            params.append(DataLineParam("note", "备注", DataLineType.STRING, theme.note, multilined=True))
            params.append(DataLineParam("license_info", "协议信息", DataLineType.STRING,
                                        theme.license_info, multilined=True))
        super().__init__(parent, "创建主题" if is_create else "编辑主题", *params)
        self.is_create = is_create
        if is_create:
            self.set_icon("theme/add.png")
        else:
            self.set_icon("theme/edit_info.png")

    def as_theme(self, theme: CursorTheme | None = None) -> CursorTheme:
        if theme is None:
            theme = CursorTheme("Barrier - KARUT")

        datas = self.datas
        name = datas["name"]
        if re.findall(INVALID_FILENAME_CHAR, name):
            wx.MessageBox(f"主题名 [{name}] 中的非法字符已替换为下划线\n(为了保存主题文件)", "主题名中的非法字符",
                          wx.OK | wx.ICON_WARNING)
        name = re.sub(INVALID_FILENAME_CHAR, "_", name)

        theme.name = name
        theme.base_size = datas["base_size"]
        theme.author = datas["author"]
        theme.description = datas["description"]
        theme.type = ThemeType(datas["type"])
        if not self.is_create:
            theme.note = datas["note"]
            theme.license_info = datas["license_info"]
        return theme


class ThemeFileTypeDialog(DataDialog):
    def __init__(self, parent: wx.Window | None):
        super().__init__(parent, "选择主题文件格式",
                         DataLineParam("type", "主题文件格式", DataLineType.CHOICE, ThemeFileType.ZIP_COMPRESS,
                                       enum_names={
                                           ThemeFileType.RAW_JSON: "原始Json (体积大) (可直接编辑)",
                                           ThemeFileType.ZIP_COMPRESS: "Zip流 (体积小) (便于分享)"
                                       }))
        self.set_icon("theme/theme_file_type.png")

    def get_result(self) -> ThemeFileType:
        return ThemeFileType(self.datas["type"])  # 套一层类实例确保IDE检测的返回类型正确


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
        """程序关闭前的动作"""
        theme_manager.save()
        deleted_theme_manager.save()
        config.save_config()
        event.Skip()


class ThemeFileDropTarget(wx.FileDropTarget):
    def __init__(self):
        super().__init__()
        self.on_drop_theme = None

    def OnDropFiles(self, x: int, y: int, filenames: list[str]):
        if self.on_drop_theme:
            self.on_drop_theme(x, y, filenames)
        return True


def mk_end(li: list):
    if len(li) > 1:
        return f" ({len(li)})"
    return ""


class ThemeSelector(PublicThemeSelector):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)

        self.themes_has_deleted: list[list[tuple[int, CursorTheme]]] = [[(0, theme)] for theme in
                                                                        deleted_theme_manager.themes]
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
        elif event.GetKeyCode() == ord("A") and event.GetModifiers() == wx.MOD_CONTROL:
            select_all(self)
        else:
            event.Skip()

    def undo(self):
        if len(self.themes_has_deleted) == 0:
            return
        stacks = self.themes_has_deleted.pop(-1)
        for index, theme in stacks[::-1]:
            deleted_theme_manager.remove_theme(theme)
            if theme in theme_manager.themes:
                theme.id = generate_id()
            theme_manager.themes.insert(index, theme)
        self.reload_themes()

    def get_select_items(self) -> list[int]:
        first = self.GetFirstSelected()
        selections = []
        while first != -1:
            selections.append(first)
            first = self.GetNextSelected(first)
        return selections

    def on_item_menu(self, event: wx.ListEvent):
        theme = self.line_theme_mapping[event.GetIndex()]
        themes = [self.line_theme_mapping[index] for index in self.get_select_items()]
        menu = EtcMenu()
        menu.Append("添加 (&A)", self.on_add_theme, icon="theme/add.png")
        menu.Append("合成主题 (&M)", self.on_create_theme, icon="theme/merge.png")
        if len(themes) == 1:
            menu.AppendSeparator()
            menu.Append("编辑主题信息 (&E)", self.on_edit_theme, theme, icon="theme/edit_info.png")
        menu.AppendSeparator()
        menu.Append("导入主题 (&I)", self.on_import_theme, icon="theme/import.png")
        menu.Append("导出主题 (&O)" + mk_end(themes), self.on_export_theme, themes, icon="theme/export.png")
        if len(themes) == 1:
            menu.AppendSeparator()
            menu.Append("导出指针 (&C)", self.on_export_theme_cursors, theme, icon="theme/export_cursor.png")
        if len(self.themes_has_deleted) != 0:
            menu.AppendSeparator()
            menu.Append("撤销 (&Z)", self.undo, icon="action/undo.png")
        if len(themes) == 1:
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
        menu.Append("显示隐藏主题 (&H)", self.on_show_hidden_theme,
                    icon="theme/unshow_hidden.png" if config.show_hidden_themes else "theme/show_hidden.png")
        menu.AppendSeparator()
        menu.Append("打开主题文件夹 (&O)", self.on_open_theme_folder, icon="action/open_data_dir.png")
        menu.Append("关于 (&E)", self.on_show_about_dialog, icon="action/about.png")

        self.PopupMenu(menu)

    def on_show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.ShowModal()

    def on_show_hidden_theme(self):
        config.show_hidden_themes = not config.show_hidden_themes
        self.reload_themes()

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
        dialog = ThemeDataDialog(self, True)
        if dialog.ShowModal() == wx.ID_OK:
            theme = dialog.as_theme()
            theme_manager.add_theme(theme)
            self.reload_themes()
            self.Select(self.GetItemCount() - 1)

    def on_edit_theme(self, theme: CursorTheme):
        dialog = ThemeDataDialog(self, False, theme)
        if dialog.ShowModal() == wx.ID_OK:
            dialog.as_theme(theme)
            theme_manager.renew_theme(theme)
            self.reload_themes()

    def on_delete_theme(self, first_theme: CursorTheme):
        logger.info(f"删除主题: {first_theme}")
        indexes: list[int] = [{v: k for k, v in self.line_theme_mapping.items()}[theme] for theme in [first_theme]]
        self.themes_has_deleted.append([(line, element) for line, element in zip(indexes[::-1], [first_theme][::-1])])
        theme_manager.remove_theme(first_theme)
        deleted_theme_manager.add_theme(first_theme)
        self.reload_themes()

    def on_drop_theme(self, _, __, filenames: list[str]):
        for file_path in filenames:
            if isfile(file_path):
                theme_manager.load_theme(file_path)
        self.reload_themes()

    def on_export_theme(self, themes: list[CursorTheme]):
        dialog = wx.FileDialog(self, f"导出主题 ({len(themes)}个主题)",
                               defaultFile=f"{themes[0].name}.mctheme",
                               wildcard="|".join(["MineCursor 主题文件 (*.mctheme)|*.mctheme",
                                                  "MineCursor 渲染主题文件 (*.rmctheme)|*.rmctheme"]),
                               style=wx.FD_SAVE)
        if dialog.ShowModal() != wx.ID_OK:
            return

        file_path = dialog.GetPath()
        file_dir = os.path.dirname(file_path)
        end_fix = file_path.split(".")[-1]

        dialog = ThemeFileTypeDialog(self)
        if dialog.ShowModal() != wx.ID_OK:
            return
        file_type = dialog.get_result()
        for theme in themes:
            export_path = os.path.join(file_dir, theme.name + "." + end_fix)
            if end_fix == "rmctheme":
                theme_manager.save_rendered_theme_file(export_path, theme, file_type)
            else:
                theme_manager.save_theme_file(export_path, theme, file_type)

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
                               wildcard="|".join(["MineCursor 主题文件 (*.mctheme)|*.mctheme",
                                                  "MineCursor 渲染主题文件 (*.rmctheme)|*.rmctheme",
                                                  "所有文件 (*.*)|*.*"]),
                               style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if dialog.ShowModal() == wx.ID_OK:
            error_paths = []
            for file_path in dialog.GetFilenames():
                try:
                    theme = theme_manager.load_theme_file(file_path)
                    theme.id = generate_id()
                    logger.info(f"已加载主题: {theme}")
                    theme_manager.add_theme(theme)
                except (KeyError, json.JSONDecodeError):
                    error_paths.append(file_path)
            if error_paths:
                pf = '\n'.join(error_paths)
                wx.MessageBox(f"以下主题文件导入失败: \n{pf}",
                              "导入主题文件失败", wx.OK | wx.ICON_ERROR)
            self.reload_themes()

    @staticmethod
    def on_open_theme_folder():
        dir_path = path_theme_data
        wx.LaunchDefaultApplication(dir_path)

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
    _, dirs, _ = next(os.walk(path_theme_cursors))
    themes_ids = {}
    for dir_name in dirs:
        if not dir_name.startswith("Theme_"):
            continue
        parts = dir_name.split("_")
        theme_id = parts[1]
        themes_ids[theme_id] = join(path_theme_cursors, dir_name)
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
    theme_cursors_dir = path_theme_cursors.make_sub_dir(f"Theme_{theme.id}_{theme.name}")
    dialog.set_panels_num(2)
    dialog.update(0, 0, range_=len(theme.projects))
    for i, project in enumerate(theme.projects):
        dialog.update(0, i, f"导出项目: {project}")
        dialog.update(1, 0, "...")
        frames = render_project(project)
        file_name = f"Cursor_{project.id}_{project.name}" + (".ani" if project.is_ani_cursor else ".cur")
        file_path = join(theme_cursors_dir, file_name)
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
            logger.error(f"应用主题失败: {e.__class__.__name__}: {e}")
            wx.MessageBox(f"应用主题失败: {e.__class__.__name__}: {e}", "错误", wx.ICON_ERROR)
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
