import ctypes
import faulthandler
import os
import sys
from datetime import datetime
from os.path import expandvars, join, split

# 在无输出句柄的情况下替换标准输出为文件

log_dir = join(split(expandvars("%APPDATA%"))[0], "Mine Cursor/Logs")
os.makedirs(log_dir, exist_ok=True)
output_file = open(join(log_dir, f"log_{datetime.now().strftime('%Y-%m-%d')}.log"), "a+", encoding="utf-8")
output_file.write(f"\n\nMineCursor Starting... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")


class StreamMix:
    def __init__(self, std_file, added_stream):
        self.std_file = std_file
        self.added_stream = added_stream

    def write(self, data: str):
        self.std_file.write(data)
        # 去除颜色转义符
        self.added_stream.write(data.rstrip("\n")[5:-4] + ("\n" if data[-1] == "\n" else ""))

    def flush(self):
        self.std_file.flush()
        self.added_stream.flush()

    def fileno(self):
        return self.std_file.fileno()


if sys.stdout is None or sys.stderr is None:
    sys.stdout = output_file
    sys.stderr = output_file
else:
    sys.stdout = StreamMix(sys.stdout, output_file)
    sys.stderr = StreamMix(sys.stderr, output_file)

faulthandler.enable()

os.chdir(os.path.dirname(__file__))  # 进入当前目录
sys.path.append(os.path.dirname(__file__))  # 添加模块导入路径

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MineCursor")

###################################################################################

# 启动程序
from lib.log import logger

logger.info("导入库中...")

import wx
from ui_ctl.theme_editor import ThemeEditor

if __name__ == "__main__":
    app = wx.App()
    frame = ThemeEditor(None)
    frame.Show()
    app.MainLoop()
