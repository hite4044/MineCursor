import wx

from lib.data import CursorProject
from widget.editable_listctrl import EditableListCtrl


class RateEditor(wx.Dialog):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, title="帧率编辑", size=(320, 670), style=wx.DEFAULT_FRAME_STYLE)
        assert project.frame_count is not None
        self.SetFont(parent.GetFont())

        self.project = project
        if project.ani_rates:
            self.rates = project.ani_rates + [project.ani_rate] * (project.frame_count - len(project.ani_rates))
        else:
            self.rates = [project.ani_rate] * project.frame_count

        self.list = EditableListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.AppendColumn("帧数")
        self.list.AppendColumn("帧率")
        self.list.EnableColumnEdit(1)
        self.list.on_data_changed = self.update_data
        self.full_data()
        self.clear_btn = wx.Button(self.list, label="清空帧率")

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        ver_sizer = wx.BoxSizer(wx.VERTICAL)
        ver_sizer.AddStretchSpacer()
        ver_sizer.Add(self.clear_btn, 0, wx.ALL, 5)
        sizer.AddStretchSpacer()
        sizer.Add(ver_sizer, 0, wx.EXPAND)
        self.list.SetSizer(sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="选中后上下键移动, 点击悬停编辑"), 0, wx.EXPAND)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.clear_data)

    def clear_data(self, _):
        self.project.ani_rates = None
        self.list.DeleteAllItems()

    def full_data(self):
        self.list.DeleteAllItems()
        for i, rate in enumerate(self.rates):
            self.list.InsertItem(i, str(i + 1))
            self.list.SetItem(i, 1, str(rate))
            if i > self.project.frame_count:
                self.list.SetItemBackgroundColour(i, wx.Colour(225, 255, 225))

    def exchange_item(self, index1: int, index2: int):
        self.rates[index1], self.rates[index2] = self.rates[index2], self.rates[index1]
        self.update_data()

    def update_data(self, row=None, col=None, value=None):
        if row:
            self.rates[row] = int(value)
        print(self.rates)
        self.project.ani_rates = self.rates
        self.full_data()

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