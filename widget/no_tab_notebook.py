import wx


class NoTabNotebook(wx.Panel):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.panels: list[wx.Window] = []
        self.now_window: wx.Window | None = None
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

    def add_page(self, window: wx.Window):
        self.panels.append(window)
        window.Hide()
        if not self.now_window:
            self.now_window = window
            self.sizer.Add(window, 1, wx.EXPAND)
            self.Layout()

    def switch_page(self, index: int):
        if self.now_window:
            self.now_window.Hide()
        self.now_window = self.panels[index]
        self.panels[index].Show()
        self.sizer.Clear()
        self.sizer.Add(self.panels[index], 1, wx.EXPAND)
        self.Layout()
        self.Refresh()
        self.now_window.Refresh()

    def remove_page(self, index: int):
        self.panels[index].Destroy()
        self.panels.pop(index)
        if len(self.panels):
            self.switch_page(0)
