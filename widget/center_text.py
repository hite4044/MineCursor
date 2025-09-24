import wx


class CenteredText(wx.Window):
    """使得绘制的文字始终保持在控件中央"""

    def __init__(
            self,
            parent: wx.Window,
            id_=wx.ID_ANY,
            label="",
            pos=wx.DefaultPosition,
            size=wx.DefaultSize,
            style=0,
            name="MineCursor.CenteredText",
            x_center=True,
            y_center=True,
    ):
        super().__init__(parent, id_, pos, size, style, name)
        print(parent.GetBackgroundColour(), parent)
        size = self.SetLabel(label)
        self.SetSize(size)
        self.SetInitialSize(size)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.x_center = x_center
        self.y_center = y_center
        self.SetDoubleBuffered(True)

    def on_size(self, event: wx.SizeEvent):
        event.Skip()
        self.Refresh()

    def SetFont(self, font):
        super().SetFont(font)
        self.SetLabel(self.GetLabel())

    def SetLabel(self, label) -> wx.Size:
        super().SetLabel(label)
        dc = wx.ClientDC(self)
        size = wx.Size(*(dc.GetFullMultiLineTextExtent(label, self.GetFont())[:2]))
        self.SetMinSize(size)
        self.CacheBestSize(size)
        self.SetVirtualSize(size)
        self.Refresh()
        if self.GetSizer():
            self.GetSizer().Layout()
        return size

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
