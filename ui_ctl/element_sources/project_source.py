import wx
from PIL import Image

from lib.data import CursorElement, CursorProject, AssetSourceInfo, AssetType, SubProjectFrames
from widget.data_entry import StringEntry, IntEntry


class ProjectSource(wx.Panel):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.name = StringEntry(self, "名称")
        self.size_width = IntEntry(self, "宽度")
        self.size_height = IntEntry(self, "高度")

        self.name.set_value("新子项目")
        self.size_width.set_value(32)
        self.size_height.set_value(32)

        sizer = wx.FlexGridSizer(4, 2, 5, 5)
        sizer.AddGrowableCol(1, 1)
        widgets = [
            self.name,
            self.size_width,
            self.size_height
        ]
        for widget in widgets:
            sizer.Add(widget.label, 0, wx.EXPAND)
            sizer.Add(widget.entry, 1, wx.EXPAND)
        sizer.Add(wx.Window(self))
        sizer.AddGrowableRow(3, 1)
        self.SetSizer(sizer)

    def get_element(self):
        element = CursorElement(self.name.data, [])
        element.create_sub_project(self.name.data, (self.size_width.data, self.size_height.data))
        return element
