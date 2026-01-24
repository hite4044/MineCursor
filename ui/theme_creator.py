from typing import cast

import wx

from lib.dialog_fix import register_close
from lib.dpi import TS
from lib.ui_interface import ui_class
from ui.theme_editor import PublicThemeSelectorUI
from ui_ctl.public_list_ctl import PublicThemeCursorList
from widget.center_text import CenteredText
from widget.widget_pad import PadDir, pad


class ThemeCreatorUI(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, size=TS(1120, 715), title="合成主题", style=wx.DEFAULT_FRAME_STYLE)
        self.SetFont(parent.GetFont())

        self.ok_btn = wx.Button(self, label="确定")
        self.main_panel = ui_class(CursorsSelectorUI)(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.main_panel, 1, wx.EXPAND)
        self.SetSizer(sizer)

        size_cbk = pad(self.ok_btn, PadDir.LEFT_RIGHT)
        self.main_panel.new_cursors.Bind(wx.EVT_PAINT, size_cbk)
        register_close(self)


class CursorsSelectorUI(wx.SplitterWindow):
    def __init__(self, parent: ThemeCreatorUI):
        super().__init__(parent)

        self.theme_selector = ui_class(PublicThemeSelectorUI)(self)
        self.theme_selector.FORCE_FULL_THEME = True
        self.cursors_con = wx.SplitterWindow(self)
        self.source_con = wx.Panel(self.cursors_con)
        self.source_cursors = ui_class(SourceThemeCursorListUI)(self.source_con)
        self.new_con = wx.Panel(self.cursors_con)
        self.new_cursors = ui_class(NewThemeCursorListUI)(self.new_con)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(CenteredText(self.source_con, label="可用指针"), 0, wx.EXPAND)
        sizer.Add(self.source_cursors, 1, wx.EXPAND)
        self.source_con.SetSizer(sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(CenteredText(self.new_con, label="合成指针"), 0, wx.EXPAND)
        sizer.Add(self.new_cursors, 1, wx.EXPAND)
        self.new_con.SetSizer(sizer)

        self.cursors_con.SetSashGravity(0.5)
        self.cursors_con.SplitVertically(self.source_con, self.new_con)

        self.SplitVertically(self.theme_selector, self.cursors_con, 450)


class SourceThemeCursorListUI(PublicThemeCursorList):
    USE_APPLY_BTN = False
    ICON_SIZE = 64
    EDITABLE = False

    def __init__(self, parent: wx.Window):
        super().__init__(parent)


class NewThemeCursorListUI(PublicThemeCursorList):
    USE_APPLY_BTN = False
    ICON_SIZE = 64

    def __init__(self, parent: wx.Window):
        super().__init__(parent)
