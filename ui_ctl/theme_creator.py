import wx

from lib.data import CursorTheme
from lib.resources import theme_manager
from ui.theme_creator import ThemeCreatorUI, CursorsSelectorUI, SourceThemeCursorListUI, NewThemeCursorListUI
from ui_ctl.public_list_ctl import EVT_THEME_SELECTED, PublicThemeSelector
from widget.center_text import CenteredText
from widget.win_icon import set_multi_size_icon


class ThemeCreator(ThemeCreatorUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        set_multi_size_icon(self, "assets/icons/theme/merge.png")

    def on_ok(self, _):
        theme = self.main_panel.new_cursors.active_theme
        theme_manager.themes.append(theme)
        self.EndModal(wx.ID_OK)


class CursorsSelector(CursorsSelectorUI):
    theme_selector: PublicThemeSelector
    source_cursors: 'SourceThemeCursorList'
    new_cursors: 'NewThemeCursorList'

    def __init__(self, parent: ThemeCreator):
        super().__init__(parent)
        self.theme_selector.load_all_theme()
        self.theme_selector.Bind(EVT_THEME_SELECTED, lambda e: self.source_cursors.load_theme(e.theme))


class SourceThemeCursorList(SourceThemeCursorListUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.drop_data = None

        self.drop_source = wx.DropSource(self)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnDragInit)

    def OnDragInit(self, _):
        if not self.check_active_theme():
            return
        projects = [self.active_theme.projects[i] for i in self.get_select_items()]
        self.drop_data = wx.TextDataObject(", ".join(project.id for project in projects))
        self.drop_source.SetData(self.drop_data)
        self.drop_source.DoDragDrop(True)


class DropTarget(wx.TextDropTarget):
    def __init__(self, cbk):
        wx.TextDropTarget.__init__(self)
        self.cbk = cbk

    def OnDropText(self, x, y, data):
        self.cbk(data)
        return True


class NewThemeCursorList(NewThemeCursorListUI):

    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.active_theme = CursorTheme("新鼠标主题", 32)

        self.drop_target = DropTarget(self.OnDropText)
        self.SetDropTarget(self.drop_target)

        self.tip = CenteredText(self, label="拖放添加指针", style=wx.TRANSPARENT_WINDOW)
        hor_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hor_sizer.AddStretchSpacer()
        hor_sizer.Add(self.tip, 0, wx.LEFT | wx.RIGHT, 5)
        ver_sizer = wx.BoxSizer(wx.VERTICAL)
        ver_sizer.AddStretchSpacer()
        ver_sizer.Add(hor_sizer, 0, wx.TOP | wx.BOTTOM, 5)
        self.SetSizer(ver_sizer)

    def OnDropText(self, data: str):
        projects = data.split(", ")
        for project_id in projects:
            if project := theme_manager.find_project(project_id):
                self.active_theme.projects.append(project.copy())
            self.reload_theme()
