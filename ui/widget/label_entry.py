import wx


class LabelEntry(wx.Panel):
    def __init__(self, parent: wx.Window, label: str):
        super().__init__(parent)
        self.label = wx.StaticText(self, label=label)
        self.entry = wx.TextCtrl(self)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.label, 0, wx.EXPAND)
        self.sizer.Add(self.entry, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

    def GetLabel(self):
        return self.label.GetLabel()

    def SetLabel(self, label):
        self.label.SetLabel(label)

    def GetValue(self):
        return self.entry.GetValue()

    def SetValue(self, value):
        self.entry.SetValue(value)
