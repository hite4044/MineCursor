from copy import deepcopy
from enum import Enum
from typing import cast

import wx
from PIL.Image import Resampling

from lib.clipboard import ClipBoard
from lib.cursor.setter import CURSOR_KIND_NAME_CUTE, CURSOR_KIND_NAME_OFFICIAL, CursorKind
from lib.data import CursorTheme, CursorProject
from lib.image_pil2wx import PilImg2WxImg
from lib.log import logger
from lib.render import render_project_frame
from lib.resources import theme_manager
from ui.public_list_ctl import PublicThemeCursorListUI, PublicThemeSelectorUI
from ui_ctl.cursor_editor import CursorEditor
from widget.data_dialog import DataLineParam, DataDialog, DataLineType
from widget.ect_menu import EtcMenu
from widget.win_icon import set_multi_size_icon

mcEVT_THEME_SELECTED = wx.NewEventType()
EVT_THEME_SELECTED = wx.PyEventBinder(mcEVT_THEME_SELECTED)


class ThemeSelectedEvent(wx.PyCommandEvent):
    def __init__(self, theme: CursorTheme):
        super().__init__(mcEVT_THEME_SELECTED)
        self.theme = theme


class PublicThemeSelector(PublicThemeSelectorUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.clip = ClipBoard(self, self.clip_on_get_copy_data, self.clip_on_set_copy_data)
        self.line_theme_mapping: dict[int, CursorTheme] = {}
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)

    def clip_on_get_copy_data(self):
        item = self.GetFirstSelected()
        return None if item == -1 else theme_manager.themes[item].id

    def clip_on_set_copy_data(self, theme_id: str):
        if theme := theme_manager.find_theme(theme_id):
            theme_manager.themes.append(theme.copy())
            self.reload_themes()

    def on_data_changed(self, row: int, col: int, value: str):
        self.line_theme_mapping[row].name = value
        theme_manager.renew_theme(self.line_theme_mapping[row])
        theme_manager.save()

    def load_all_theme(self):
        self.DeleteAllItems()
        self.line_theme_mapping.clear()
        for theme in theme_manager.themes:
            self.append_theme(theme)

    def reload_themes(self):
        self.load_all_theme()

        theme_manager.save()  # 经过测试，这行代码会在执行完菜单项里所绑定的函数过后才会之心

    def append_theme(self, theme: CursorTheme):
        line = self.GetItemCount()
        index = self.InsertItem(line, theme.name)
        self.SetItem(index, 1, str(theme.base_size))
        self.SetItem(index, 2, theme.author)
        self.SetItem(index, 3, theme.description)
        self.line_theme_mapping[index] = theme

    def on_item_selected(self, event: wx.ListEvent):
        event.Skip()
        theme = self.line_theme_mapping[event.GetIndex()]
        logger.debug(f"主题被选择: {theme}")
        wx.PostEvent(self, ThemeSelectedEvent(theme))


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
                         DataLineParam("name", "项目名称", DataLineType.STRING, name if name else ""),
                         DataLineParam("external_name", "展示名称", DataLineType.STRING,
                                       external_name if external_name else ""),
                         *self.canvas_params,
                         DataLineParam("kind", "类型", DataLineType.CHOICE, kind,
                                       enum_names=CURSOR_KIND_NAME_OFFICIAL))
        if is_create:
            self.set_icon("project/add.png")
        else:
            self.set_icon("project/edit_info.png")

    def get_result(self) -> tuple[str | str, str | None, int | tuple[int, int], CursorKind]:
        datas = self.datas
        if len(self.canvas_params) == 1:
            size = datas["canvas_size"]
        else:
            size = (datas["size_width"], datas["size_height"])
        result = [datas["name"], datas["external_name"] if datas["external_name"] else None, size, datas["kind"]]
        if datas["name"] == "":
            result[0] = None
        return cast(tuple[str, str | None, int | tuple[int, int], CursorKind], tuple(result))


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
        self.set_icon("project/add.png")

        self.entries[1].set_depend(self.entries[0])
        self.entries[2].set_depend(self.entries[0])
        self.entries[4].set_depend(self.entries[3])

    def get_result(self) -> tuple[tuple[bool, int, int], tuple[bool, float]]:
        datas = self.datas
        return (datas["edit_size"], datas["size_width"], datas["size_height"]), (datas["edit_scale"], datas["scale"])


class ProjectCopyDialog(DataDialog):
    def __init__(self, parent: wx.Window | None, project: CursorProject):
        self.project = project
        super().__init__(parent, "复制指针项目",
                         DataLineParam("kind", "类型", DataLineType.CHOICE, project.kind,
                                       enum_names=CURSOR_KIND_NAME_OFFICIAL)
                         )
        self.set_icon("project/copy.png")

    def get_result(self) -> CursorProject:
        data_dict = deepcopy(self.project.to_dict())
        new_project = CursorProject.from_dict(data_dict)
        new_project.kind = cast(CursorKind, self.datas["kind"])
        return new_project


