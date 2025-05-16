import wx

from lib.ui_interface import ui_class
from ui.widget.font import ft


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
        list_sizer.Add(self.cursor_list, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 15)
        self.cursor_list_outbox.SetSizer(list_sizer)

        self.splitter.SplitVertically(self.theme_selector, self.cursor_list_outbox)
        self.splitter.SetSashPosition(450)
        wx.CallLater(500, self.splitter.SetMinimumPaneSize, 50)


class ThemeCursorListUI(wx.ListView):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, style=wx.LC_ICON | wx.NO_BORDER)

        self.apply_theme_btn = wx.Button(self, label="应用")

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.apply_theme_btn, 0)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

class ThemeSelectorUI(wx.ListCtrl):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, style=wx.LC_REPORT | wx.NO_BORDER)

        self.InsertColumn(1, "主题", width=180)
        self.AppendColumn("大小", width=50, format=wx.LIST_FORMAT_CENTER)
        self.AppendColumn("作者", width=100)
        self.AppendColumn("描述", width=300)
