import wx


class CenteredText(wx.Window):
    """使得绘制的文字始终保持在控件中央"""

    def __init__(
            self,
            parent,
            id_=wx.ID_ANY,
            label=wx.EmptyString,
            pos=wx.DefaultPosition,
            size=wx.DefaultSize,
            style=0,
            name=wx.StaticTextNameStr,
            x_center=True,
            y_center=True,
    ):
        super().__init__(parent, id_, pos, size, style, name)
        self.SetLabel(label)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.x_center = x_center
        self.y_center = y_center

    def SetLabel(self, label):
        super().SetLabel(label)
        dc = wx.ClientDC(self)
        size = wx.Size(*(dc.GetFullMultiLineTextExtent(label, self.GetFont())[:2]))
        self.SetSize(size)
        self.CacheBestSize(size)
        self.SetMinSize(size)
        self.Refresh()

    def on_paint(self, _):
        dc = wx.PaintDC(self)
        dc.Clear()
        label = self.GetLabel()
        dc.SetFont(self.GetFont())
        text_size = dc.GetTextExtent(label)
        size = self.GetSize()

        dc.DrawText(
            label,
            ((size[0] - text_size[0]) // 2) * int(self.x_center),
            ((size[1] - text_size[1]) // 2) * int(self.y_center),
        )
