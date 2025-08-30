import faulthandler

faulthandler.enable()

import ctypes
import sys
import os

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MineCursor")

os.chdir(os.path.dirname(__file__))  # 进入当前目录
sys.path.append(os.path.dirname(__file__))  # 添加模块导入路径

import wx
from ui_ctl.theme_editor import ThemeEditor

if __name__ == "__main__":
    app = wx.App()
    frame = ThemeEditor(None)
    frame.Show()
    app.MainLoop()
