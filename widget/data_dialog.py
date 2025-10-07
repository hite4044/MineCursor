from dataclasses import dataclass
from enum import Enum
from typing import Union, Type

import wx

from widget.data_entry import DataEntry
from widget.win_icon import set_multi_size_icon


class DataLineType(Enum):
    STRING = 0
    INT = 1
    FLOAT = 2
    BOOL = 3
    CHOICE = 4


DataType = Union[str, int, float, bool, str, Enum]
DATA_TYPE_MAP: dict[DataLineType, Type[DataType]] = {
    DataLineType.STRING: str,
    DataLineType.INT: int,
    DataLineType.FLOAT: float,
    DataLineType.BOOL: bool,
}


@dataclass
class DataLineParam:
    id: str
    label: str
    type: DataLineType
    default: DataType = None
    tip: str = None

    enum_names: dict[Enum, str] | None = None

    disabled: bool = False
    multilined: bool = False


class DataDialog(wx.Dialog):
    def __init__(self, parent: wx.Window | None, title: str, *params: DataLineParam):
        super().__init__(parent, title=title, style=wx.DEFAULT_FRAME_STYLE)
        if parent:
            self.SetFont(parent.GetFont())
        self.datas: dict[str, DataType] = {}
        self.params: list[DataLineParam] = list(params)
        for param in params:
            if param.default:
                self.datas[param.id] = param.default
                continue

            if param.type == DataLineType.STRING:
                self.datas[param.id] = ""
            elif param.type == DataLineType.INT:
                self.datas[param.id] = 0
            elif param.type == DataLineType.FLOAT:
                self.datas[param.id] = 0.0
            elif param.type == DataLineType.BOOL:
                self.datas[param.id] = False

        entries_sizer = wx.FlexGridSizer(len(params) + 1, 2, 5, 5)
        entries_sizer.AddGrowableCol(1, 1)
        self.entries: list[DataEntry] = []
        for index in range(len(params)):
            param: DataLineParam = params[index]
            data_type = DATA_TYPE_MAP[param.type] if param.type != DataLineType.CHOICE else next(
                iter(param.enum_names.keys())).__class__
            entry: DataEntry = DataEntry(self, param.label, data_type, enum_names=param.enum_names,
                                         disabled=param.disabled, multilined=param.multilined)
            entry.set_value(param.default)
            entry.label.SetToolTip(param.tip)
            entry.entry.SetMinSize((350, -1))

            entries_sizer.Add(entry.label, 0, wx.EXPAND)
            entries_sizer.Add(entry.entry, 1, wx.EXPAND)
            if param.multilined:
                entries_sizer.AddGrowableRow(index, 1)
            self.entries.append(entry)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ok_btn = wx.Button(self, label="确定")
        self.cancel_btn = wx.Button(self, label="取消")
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.ok_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.cancel_btn, 0, wx.EXPAND)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(3)
        sizer.Add(entries_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 7)
        sizer.AddSpacer(10)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 7)
        sizer.AddSpacer(10)
        self.SetSizer(sizer)
        self.Fit()

        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)

    def set_icon(self, path: str):
        path = "assets/icons/" + path
        set_multi_size_icon(self, path)

    def on_cancel(self, _):
        self.EndModal(wx.ID_CANCEL)
        self.Destroy()

    def on_ok(self, _):
        for i, entry in enumerate(self.entries):
            param = self.params[i]
            self.datas[param.id] = entry.data
        self.EndModal(wx.ID_OK)
        self.Destroy()


if __name__ == "__main__":
    app = wx.App()
    frame = DataDialog(None, "测试",
                       DataLineParam("name", "名字", DataLineType.STRING, "测试名字"),
                       DataLineParam("age", "年龄", DataLineType.INT, 18, "测试年龄"),
                       DataLineParam("sex", "性别", DataLineType.BOOL, False, "测试性别"),
                       DataLineParam("height", "身高", DataLineType.FLOAT, 1.8, "测试身高"),
                       DataLineParam("color", "颜色", DataLineType.CHOICE, DataLineType.INT, "测试颜色",
                                     {DataLineType.STRING: "字符串", DataLineType.INT: "整数"}))
    frame.ShowModal()
    print(frame.datas)
