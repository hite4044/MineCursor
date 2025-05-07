from typing import Type

import wx

from ui.widget.center_text import CenteredText

INT32_MAX = 2 ** 31 - 1
mcEVT_DATA_UPDATE = wx.NewEventType()
EVT_DATA_UPDATE = wx.PyEventBinder(mcEVT_DATA_UPDATE, 1)


class DataEntryEvent(wx.PyCommandEvent):
    def __init__(self, data: str | int | float | bool):
        super().__init__(mcEVT_DATA_UPDATE)
        self.data = data


class DataEntry(wx.Panel):
    def __init__(self, parent: wx.Window, label: str,
                 data_type: Type[str | int | float | bool],
                 limits: tuple[int | float, int | float] | None = None, use_sizer=False):
        if use_sizer:
            super().__init__(parent)
            parent = self
        self.limits = limits
        self.data_type = data_type
        self.last_value = None
        self.label = CenteredText(parent, label=label, x_center=False)
        if data_type in [str, int, float]:
            self.entry = wx.TextCtrl(parent, style=wx.TE_PROCESS_ENTER)
            if data_type == str:
                self.entry.Bind(wx.EVT_TEXT, lambda e: wx.PostEvent(self.entry, DataEntryEvent(self.entry.GetValue())))
        elif data_type == bool:
            self.entry = wx.CheckBox(parent)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

        if data_type == bool:
            self.entry.Bind(wx.EVT_CHECKBOX, self.on_finish_edit)
        else:
            self.entry.Bind(wx.EVT_SET_FOCUS, self.on_start_edit)
            self.entry.Bind(wx.EVT_KILL_FOCUS, self.on_finish_edit)
            self.entry.Bind(wx.EVT_TEXT_ENTER, self.on_finish_edit)

        if use_sizer:
            self.sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.sizer.Add(self.label, 0, wx.ALIGN_CENTER_VERTICAL)
            self.sizer.AddSpacer(8)
            self.sizer.Add(self.entry, 1, wx.EXPAND)
            self.SetSizer(self.sizer)
        self.entry.SetMaxSize((-1, 28))

    def on_start_edit(self, event: wx.Event):
        event.Skip()
        self.last_value = self.entry.GetValue()

    def on_finish_edit(self, event: wx.Event):
        if not isinstance(event, wx.CommandEvent) or not event.GetString() == self.entry.GetValue():
            event.Skip()
        try:
            data = self.data_type(self.entry.GetValue())
        except ValueError:
            self.entry.SetValue(self.last_value)
            return
        if self.data_type in [int, float]:
            assert isinstance(self.entry, wx.TextCtrl)
            self.entry.SetValue(str(data))
        if self.data_type in [int, float] and self.limits is not None:
            assert isinstance(self.entry, wx.SpinCtrl) or isinstance(self.entry, wx.SpinCtrlDouble)
            limited_data = max(self.limits[0], min(self.limits[1], data))
            if data != limited_data:
                self.entry.SetValue(str(limited_data))
                data = limited_data

        event = DataEntryEvent(data)
        wx.PostEvent(self.entry, event)

    def set_value(self, value: str | int | float | bool):
        if self.data_type in [int, float]:
            assert isinstance(self.entry, wx.TextCtrl)
            self.entry.SetValue(str(value))
            return
        self.entry.SetValue(value)


class StringEntry(DataEntry):
    def __init__(self, parent: wx.Window, label: str, use_sizer=False):
        super().__init__(parent, label, str, use_sizer=use_sizer)


class IntEntry(DataEntry):
    def __init__(self, parent: wx.Window, label: str, limits: tuple[int, int] = None, use_sizer=False):
        super().__init__(parent, label, int, limits, use_sizer=use_sizer)


class FloatEntry(DataEntry):
    def __init__(self, parent: wx.Window, label: str, limits: tuple[int, int] = None, use_sizer=False):
        super().__init__(parent, label, float, limits, use_sizer=use_sizer)


class BoolEntry(DataEntry):
    def __init__(self, parent: wx.Window, label: str, use_sizer=False):
        super().__init__(parent, label, bool, use_sizer=use_sizer)
