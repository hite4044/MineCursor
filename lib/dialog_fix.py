import wx


def register_close(frame: wx.Dialog):
    def on_close(event: wx.CloseEvent):
        if event.CanVeto():
            frame.EndModal(wx.ID_CANCEL)
            frame.Destroy()
        else:
            event.Skip()

    frame.Bind(wx.EVT_CLOSE, on_close)
