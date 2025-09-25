import os
import sys
import winreg
from os.path import abspath

import wx

from lib.config import config
from lib.info import IS_PACKAGE_ENV
from widget.data_entry import DataEntry
from widget.win_icon import set_multi_size_icon

LABEL_MAP = {
    "show_hidden_themes": "显示隐藏主题",
    "live_save_time": "保存延时时间",
    "default_author": "默认作者名称",
    "data_dir": "数据保存目录 (高级)"
}


class SettingsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, title="设置", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetFont(parent.GetFont())
        set_multi_size_icon(self, "assets/icons/action/settings.png")

        self.entries: dict[str, DataEntry] = {}
        for config_name in LABEL_MAP.keys():
            config_value = getattr(config, config_name)
            if type(config_value) not in [str, int, float, bool]:
                continue
            entry = DataEntry(self, LABEL_MAP.get(config_name, config_name), type(config_value))
            entry.set_value(config_value)
            self.entries[config_name] = entry
        self.ok = wx.Button(self, label="确定")
        self.cancel = wx.Button(self, label="取消")
        self.set_filetype_btn = wx.Button(self, label="设置文件类型信息")
        self.delete_filetype_btn = wx.Button(self, label="删除文件类型信息")

        sizer = wx.BoxSizer(wx.VERTICAL)
        entries_sizer = wx.FlexGridSizer(len(self.entries) + 2, 2, 5, 5)
        entries_sizer.AddGrowableCol(1, 1)
        for entry in list(self.entries.values()) + [
            self.set_filetype_btn,
            self.delete_filetype_btn
        ]:
            if isinstance(entry, DataEntry):
                entries_sizer.Add(entry.label, 0, wx.EXPAND)
                entries_sizer.Add(entry.entry, 1, wx.EXPAND)
            else:
                entries_sizer.Add(wx.Window(self), 0, wx.EXPAND)
                entries_sizer.Add(entry, 1, wx.EXPAND)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.ok)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.cancel)
        sizer.Add(entries_sizer, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.SetSizer(sizer)
        self.Fit()

        self.ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.set_filetype_btn.Bind(wx.EVT_BUTTON, self.on_set_filetype_info)
        self.delete_filetype_btn.Bind(wx.EVT_BUTTON, self.on_delete_filetype_info)

    def on_ok(self, _):
        for config_name, entry in self.entries.items():
            setattr(config, config_name, entry.data)
        config.save_config()
        self.EndModal(wx.ID_OK)
        self.Destroy()

    def on_cancel(self, _):
        self.EndModal(wx.ID_CANCEL)
        self.Destroy()

    def on_set_filetype_info(self, _):
        self.set_filetype_info(winreg.OpenKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\Classes"))

    def on_delete_filetype_info(self, _):
        self.delete_filetype_info(winreg.OpenKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\Classes"))

    @staticmethod
    def delete_filetype_info(parent_key: int | winreg.HKEYType):
        names = [".mctheme", ".rmctheme"]
        for name in names:
            winreg.DeleteKey(parent_key, name)
        winreg.DeleteKey(parent_key, "MineCursor.ThemeFile")

    def set_filetype_info(self, parent_key: int | winreg.HKEYType, write_cls: bool = True):
        names = [".mctheme", ".rmctheme"]
        for name in names:
            cls_root = winreg.CreateKeyEx(parent_key, name, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(cls_root, None, 0, winreg.REG_SZ, "MineCursor.ThemeFile")

        if not write_cls:
            return
        cls_root = winreg.CreateKeyEx(parent_key, f"MineCursor.ThemeFile", access=winreg.KEY_WRITE)
        winreg.SetValueEx(cls_root, None, 0, winreg.REG_SZ, "MineCursor 主题文件")
        default_icon = winreg.CreateKeyEx(cls_root, "DefaultIcon", access=winreg.KEY_WRITE)
        winreg.SetValueEx(default_icon, None, 0, winreg.REG_SZ, abspath("assets/icons/file_icons/ThemeFile.ico"))
        shell = winreg.CreateKeyEx(cls_root, "shell", access=winreg.KEY_WRITE)
        open_key = winreg.CreateKeyEx(shell, "open", access=winreg.KEY_WRITE)
        winreg.SetValueEx(open_key, "FriendlyAppName", 0, winreg.REG_SZ, "MineCursor")
        command_key = winreg.CreateKeyEx(open_key, "command", access=winreg.KEY_WRITE)
        winreg.SetValueEx(command_key, None, 0, winreg.REG_SZ, self.get_shell_cmd())

    @staticmethod
    def get_shell_cmd():
        if IS_PACKAGE_ENV:
            parent_dir = os.path.split(os.getcwd())[0]
            args = [os.path.join(parent_dir, "MineCursor.exe")]
        else:
            args = [abspath(sys.executable).replace("python.exe", "pythonw.exe"), abspath(sys.argv[0])]
        for i in range(len(args)):
            part = args[i].strip('"')
            args[i] = f'"{part}"'
        args.append('"%1"')
        return " ".join(args)
