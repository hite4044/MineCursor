import ctypes
import faulthandler
import os
import sys
from datetime import datetime
from os.path import expandvars, join, split


class StreamMixer:
    def __init__(self, std_file, added_stream):
        self.std_file = std_file
        self.added_stream = added_stream

    def write(self, data: str):
        self.std_file.write(data)
        # 去除颜色转义符
        if data.startswith("\033"):  # 去除颜色符号
            data = data.rstrip("\n")[5:-4] + "\n"
        self.added_stream.write(data)

    def flush(self):
        self.std_file.flush()
        self.added_stream.flush()

    def fileno(self):
        return self.std_file.fileno()


class MineCursorLauncher:
    def __init__(self):
        self.switch_work_dir()
        self.handle_output()
        self.program_prepare()
        self.run_app()

    @staticmethod
    def switch_work_dir():
        t = os.path.dirname(os.path.abspath(__file__))
        os.chdir(t)  # 进入当前目录
        sys.path.append(t)  # 添加模块导入路径

    @staticmethod
    def handle_output():  # 在无输出句柄的情况下替换标准输出为文件
        data_dir = MineCursorLauncher.get_data_dir()
        log_dir = join(data_dir, "Logs")
        os.makedirs(log_dir, exist_ok=True)

        output_file = open(join(log_dir, f"log_{datetime.now().strftime('%Y-%m-%d')}.log"), "a+", encoding="utf-8")
        output_file.write(f"\n\nMineCursor Starting... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")

        if sys.stdout is None or sys.stderr is None:
            sys.stdout = output_file
            sys.stderr = output_file
        else:
            sys.stdout = StreamMixer(sys.stdout, output_file)
            sys.stderr = StreamMixer(sys.stderr, output_file)

    @staticmethod
    def get_data_dir():
        data_dir = join(split(expandvars("%APPDATA%"))[0], "Mine Cursor")
        if os.path.isfile("config.json"):
            import json
            config = json.load(open("config.json", encoding="utf-8"))
            if isinstance(config, dict) and config.get("data_dir"):
                data_dir = os.path.abspath(expandvars(config.get("data_dir")))
        return data_dir

    @staticmethod
    def program_prepare():
        faulthandler.enable()
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MineCursor")

    @staticmethod
    def run_app():
        from lib.log import logger
        logger.info("导入库中...")

        import wx
        from ui_ctl.theme_editor import ThemeEditor

        app = wx.App()
        frame = ThemeEditor(None)
        frame.Show()
        app.MainLoop()


if __name__ == '__main__':
    MineCursorLauncher()