class ProjectMoveThemeDialog(DataDialog):
    def __init__(self, parent: wx.Window, active_theme: CursorTheme):
        self.themes_enum_cls = Enum("ThemesEnum", tuple(theme.id for theme in theme_manager.themes))
        self.enum_to_theme_map = {self.themes_enum_cls[theme.id]: theme for theme in theme_manager.themes}
        super().__init__(parent, "移动指针项目至其他主题",
                         DataLineParam("theme", "目标主题", DataLineType.CHOICE,
                                       getattr(self.themes_enum_cls, active_theme.id),
                                       enum_names={ \
                                           getattr(self.themes_enum_cls, theme.id): \
                                               f"{theme.name} ({len(theme.projects)}-cur)" \
                                           for theme in theme_manager.themes}))
        self.set_icon("project/move.png")

    def get_result(self) -> CursorTheme:
        return self.enum_to_theme_map[self.datas["theme"]]


ActionStack = list[tuple[int, CursorProject]]


def mk_end(li: list):
    if len(li) > 1:
        return f" ({len(li)})"
    return ""


class PublicThemeCursorList(PublicThemeCursorListUI):
    ICON_SIZE = 96

    def __init__(self, parent: wx.Window):
        super().__init__(parent)

        self.use_cute_name: bool = True
        self.image_list = wx.ImageList()
        self.active_theme: CursorTheme | None = None
        self.cursors_has_deleted_map: dict[CursorTheme, list[ActionStack]] = {}
        self.cursors_has_deleted: list[ActionStack] = []

        if self.EDITABLE:
            self.Bind(wx.EVT_RIGHT_DOWN, self.on_empty_menu, self)
            self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_menu, self)
            self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated, self)

            self.Bind(wx.EVT_KEY_DOWN, self.on_key_down, self)

        self.clip = ClipBoard(self, self.clip_on_get_copy_data, self.clip_on_set_copy_data)

    def clip_on_get_copy_data(self):
        if not self.check_active_theme():
            return None
        item = self.GetFirstSelected()
        return None if item == -1 else self.active_theme.projects[item].id

    def clip_on_set_copy_data(self, project_id: str):
        if project := theme_manager.find_project(project_id):
            self.active_theme.projects.append(project.copy())
            self.reload_theme()

    def on_key_down(self, event: wx.KeyEvent):
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.menu_delete_projects(projects=[self.active_theme.projects[i] for i in self.get_select_items()])
        elif event.GetKeyCode() == ord("Z") and event.GetModifiers() == wx.MOD_CONTROL:
            self.undo_action()
        elif event.GetKeyCode() == wx.WXK_UP and event.GetModifiers() == wx.MOD_SHIFT:
            self.move_project(self.get_select_items()[0], -1)
        elif event.GetKeyCode() == wx.WXK_DOWN and event.GetModifiers() == wx.MOD_SHIFT:
            self.move_project(self.get_select_items()[0], 1)
        else:
            event.Skip()

    def undo_action(self):
        if not self.check_active_theme():
            return
        if len(self.cursors_has_deleted) == 0:
            return
        stacks = self.cursors_has_deleted.pop(-1)
        for index, project in stacks[::-1]:
            self.active_theme.projects.insert(index, project)
        self.reload_theme()

    def clear(self):
        self.image_list.RemoveAll()
        self.image_list.Destroy()
        self.DeleteAllItems()

    def load_projects(self, projects: list[CursorProject]):
        self.clear()

        size = self.ICON_SIZE
        self.image_list = wx.ImageList(size, size)
        self.AssignImageList(self.image_list, wx.IMAGE_LIST_NORMAL)
        for i, project in enumerate(projects):
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

    def on_empty_menu(self, event: wx.MouseEvent):
        index = cast(tuple[int, int], self.HitTest(event.GetPosition()))[0]
        if index != -1:
            event.Skip()
            return

        menu = EtcMenu()
        menu.Append("添加项目 (&A)", self.menu_add_project, icon="project/add.png")
        menu.AppendSeparator()
        if len(self.cursors_has_deleted) != 0:
            menu.Append("撤销操作 (&Z)", self.undo_action, icon="action/undo.png")
            menu.AppendSeparator()
        menu.Append("清空所有项目 (&D)", self.menu_clear_all_projects, icon="action/delete.png")
        self.PopupMenu(menu)

    def on_item_menu(self, event: wx.ListEvent):  # 当鼠标右键某个项目时触发
        active_project = self.active_theme.projects[event.GetIndex()]
        projects = [self.active_theme.projects[i] for i in self.get_select_items()]
        menu = EtcMenu()
        menu.Append("添加项目 (&A)", self.menu_add_project, icon="project/add.png")
        menu.AppendSeparator()
        menu.Append("编辑项目 (&E)" + mk_end(projects), self.menu_edit_projects, projects, icon="project/edit.png")
        menu.Append("编辑项目信息 (&I)" + mk_end(projects), self.menu_edit_project_info, projects, active_project, icon="project/edit_info.png")
        if len(projects) == 1 and len(self.active_theme.projects) != 1:
            menu.AppendSeparator()
            if event.GetIndex() != 0:
                menu.Append("向上移动 (&W)", self.move_project, event.GetIndex(), -1, icon="action/up.png")
            if event.GetIndex() != len(self.active_theme.projects) - 1:
                menu.Append("向下移动 (&S)", self.move_project, event.GetIndex(), 1, icon="action/down.png")
        if len(projects) == 1:
            menu.AppendSeparator()
            menu.Append("复制项目 (&C)", self.menu_copy_project, active_project, icon="project/copy.png")
        menu.AppendSeparator()
        menu.Append("移动至其他主题 (&M)" + mk_end(projects), self.move_project_to_theme, projects, icon="project/move.png")
        if len(self.cursors_has_deleted) != 0:
            menu.Append("撤销操作 (&Z)", self.undo_action, icon="action/undo.png")
        menu.AppendSeparator()
        menu.Append("删除 (&D)" + mk_end(projects), self.menu_delete_projects, projects, icon="action/delete.png")

        self.PopupMenu(menu)

    def move_project_to_theme(self, projects: list[CursorProject]):
        if not self.check_active_theme():
            return
        dialog = ProjectMoveThemeDialog(self, self.active_theme)
        if dialog.ShowModal() == wx.ID_OK:
            theme = dialog.get_result()
            theme.projects.extend([project.copy() for project in projects])
            self.reload_theme()

    def move_project(self, index: int, offset: int):
        if not self.check_active_theme():
            return
        if not (0 <= index + offset < len(self.active_theme.projects)):
            return
        project = self.active_theme.projects[index]
        self.active_theme.projects.pop(index)
        self.active_theme.projects.insert(index + offset, project)
        self.reload_theme()
        self.Select(index + offset)

    def menu_add_project(self):  # 新建一个项目
        if not self.check_active_theme():
            return
        dialog = ProjectDataDialog(self, size=self.active_theme.base_size)
        if dialog.ShowModal() == wx.ID_OK:
            name, external_name, size, kind = dialog.get_result()
            project = CursorProject(name, (size, size))
            project.kind = kind
            project.external_name = external_name
            self.active_theme.projects.append(project)
            self.reload_theme()

    def menu_edit_projects(self, projects: list[CursorProject]):  # 打开项目的编辑器
        for project in projects:
            editor = CursorEditor(self, project)
            editor.Show()
            editor.Bind(wx.EVT_CLOSE, self.on_editor_close)

    def menu_edit_project_info(self, projects: list[CursorProject],
                               active_project: CursorProject | None = None):  # 编辑列表中的项目信息
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
            dialog = MutilProjectDataDialog(self, active_project.raw_canvas_size, active_project.scale)
            if dialog.ShowModal() == wx.ID_OK:
                (enable_size, size_w, size_h), (enable_scale, scale) = dialog.get_result()
                if enable_size:
                    for project in projects:
                        project.raw_canvas_size = (size_w, size_h)
                if enable_scale:
                    for project in projects:
                        project.scale = scale
                self.reload_theme()

    def menu_copy_project(self, project: CursorProject):  # 复制列表中的一个项目
        if not self.check_active_theme():
            return
        dialog = ProjectCopyDialog(self, project)
        if dialog.ShowModal() == wx.ID_OK:
            new_project = dialog.get_result()
            self.active_theme.projects.append(new_project)
            self.reload_theme()

    def menu_delete_projects(self, projects: list[CursorProject]):  # 从列表中删除多个项目
        if not self.check_active_theme():
            return
        stacks = []
        for project in projects[::-1]:  # 倒序以便保存的操作索引正确
            stacks.append((self.active_theme.projects.index(project), project))
            self.active_theme.projects.remove(project)
        self.cursors_has_deleted.append(stacks)
        self.reload_theme()

    def menu_clear_all_projects(self):  # 清空所有项目
        if not self.check_active_theme():
            return
        ret = wx.MessageBox("真的要清空所有项目吗?", "清理确认", wx.ICON_WARNING | wx.YES_NO)
        if ret != wx.YES:
            return
        self.active_theme.projects.clear()
        self.reload_theme()

    def on_editor_close(self, event: wx.CloseEvent):
        self.load_theme(self.active_theme)
        event.Skip()

    def load_theme(self, theme: CursorTheme | None):
        self.cursors_has_deleted_map[self.active_theme] = self.cursors_has_deleted.copy()
        if theme in self.cursors_has_deleted_map:
            self.cursors_has_deleted = self.cursors_has_deleted_map[theme]
        else:
            self.cursors_has_deleted.clear()

        self.active_theme = theme
        if theme is None:
            self.image_list.RemoveAll()
            self.image_list.Destroy()
            self.DeleteAllItems()
        else:
            self.load_projects(theme.projects)

    def check_active_theme(self):
        if self.active_theme is None:
            wx.MessageBox("请先选择一个主题", "错误", wx.ICON_ERROR)
            return False
        return True

    def reload_theme(self):
        self.load_theme(self.active_theme)
        theme_manager.save()

    def on_item_activated(self, event: wx.ListEvent):
        active_project = self.active_theme.projects[event.GetIndex()]
        self.menu_edit_projects([active_project])
