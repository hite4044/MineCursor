import os
from copy import deepcopy
from enum import Enum
from os import makedirs
from os.path import join, isfile
from shutil import rmtree
from threading import Thread
from typing import cast

import wx
from PIL.Image import Resampling

from lib.cursor_setter import CURSOR_KIND_NAME_OFFICIAL, CURSOR_KIND_NAME_CUTE, CursorKind, CursorsInfo, \
    set_cursors_progress, \
    SchemesType, CR_INFO_FIELD_MAP, CursorData
from lib.cursor_writer import write_cursor_progress
from lib.data import CursorTheme, CursorProject, cursors_file_manager, data_file_manager
from lib.image_pil2wx import PilImg2WxImg
from lib.log import logger
from lib.render import render_project_frame, render_project
from lib.theme_manager import theme_manager, ThemeAction
from ui.theme_editor import ThemeEditorUI, ThemeCursorListUI, ThemeSelectorUI
from ui_ctl.cursor_editor import CursorEditor
from widget.adv_progress_dialog import AdvancedProgressDialog
from widget.data_dialog import DataDialog, DataLineParam, DataLineType
from widget.ect_menu import EtcMenu
from widget.win_icon import set_multi_size_icon
from os.path import join as path_join


def get_user_name() -> str:
    import getpass
    return getpass.getuser()


USER_NAME = get_user_name()

mcEVT_THEME_SELECTED = wx.NewEventType()
EVT_THEME_SELECTED = wx.PyEventBinder(mcEVT_THEME_SELECTED)


class ThemeSelectedEvent(wx.PyCommandEvent):
    def __init__(self, theme: CursorTheme):
        super().__init__(mcEVT_THEME_SELECTED)
        self.theme = theme


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
                                                   CursorLostType.USE_AERO: "使用Aero光标"}))
        set_multi_size_icon(self, r"assets/icons/apply_theme.png")

    def get_result(self) -> tuple[SchemesType, CursorLostType]:
        datas = self.datas
        result = (datas["target"], datas["lost_type"])
        return cast(tuple[SchemesType, CursorLostType], result)


class ProjectDataDialog(DataDialog):
    def __init__(self, parent: wx.Window | None, is_create: bool = True,
                 name: str = "", external_name: str = "", size: int | tuple[int, int] = 32,
                 kind: CursorKind = CursorKind.ARROW):
        self.canvas_params = [
            DataLineParam("canvas_size", "画布尺寸", DataLineType.INT, size),
        ] if is_create else [
            DataLineParam("size_width", "画布宽", DataLineType.INT, size[0]),
            DataLineParam("size_height", "画布高", DataLineType.INT, size[1]),
        ]
        super().__init__(parent, "添加指针项目",
                         DataLineParam("name", "项目名称", DataLineType.STRING, name),
                         DataLineParam("external_name", "展示名称", DataLineType.STRING,
                                       external_name if external_name else ""),
                         *self.canvas_params,
                         DataLineParam("kind", "类型", DataLineType.CHOICE, kind,
                                       enum_names=CURSOR_KIND_NAME_OFFICIAL))
        set_multi_size_icon(self, r"assets/icons/add_project.png")

    def get_result(self) -> tuple[str, str | None, int | tuple[int, int], CursorKind]:
        datas = self.datas
        if len(self.canvas_params) == 1:
            size = datas["canvas_size"]
        else:
            size = (datas["size_width"], datas["size_height"])
        if datas["name"] == "":
            datas["name"] = CURSOR_KIND_NAME_OFFICIAL[cast(CursorKind, datas["kind"])]
        result = (datas["name"], datas["external_name"] if datas["external_name"] else None, size, datas["kind"])
        return cast(tuple[str, str | None, int | tuple[int, int], CursorKind], result)


class MutilProjectDataDialog(DataDialog):
    def __init__(self, parent: wx.Window | None,
                 size: int | tuple[int, int] = 32,
                 scale: float = 1.0):
        self.params = [
            DataLineParam("edit_size", "编辑画布大小", DataLineType.BOOL, False),
            DataLineParam("size_width", "画布宽", DataLineType.INT, size[0]),
            DataLineParam("size_height", "画布高", DataLineType.INT, size[1]),
            DataLineParam("edit_scale", "编辑缩放", DataLineType.BOOL, False),
            DataLineParam("scale", "缩放", DataLineType.FLOAT, scale)
        ]
        super().__init__(parent, "添加指针项目", *self.params)
        set_multi_size_icon(self, r"assets/icons/add_project.png")

    def get_result(self) -> tuple[tuple[bool, int, int], tuple[bool, float]]:
        datas = self.datas
        return (datas["edit_size"], datas["size_width"], datas["size_height"]), (datas["edit_scale"], datas["scale"])


