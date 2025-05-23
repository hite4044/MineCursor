import wx


class ProgressPanel(wx.Panel):
    def __init__(self, parent: wx.Window, msg: str):
        super().__init__(parent)

        self.text = wx.StaticText(self, label=msg)
        self.gauge = wx.Gauge(self, range=100)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.text, 0, wx.EXPAND)
        sizer.Add(self.gauge, 0, wx.EXPAND)
        self.SetSizer(sizer)

    def update(self, value: int, new_text: str = "", range_: int = 100):
        if range_ is not None and range_ != self.gauge.GetRange():
            self.gauge.SetRange(range_)
        self.gauge.SetValue(value)
        if new_text:
            self.text.SetLabel(new_text)


class AdvancedProgressDialog(wx.Dialog):
    def __init__(self, parent: wx.Window | None, title: str, max_panels: int):
        super().__init__(parent, title=title)
        if parent:
            self.SetFont(parent.GetFont())

        self.panels = [ProgressPanel(self, f"进度 {i + 1}") for i in range(max_panels)]
        self.sizer = wx.FlexGridSizer(max_panels, 1, 5, 5)
        self.sizer.AddGrowableRow(0)
        for panel in self.panels:
            self.sizer.Add(panel, 1, wx.EXPAND)
        self.out_box = wx.BoxSizer(wx.VERTICAL)
        self.out_box.Add(self.sizer, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(self.out_box)
        self.Fit()

    def set_panels_num(self, num: int):
        for i, panels in enumerate(self.panels):
            panel = self.panels[i]
            if i >= num:
                panel.Hide()
            else:
                panel.Show()
        self.Fit()

    def update(self, index: int, value: int, new_text: str = "", range_: int | None = None):
        wx.CallAfter(self.update_safe, index, value, new_text, range_)
        self.GetId() # 测试控件是否已经销毁

    def update_safe(self, index: int, value: int, new_text: str = "", range_: int | None = None):
        try:
            self.panels[index].update(value, new_text, range_)
            self.Fit()
        except RuntimeError:
            pass

def test_main():
    app = wx.App()
    dlg = AdvancedProgressDialog(None, "测试进度条", 2)
    dlg.Show()
    wx.CallLater(1000, dlg.update, 0, 50, "进度 1")
    wx.CallLater(2000, dlg.update, 1, 100, "进度 2")
    wx.CallLater(3000, dlg.set_panels_num, 1)
    app.MainLoop()

if __name__ == "__main__":
    test_main()
