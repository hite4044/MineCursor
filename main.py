import faulthandler

faulthandler.enable()

import ctypes

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MineCursor")

import wx
from ui_ctl.theme_editor import ThemeEditor

if __name__ == "__main__":
    app = wx.App()
    frame = ThemeEditor(None)
    frame.Show()
    app.MainLoop()
