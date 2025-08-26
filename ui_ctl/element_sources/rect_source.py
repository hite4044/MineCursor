import wx
from PIL import Image

from lib.data import CursorElement, AssetSourceInfo, AssetType
from ui.element_add_dialog import RectElementSourceUI


class RectElementSource(RectElementSourceUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.name.set_value("矩形")
        self.size_width.set_value(16)
        self.size_height.set_value(16)
        self.color_r.set_value(255)
        self.color_g.set_value(255)
        self.color_b.set_value(255)
        self.color_a.set_value(255)
        self.picker.SetColour(wx.Colour(255, 255, 255))
        self.picker.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_pick_color)

    def on_pick_color(self, event: wx.Event):
        event.Skip()
        color = self.picker.GetColour()
        self.color_r.set_value(color.Red())
        self.color_g.set_value(color.Green())
        self.color_b.set_value(color.Blue())

    def get_element(self):
        size = (self.size_width.data, self.size_height.data)
        color = (self.color_r.data, self.color_g.data, self.color_b.data, self.color_a.data)
        frame = Image.new("RGBA", size, color)
        return CursorElement(self.name.data, [frame], [AssetSourceInfo(AssetType.RECT, size=size, color=color)])
