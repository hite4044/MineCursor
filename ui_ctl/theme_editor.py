from copy import deepcopy
from typing import cast

import wx
from PIL import Image
from PIL.Image import Resampling

from lib.cursor_setter import CURSOR_KIND_NAME_OFFICIAL, CURSOR_KIND_NAME_CUTE, CursorKind
from lib.data import CursorTheme, CursorProject, CursorElement, Position, Scale2D
from lib.data_manager import theme_manager
from lib.image_pil2wx import PilImg2WxImg
from lib.render import render_project_frame
from ui.theme_editor import ThemeEditorUI, ThemeCursorListUI, ThemeSelectorUI
from ui.widget.data_dialog import DataDialog, DataLineParam, DataLineType
from ui.widget.ect_menu import EtcMenu
from ui.widget.win_icon import set_multi_size_icon

mcEVT_THEME_SELECTED = wx.NewEventType()
EVT_THEME_SELECTED = wx.PyEventBinder(mcEVT_THEME_SELECTED)


class ThemeSelectedEvent(wx.PyCommandEvent):
    def __init__(self, theme: CursorTheme):
        super().__init__(mcEVT_THEME_SELECTED)
        self.theme = theme


def get_user_name() -> str:
    import getpass
    return getpass.getuser()


USER_NAME = get_user_name()


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


class ThemeSelector(ThemeSelectorUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.line_theme_mapping: dict[int, CursorTheme] = {}

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_menu)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu)

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
        menu.Append("编辑数据", self.on_edit_theme, theme)
        menu.AppendSeparator()
        menu.Append("删除", self.on_delete_theme, theme)
        self.PopupMenu(menu)

    def on_menu(self, event: wx.MouseEvent):
        index = cast(tuple[int, int], self.HitTest(event.GetPosition()))[0]
        if index != -1:
            event.Skip()
            return

        menu = EtcMenu()
        menu.Append("添加", self.on_add_theme)
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
        theme_manager.remove_theme(theme)
        self.reload_themes()

    def on_clear_all_theme(self):
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
            target_name = f"{DEFAULT_NAME} ({line+1})" if line != 0 else DEFAULT_NAME
            if target_name not in names:
                return target_name
        return f"{DEFAULT_NAME} ({line+1})"

    def on_item_selected(self, event: wx.ListEvent):
        theme = self.line_theme_mapping[event.GetIndex()]
        wx.PostEvent(self, ThemeSelectedEvent(theme))

    def append_theme(self, theme: CursorTheme):
        line = self.GetItemCount()
        index = self.InsertItem(line, theme.name)
        self.SetItem(index, 1, str(theme.base_size))
        self.SetItem(index, 2, theme.author)
        self.SetItem(index, 3, theme.description)
        self.line_theme_mapping[index] = theme


class ThemeCursorList(ThemeCursorListUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.image_list = wx.ImageList()
        self.use_cute_name: bool = True

    def load_theme(self, theme: CursorTheme):
        size = theme.base_size * 3
        self.image_list.RemoveAll()
        self.image_list.Destroy()
        self.image_list = wx.ImageList(size, size)
        self.AssignImageList(self.image_list, wx.IMAGE_LIST_NORMAL)
        self.DeleteAllItems()
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


def test_editor():
    app = wx.App()
    frame = ThemeEditor(None)
    frame.Show()

    theme = CursorTheme("Test Theme")
    project = CursorProject("Sword Loading", (32, 32))
    project.scale = 2.0
    project.is_ani_cursor = True
    project.frame_count = 64
    project.ani_rate = 50
    project.add_element(
        CursorElement("Diamond Sword", [Image.open("diamond_sword.png").convert("RGBA")], scale=Scale2D(2.0, 2.0),
                      reverse_x=True))

    element = CursorElement("Clock", [])
    element.position = Position(17, 0)
    for f_index in range(64):
        fp = rf"assets_test\clock_{str(f_index).zfill(2)}.png"
        element.frames.append(Image.open(fp).convert("RGBA"))
    element.animation_key_data.frame_length = 64
    element.update_ani_data_by_key_data()
    project.add_element(element)

    for member in CursorKind:
        project.kind = member
        theme.projects.append(deepcopy(project))
    theme_manager.add_theme(theme)
    frame.theme_selector.reload_themes()

    app.MainLoop()


if __name__ == "__main__":
    test_editor()
