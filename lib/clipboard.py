import wx


class ClipBoard:
    def __init__(self, window: wx.Window | None, get_data_func, set_data_func):
        self.window = window
        self.content = None
        self.get_data_func = get_data_func
        self.set_data_func = set_data_func

        if window:
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


class PublicClipBoard(ClipBoard):
    def __init__(self, ):
        super().__init__(None, self.on_get_data_hook, self.on_set_data_hook)
        self.callbacks: dict[int, tuple] = {}

    def __call__(self, window: wx.Window, get_data_func, set_data_func):
        self.callbacks[window.GetHandle()] = get_data_func, set_data_func
        window.Bind(wx.EVT_KEY_DOWN, self.on_key)
        window.Bind(getattr(wx, "EVT_WINDOW_DESTROY"), self.on_window_destroyed)

    def on_key(self, event: wx.KeyEvent):
        self.window = event.GetEventObject()
        return super().on_key(event)

    def on_get_data_hook(self):
        return self.callbacks[self.window.GetHandle()][0]()

    def on_set_data_hook(self, data):
        self.callbacks[self.window.GetHandle()][1](data)

    def on_window_destroyed(self, event: wx.WindowDestroyEvent):
        self.callbacks.pop(event.GetWindow().GetHandle())

PUBLIC_ELEMENT_CLIPBOARD = PublicClipBoard()