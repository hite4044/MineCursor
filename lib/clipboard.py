import wx


class ClipBoard:
    def __init__(self, window: wx.Window, get_data_func, set_data_func):
        self.window = window
        self.content = None
        self.get_data_func = get_data_func
        self.set_data_func = set_data_func

        self.window.Bind(wx.EVT_KEY_DOWN, self.on_key)

    def on_key(self, event: wx.KeyEvent):
        if event.GetKeyCode() == ord("C") and event.GetModifiers() == wx.MOD_CONTROL:
            self.set(self.get_data_func())
        elif event.GetKeyCode() == ord("V") and event.GetModifiers() == wx.MOD_CONTROL:
            if self.content is not None:
                self.set_data_func(self.get())
        event.Skip()

    def get(self):
        return self.content

    def set(self, content):
        self.content = content