class ThemeDataDialog(DataDialog):
    def __init__(self, parent: wx.Window | None, is_create,
                 name: str = "Cursor Theme", base_size: int = 32,
                 author: str = USER_NAME, description: str = "None"):
        super().__init__(parent, "创建主题" if is_create else "编辑主题",
                         DataLineParam("name", "主题名称", DataLineType.STRING, name),
                         DataLineParam("base_size", "基础尺寸", DataLineType.INT, base_size),
                         DataLineParam("author", "作者", DataLineType.STRING, author),
                         DataLineParam("description", "描述", DataLineType.STRING, description),
                         )
        if is_create:
            set_multi_size_icon(self, r"assets/icons/add_theme.png")
        else:
            set_multi_size_icon(self, r"assets/icons/edit_theme.png")

    def get_result(self) -> tuple[str, int, str, str]:
        datas = self.datas
        return datas["name"], datas["base_size"], datas["author"], datas["description"]


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


class ThemeSelector(ThemeSelectorUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.line_theme_mapping: dict[int, CursorTheme] = {}

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_menu)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu)
        self.load_all_theme()
        target = ThemeFileDropTarget()
        target.on_drop_theme = self.on_drop_theme
        self.SetDropTarget(target)

    def load_all_theme(self):
        for theme in theme_manager.themes:
            self.append_theme(theme)

    def reload_themes(self):
        self.DeleteAllItems()
        self.line_theme_mapping.clear()
        self.load_all_theme()

    def on_item_menu(self, event: wx.ListEvent):
        theme = self.line_theme_mapping[event.GetIndex()]
        menu = EtcMenu()
        menu.Append("添加", self.on_add_theme)
        menu.AppendSeparator()
        menu.Append("导入主题", self.on_import_theme)
        menu.AppendSeparator()
        menu.Append("编辑主题信息", self.on_edit_theme, theme)
        menu.Append("删除", self.on_delete_theme, theme)
        menu.AppendSeparator()
        menu.Append("导出主题", self.on_export_theme, theme)
        menu.Append("导出指针", self.on_export_theme_cursors, theme)
        self.PopupMenu(menu)

    def on_menu(self, event: wx.MouseEvent):
        index = cast(tuple[int, int], self.HitTest(event.GetPosition()))[0]
        if index != -1:
            event.Skip()
            return

        menu = EtcMenu()
        menu.Append("添加", self.on_add_theme)
        menu.AppendSeparator()
        menu.Append("导入主题", self.on_import_theme)
        menu.Append("打开主题文件夹", self.on_open_theme_folder)
        menu.AppendSeparator()
        menu.Append("清空所有主题", self.on_clear_all_theme)
        self.PopupMenu(menu)

    def on_add_theme(self):
        dialog = ThemeDataDialog(self, True, self.get_theme_default_name())
        if dialog.ShowModal() == wx.ID_OK:
            name, base_size, author, description = dialog.get_result()
            theme = CursorTheme(name, base_size, author, description)
            theme_manager.add_theme(theme)
            self.reload_themes()
            self.Select(self.GetItemCount() - 1)

    def on_edit_theme(self, theme: CursorTheme):
        dialog = ThemeDataDialog(self, False, theme.name, theme.base_size, theme.author, theme.description)
        if dialog.ShowModal() == wx.ID_OK:
            name, base_size, author, description = dialog.get_result()
            theme.name = name
            theme.base_size = base_size
            theme.author = author
            theme.description = description
            self.reload_themes()

    def on_delete_theme(self, theme: CursorTheme):
        logger.info(f"删除主题: {theme}")
        theme_manager.remove_theme(theme)
        self.reload_themes()

    def on_drop_theme(self, _, __, filenames: list[str]):
        for file_path in filenames:
            if isfile(file_path):
                theme_manager.load_theme_file(file_path)
        self.reload_themes()

    def on_export_theme(self, theme: CursorTheme):
        dialog = wx.FileDialog(self, "导出主题", wildcard="MineCursor 主题文件 (*.mctheme)|*.mctheme", style=wx.FD_SAVE)
        if dialog.ShowModal() == wx.ID_OK:
            file_path = dialog.GetPath()
            theme_manager.save_theme_file(file_path, theme)

    def on_export_theme_cursors(self, theme: CursorTheme):
        dialog = wx.DirDialog(self, "导出主题指针", defaultPath=theme.name)
        if dialog.ShowModal() == wx.ID_OK:
            dir_path = dialog.GetPath()
            makedirs(dir_path, exist_ok=True)
            for project in theme.projects:
                fp = path_join(dir_path, f"{project.name}_{project.id}" + (".ani" if project.is_ani_cursor else ".cur"))
                frames = render_project(project)
                list(write_cursor_progress(fp, frames, project.center_pos, project.ani_rate))


    def on_import_theme(self):
        dialog = wx.FileDialog(self, "导入主题",
                               wildcard="MineCursor 主题文件 (*.mctheme)|*.mctheme|所有文件 (*.*)|*.*",
                               style=wx.FD_OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            file_path = dialog.GetPath()
            theme_manager.load_theme_file(file_path)
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

    def on_item_selected(self, event: wx.ListEvent):
        theme = self.line_theme_mapping[event.GetIndex()]
        logger.debug(f"主题被选择: {theme}")
        wx.PostEvent(self, ThemeSelectedEvent(theme))

    def append_theme(self, theme: CursorTheme):
        line = self.GetItemCount()
        index = self.InsertItem(line, theme.name)
        self.SetItem(index, 1, str(theme.base_size))
        self.SetItem(index, 2, theme.author)
        self.SetItem(index, 3, theme.description)
        self.line_theme_mapping[index] = theme


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


def apply_theme(theme: CursorTheme, target: SchemesType, lost_type: CursorLostType,
                dialog: AdvancedProgressDialog):
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
        gen = write_cursor_progress(file_path, frames, project.center_pos, project.ani_rate)
        for msg, index in gen:
            real_msg = f"{msg} ({index}/{frames_num})" if index != -1 else msg
            dialog.update(1, index, real_msg)

        attr_name = CR_INFO_FIELD_MAP[project.kind]
        cursor_data: CursorData = getattr(cursor_paths, attr_name)
        cursor_data.set_path(file_path)

    dialog.set_panels_num(1)
    gen = set_cursors_progress(cursor_paths, target, theme.name, theme.id, theme.base_size)
    msg = ""
    for msg, index in gen:
        if isinstance(msg, bool):
            break
        dialog.update(0, index, msg)
    if not msg:
        wx.MessageBox("设置注册表失败", "主题应用错误", wx.ICON_ERROR)


class ThemeCursorList(ThemeCursorListUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.active_theme: CursorTheme | None = None
        self.image_list = wx.ImageList()
        self.use_cute_name: bool = True
        theme_manager.register_theme_change_callback(ThemeAction.DELETE, self.on_delete_theme)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_menu, self)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated, self)
        self.apply_theme_btn.Bind(wx.EVT_BUTTON, self.on_apply_theme)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu, self)

    def on_apply_theme(self, _):
        if self.active_theme is None:
            return
        theme = self.active_theme
        info_dialog = ThemeApplyDialog(self, theme)
        if info_dialog.ShowModal() != wx.ID_OK:
            return
        target, lost_type = info_dialog.get_result()

        dialog = AdvancedProgressDialog(self, "应用主题", 2)
        self.apply_theme_btn.Disable()
        Thread(target=self.real_apply_theme, args=(theme, target, lost_type, dialog), daemon=True).start()
        dialog.ShowModal()
        dialog.Destroy()

    def real_apply_theme(self, theme: CursorTheme, target: SchemesType, lost_type: CursorLostType,
                         dialog: AdvancedProgressDialog):
        try:
            apply_theme(theme, target, lost_type, dialog)
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

    def load_theme(self, theme: CursorTheme | None):
        self.active_theme = theme
        self.image_list.RemoveAll()
        self.image_list.Destroy()
        size = 96
        self.image_list = wx.ImageList(size, size)
        self.AssignImageList(self.image_list, wx.IMAGE_LIST_NORMAL)
        self.DeleteAllItems()
        if theme is None:
            return
        for i, project in enumerate(theme.projects):
            cursor_image = render_project_frame(project, 0)
            cursor_image = cursor_image.resize((size, size), Resampling.BOX)
            cursor_bitmap = PilImg2WxImg(cursor_image).ConvertToBitmap()
            cursor_image_id = self.image_list.Add(cursor_bitmap)
            if project.external_name is not None:
                name = project.external_name
            elif self.use_cute_name:
                name = CURSOR_KIND_NAME_CUTE[project.kind]
            else:
                name = CURSOR_KIND_NAME_OFFICIAL[project.kind]
            self.InsertItem(i, name, cursor_image_id)

    def get_select_items(self) -> list[int]:
        first = self.GetFirstSelected()
        selections = []
        while first != -1:
            selections.append(first)
            first = self.GetNextSelected(first)
        return selections

    def on_item_activated(self, event: wx.ListEvent):
        active_project = self.active_theme.projects[event.GetIndex()]
        self.menu_edit_projects([active_project])

    def on_item_menu(self, event: wx.ListEvent):
        active_project = self.active_theme.projects[event.GetIndex()]
        projects = [self.active_theme.projects[i] for i in self.get_select_items()]
        menu = EtcMenu()
        menu.Append("添加项目", self.menu_add_project)
        menu.AppendSeparator()
        text = "编辑项目" if len(projects) == 1 else f"编辑项目 ({len(projects)})"
        menu.Append(text, self.menu_edit_projects, projects)
        text = "编辑项目信息" if len(projects) == 1 else f"编辑项目信息 ({len(projects)})"
        menu.Append(text, self.menu_edit_project_info, projects, active_project)
        if len(projects) == 1:
            menu.AppendSeparator()
            menu.Append("复制项目", self.menu_copy_project, active_project)
        menu.AppendSeparator()
        text = "删除" if len(projects) == 1 else f"删除 ({len(projects)})"
        menu.Append(text, self.menu_delete_projects, projects)
        self.PopupMenu(menu)

    def on_menu(self, event: wx.MouseEvent):
        index = cast(tuple[int, int], self.HitTest(event.GetPosition()))[0]
        if index != -1:
            event.Skip()
            return

        menu = EtcMenu()
        menu.Append("添加项目", self.menu_add_project)
        menu.AppendSeparator()
        menu.Append("清空所有项目", self.menu_clear_all_projects)
        self.PopupMenu(menu)

    def check_active_theme(self):
        if self.active_theme is None:
            wx.MessageBox("请先选择一个主题", "错误", wx.ICON_ERROR)
            return False
        return True

    def menu_copy_project(self, project: CursorProject):
        if not self.check_active_theme():
            return
        data_dict = deepcopy(project.to_dict())
        new_project = CursorProject.from_dict(data_dict)
        new_project.name += " (New)"
        if new_project.external_name is not None:
            new_project.external_name += " (New)"
        self.active_theme.projects.append(new_project)
        self.reload_theme()

    def menu_edit_projects(self, projects: list[CursorProject]):
        for project in projects:
            editor = CursorEditor(self, project)
            editor.Show()
            editor.Bind(wx.EVT_CLOSE, self.on_editor_close)

    def on_editor_close(self, event: wx.CloseEvent):
        self.load_theme(self.active_theme)
        event.Skip()

    def menu_add_project(self):
        if not self.check_active_theme():
            return
        dialog = ProjectDataDialog(self)
        if dialog.ShowModal() == wx.ID_OK:
            name, external_name, size, kind = dialog.get_result()
            project = CursorProject(name, (size, size))
            project.kind = kind
            project.external_name = external_name
            self.active_theme.projects.append(project)
            self.reload_theme()

    def menu_edit_project_info(self, projects: list[CursorProject], active_project: CursorProject | None = None):
        if not self.check_active_theme():
            return
        if len(projects) == 1:
            project = projects[0]
            dialog = ProjectDataDialog(self, False, project.name, project.external_name, project.raw_canvas_size,
                                       project.kind)
            if dialog.ShowModal() == wx.ID_OK:
                name, external_name, size, kind = dialog.get_result()
                project.name = name
                project.external_name = external_name
                project.raw_canvas_size = size
                project.kind = kind
                self.reload_theme()
        else:
            dialog = MutilProjectDataDialog(self, active_project.raw_canvas_size)
            if dialog.ShowModal() == wx.ID_OK:
                (enable_size, size_w, size_h), (enable_scale, scale) = dialog.get_result()
                if enable_size:
                    for project in projects:
                        project.raw_canvas_size = (size_w, size_h)
                if enable_scale:
                    for project in projects:
                        project.scale = scale
                self.reload_theme()

    def menu_delete_projects(self, projects: list[CursorProject]):
        if not self.check_active_theme():
            return
        for project in projects:
            self.active_theme.projects.remove(project)
        self.reload_theme()

    def menu_clear_all_projects(self):
        if not self.check_active_theme():
            return
        ret = wx.MessageBox("真的要清空所有项目吗?", "清理确认", wx.ICON_WARNING | wx.YES_NO)
        if ret != wx.YES:
            return
        self.active_theme.projects.clear()
        self.reload_theme()

    def reload_theme(self):
        self.load_theme(self.active_theme)


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
    #     theme.projects.append(deepcopy(project))
    # theme_manager.add_theme(theme)
    # frame.theme_selector.reload_themes()

    app.MainLoop()


if __name__ == "__main__":
    test_editor()
