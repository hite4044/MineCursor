import wx

from widget.editable_listctrl import EditableListCtrl


class PublicThemeCursorListUI(wx.ListCtrl):
    USE_APPLY_BTN = True
    EDITABLE = True

    def __init__(self, parent: wx.Window):
        super().__init__(parent, style=wx.LC_ICON | wx.NO_BORDER)
        if not self.USE_APPLY_BTN:
            return

        self.apply_theme_btn = wx.Button(self, label="应用")

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.apply_theme_btn, 0)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)


class PublicThemeSelectorUI(EditableListCtrl):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, style=wx.LC_REPORT | wx.NO_BORDER)

        self.InsertColumn(1, "主题", width=180)
        self.AppendColumn("大小", width=50, format=wx.LIST_FORMAT_CENTER)
        self.AppendColumn("作者", width=100)
        self.AppendColumn("描述", width=300)

        self.EnableColumnEdit(0)
