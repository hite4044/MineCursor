import wx

from lib.data import CursorProject
from widget.editable_listctrl import EditableListCtrl


class RateEditor(wx.Frame):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, title="帧率编辑", size=(320, 670), style=wx.DEFAULT_FRAME_STYLE)
        assert project.frame_count is not None
        self.SetFont(parent.GetFont())

        self.project = project
        self.rates = []

        self.list = EditableListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, open_delay=200)
        self.list.AppendColumn("帧数", width=50)
        self.list.AppendColumn("时间", width=100)
        self.list.AppendColumn("帧率")
        self.list.EnableColumnEdit(2)
        self.list.on_data_changed = self.update_data
        if project.ani_rates:
            self.load_default(None)
            self.full_data()
        self.default_btn = wx.Button(self.list, label="加载默认")
        self.clear_btn = wx.Button(self.list, label="清空帧率")

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        ver_sizer = wx.BoxSizer(wx.VERTICAL)
        ver_sizer.AddStretchSpacer()
        ver_sizer.Add(self.default_btn, 0, wx.ALL, 5)
        ver_sizer.Add(self.clear_btn, 0, wx.ALL, 5)
        sizer.AddStretchSpacer()
        sizer.Add(ver_sizer, 0, wx.EXPAND)
        self.list.SetSizer(sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        tip = wx.StaticText(self, label="选中后上下键移动, 点击悬停编辑")
        tip.SetBackgroundColour(self.list.GetBackgroundColour())
        sizer.Add(tip, 0, wx.EXPAND)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.clear_data)
        self.default_btn.Bind(wx.EVT_BUTTON, self.load_default)

    def load_default(self, _):
        project = self.project
        if project.ani_rates:
            self.rates = project.ani_rates + [project.ani_rate] * (project.frame_count - len(project.ani_rates))
        else:
            self.rates = [project.ani_rate] * project.frame_count
        self.full_data()
        self.apply_to_project()

    def clear_data(self, _):
        self.rates = []
        self.project.ani_rates = None
        self.list.DeleteAllItems()

    def full_data(self):
        select_now = self.list.GetFirstSelected()
        scroll_value = self.list.GetScrollPos(wx.VERTICAL)
        self.list.DeleteAllItems()
        for i, rate in enumerate(self.rates):
            self.list.InsertItem(i, str(i + 1))
            self.list.SetItem(i, 1, f"{rate / 60 * 1000:.1f} ms")
            self.list.SetItem(i, 2, str(rate))
            if i > self.project.frame_count:
                self.list.SetItemBackgroundColour(i, wx.Colour(225, 255, 225))
        self.list.Refresh()
        self.list.ScrollLines(scroll_value)
        self.list.EnsureVisible(select_now)
        self.list.Select(select_now)

    def exchange_item(self, index1: int, index2: int):
        self.rates[index1], self.rates[index2] = self.rates[index2], self.rates[index1]
        self.update_data()

    def update_data(self, row=None, col=None, value=None):
        if row is not None:
            self.rates[row] = int(value)
            self.list.SetItem(row, 1, f"{int(value) / 60 * 1000:.1f} ms")
        else:
            self.full_data()
        self.apply_to_project()

    def apply_to_project(self):
        if not self.rates:
            self.project.ani_rates = None
        else:
            self.project.ani_rates = self.rates

    def on_key(self, event: wx.KeyEvent):
        item_selected = self.list.GetFirstSelected() if self.list.GetFirstSelected() != wx.NOT_FOUND else None
        if event.GetKeyCode() == wx.WXK_UP and \
                item_selected is not None and item_selected > 0:
            self.exchange_item(item_selected, item_selected - 1)
            self.list.Select(item_selected - 1)
        elif event.GetKeyCode() == wx.WXK_DOWN and \
                item_selected is not None and item_selected < self.list.GetItemCount() - 1:
            self.exchange_item(item_selected, item_selected + 1)
            self.list.Select(item_selected + 1)
        else:
            event.Skip()