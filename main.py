import wx
import faulthandler

from ui_ctl.theme_editor import ThemeEditor

if __name__ == "__main__":
    app = wx.App()
    frame = ThemeEditor(None)
    frame.Show()
    app.MainLoop()
