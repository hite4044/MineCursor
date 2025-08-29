import wx

from lib.ui_interface import ui_class
from ui.public_list_ctl import PublicThemeCursorListUI, PublicThemeSelectorUI
from widget.font import ft



class ThemeEditorUI(wx.Frame):
    def __init__(self, parent: wx.Window | None):
        super().__init__(parent, title="Mine Cursor", size=(1166, 625))
        self.SetFont(ft(11))

        self.splitter = wx.SplitterWindow(self)
        self.theme_selector = ui_class(ThemeSelectorUI)(self.splitter)
        self.cursor_list_outbox = wx.Panel(self.splitter)
        self.cursor_list = ui_class(ThemeCursorListUI)(self.cursor_list_outbox)
        self.cursor_list_outbox.SetBackgroundColour(self.cursor_list.GetBackgroundColour())
        list_sizer = wx.BoxSizer(wx.VERTICAL)
        list_sizer.Add(self.cursor_list, 1, wx.EXPAND | wx.TOP, 15)
        self.cursor_list_outbox.SetSizer(list_sizer)

        self.splitter.SplitVertically(self.theme_selector, self.cursor_list_outbox)
        self.splitter.SetSashPosition(450)
        wx.CallLater(500, self.splitter.SetMinimumPaneSize, 50)


class ThemeSelectorUI(PublicThemeSelectorUI):
    pass


class ThemeCursorListUI(PublicThemeCursorListUI):
    pass
