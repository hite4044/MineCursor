import os
import sys
import winreg
from os.path import abspath, isdir, join, exists

import pylnk3
import wx

from lib.config import config
from lib.datas.data_dir import path_theme_data
from lib.datas.source import SourceNotFoundError
from lib.info import IS_PACKAGE_ENV
from lib.log import logger
from lib.resources import theme_manager
from ui_ctl.sources_editor import SourcesEditor
from widget.data_entry import DataEntry
from widget.win_icon import set_multi_size_icon

LABEL_MAP = {
    "show_hidden_themes": "显示隐藏主题",
    "live_save_time": "保存延时时间",
    "default_author": "默认作者名称",
    "record_create_time": "记录主题创建时间",
    "theme_use_cute_name": "指针项目使用特别名称",
    "auto_change_to_frame": "选中单帧元素时自动切换帧",
    "data_dir": "数据保存目录 (高级)",
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
        self.open_sources_editor_btn = wx.Button(self, label="打开源编辑器")
        self.import_default_themes_btn = wx.Button(self, label="导入默认主题")
        self.create_desktop_shortcut_btn = wx.Button(self, label="创建桌面快捷方式")

        sizer = wx.BoxSizer(wx.VERTICAL)
        entries_sizer = wx.FlexGridSizer(len(self.entries) + 5, 2, 5, 5)
        entries_sizer.AddGrowableCol(1, 1)
        for entry in list(self.entries.values()) + [
            self.set_filetype_btn,
            self.delete_filetype_btn,
            self.open_sources_editor_btn,
            self.import_default_themes_btn,
            self.create_desktop_shortcut_btn
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
        self.open_sources_editor_btn.Bind(wx.EVT_BUTTON, self.on_open_sources_editor)
        self.import_default_themes_btn.Bind(wx.EVT_BUTTON, lambda _: self.import_default_themes())
        self.create_desktop_shortcut_btn.Bind(wx.EVT_BUTTON, self.create_desktop_shortcut)

    def on_ok(self, _):
        for config_name, entry in self.entries.items():
            setattr(config, config_name, entry.data)
        config.save_config()
        self.EndModal(wx.ID_OK)
        self.Destroy()

    def on_cancel(self, _):
        self.EndModal(wx.ID_CANCEL)
        self.Destroy()

    def on_open_sources_editor(self, _):
        editor = SourcesEditor(self)
        editor.ShowModal()

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

    @staticmethod
    def import_default_themes(first_import: bool = False):
        overwrite = first_import or wx.YES == \
                    wx.MessageBox("导入默认主题时, 覆盖(是)/跳过(否) 已存在的同ID主题?", "提示",
                                  wx.YES_NO | wx.ICON_QUESTION)

        default_themes_dir = abspath("assets/default_themes")
        if not isdir(default_themes_dir):
            wx.MessageBox("未找到默认主题目录\nassets/default_themes", "错误", wx.OK | wx.ICON_ERROR)
            return

        for theme_file in os.listdir(default_themes_dir):
            if not theme_file.endswith(".mctheme"):
                continue
            theme_path = join(default_themes_dir, theme_file)
            new_path = join(path_theme_data, theme_file)
            if exists(new_path):
                if not overwrite:
                    continue
                os.remove(new_path)
                if new_path in theme_manager.theme_file_mapping:
                    theme = theme_manager.theme_file_mapping.pop(new_path)
                    theme_manager.themes.remove(theme)

            try:
                theme, info = theme_manager.load_theme_file(theme_path)
            except SourceNotFoundError as e:
                logger.warning(f"主题 [{theme_file}] 中ID为 [{e.source_id}] 的源不存在")
                continue
            logger.info(f"已加载主题: {theme}")

            if orig_theme := theme_manager.find_theme(theme.id):
                if not overwrite:
                    continue
                theme_manager.themes.remove(orig_theme)
            theme_manager.add_theme(theme)

    @staticmethod
    def create_desktop_shortcut(*args):
        if IS_PACKAGE_ENV:
            lnk = pylnk3.for_file(abspath("..\MineCursor.exe"), work_dir=abspath("."))
        else:
            lnk = pylnk3.for_file(abspath(sys.executable.replace("python.exe", "pythonw.exe")),
                                  arguments=abspath("main.py"),
                                  icon_file=abspath("assets/icon.ico"), work_dir=abspath("."))

        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
        winreg.CloseKey(key)
        lnk.save(join(desktop_path, "Mine Cursor.lnk"))
