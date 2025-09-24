import wx

from lib.config import config
from widget.data_entry import DataEntry
from widget.win_icon import set_multi_size_icon

LABEL_MAP = {
    "show_hidden_themes": "显示隐藏主题",
    "live_save_time": "保存延时时间",
    "default_author": "默认作者名称"
}


class SettingsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, title="设置", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetFont(parent.GetFont())
        set_multi_size_icon(self, "assets/icons/action/settings.png")

        self.entries: dict[str, DataEntry] = {}
        for config_name in config.find_config_names():
            config_value = getattr(config, config_name)
            if type(config_value) not in [str, int, float, bool]:
                continue
            entry = DataEntry(self, LABEL_MAP.get(config_name, config_name), type(config_value))
            entry.set_value(config_value)
            self.entries[config_name] = entry
        self.ok = wx.Button(self, label="确定")
        self.cancel = wx.Button(self, label="取消")

        sizer = wx.BoxSizer(wx.VERTICAL)
        entries_sizer = wx.FlexGridSizer(len(self.entries), 2, 5, 5)
        entries_sizer.AddGrowableCol(1, 1)
        for entry in self.entries.values():
            entries_sizer.Add(entry.label, 0, wx.EXPAND)
            entries_sizer.Add(entry.entry, 1, wx.EXPAND)
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


    def on_ok(self, _):
        for config_name, entry in self.entries.items():
            setattr(config, config_name, entry.data)
        config.save_config()
        self.EndModal(wx.ID_OK)
        self.Destroy()

    def on_cancel(self, _):
        self.EndModal(wx.ID_CANCEL)
        self.Destroy()
