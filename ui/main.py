import wx

from lib.data import CursorProject
from ui.widget.font import ft
from ui_ctl.cursor_editor import CursorEditor


class Panel(wx.Panel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(self.__class__.__name__)
wx.Panel = Panel
from ui.cursor_editor import CursorEditorUI


class MineCursorUI(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Mine Cursor", size=(900, 600))
        self.SetFont(ft(11))
        sizer = wx.BoxSizer(wx.VERTICAL)
        project = CursorProject("Test", (16, 16))
        editor = CursorEditor(self, project)
        sizer.Add(editor, 1, wx.EXPAND)
        self.SetSizer(sizer)


if __name__ == "__main__":
    app = wx.App()
    frame = MineCursorUI()
    frame.Show()
    app.MainLoop()