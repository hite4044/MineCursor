from enum import Enum
from typing import Type

import wx

from lib.log import logger
from widget.center_text import CenteredText

INT32_MAX = 2 ** 31 - 1
mcEVT_DATA_UPDATE = wx.NewEventType()
EVT_DATA_UPDATE = wx.PyEventBinder(mcEVT_DATA_UPDATE, 1)


class DataEntryEvent(wx.PyCommandEvent):
    def __init__(self, data: str | int | float | bool | Enum):
        super().__init__(mcEVT_DATA_UPDATE, -1)
        self.data = data

    def Skip(self, skip=True):
        super().Skip(skip)


class DataEntry(wx.Panel):
    entry: wx.TextCtrl | wx.CheckBox | wx.Choice

    def __init__(self, parent: wx.Window, label: str,
                 data_type: Type[str | int | float | bool | Enum],
                 limits: tuple[int | float, int | float] | None = None, enum_names: dict[Enum, str] | None = None,
                 disabled: bool = False, multilined: bool = False,
                 use_sizer=False):
        self.depend_entry = None
        if use_sizer:
            super().__init__(parent)
            parent = self
        self.limits = limits
        self.data_type = data_type
        self.data = None
        self.last_value = None
        self.enum_names = enum_names
        self.label = CenteredText(parent, label=label, x_center=False)
        self.after_call = wx.CallLater(100, self.after_task_func)
        self.after_tasks = []
        if data_type in [str, int, float]:
            style = (wx.TE_MULTILINE if multilined else 0) | (wx.TE_READONLY if disabled else 0)
            self.entry = wx.TextCtrl(parent, style=wx.TE_PROCESS_ENTER | style)
            if data_type == str:
                self.entry.Bind(wx.EVT_TEXT, self.on_text)
        elif data_type == bool:
            self.entry = wx.CheckBox(parent)
        elif issubclass(data_type, Enum):
            self.entry = wx.Choice(parent)  # 组件创建性能不佳
            self.entry.Bind(wx.EVT_CHOICE, self.finish_edit)

            def at():
                self.entry.AppendItems(list(enum_names.values()))
                for i, enum in enumerate(enum_names):
                    if enum_names[enum] == self.data:
                        self.entry.SetSelection(i)
                        break
                else:
                    self.entry.SetSelection(0)

            self.after_tasks.append(at)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

        if disabled:
            if not isinstance(self.entry, wx.TextCtrl):
                self.entry.Disable()
        else:
            if data_type == bool:
                self.entry.Bind(wx.EVT_CHECKBOX, self.finish_edit)
            else:
                self.entry.Bind(wx.EVT_SET_FOCUS, self.on_start_edit)
                self.entry.Bind(wx.EVT_KILL_FOCUS, self.on_focus_lost)
                self.entry.Bind(wx.EVT_TEXT_ENTER, self.on_enter_press)
            if data_type in [int, float]:
                self.entry.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

        if use_sizer:
            self.sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.sizer.Add(self.label, 0, wx.EXPAND)
            self.sizer.AddSpacer(8)
            self.sizer.Add(self.entry, 1, wx.EXPAND)
            self.SetSizer(self.sizer)

        # self.label.SetMinSize((-1, 28))
        self.entry.SetMinSize((-1, 28))

    def after_task_func(self):
        for task in self.after_tasks:
            task()
        self.after_tasks.clear()

    def Bind(self, event, handler, *args):
        if event is EVT_DATA_UPDATE:
            self.entry.Bind(event, handler)
            return
        super().Bind(event, handler, *args)

    def on_mouse_wheel(self, event: wx.MouseEvent):
        delta = event.GetWheelRotation() / event.GetWheelDelta()
        self.data += self.data_type(delta)
        self.set_value(self.data)
        event = DataEntryEvent(self.data)
        wx.PostEvent(self.entry, event)

    def on_start_edit(self, event: wx.Event):
        event.Skip()
        if issubclass(self.data_type, Enum):
            return
        self.last_value = self.entry.GetValue()

    def on_focus_lost(self, event: wx.FocusEvent):
        event.Skip()
        self.finish_edit()

    def on_enter_press(self, _):
        self.finish_edit()

    def on_text(self, event: wx.KeyEvent):
        event.Skip()
        assert isinstance(self.entry, wx.TextCtrl)
        value = self.entry.GetValue()
        if value != self.last_value:
            self.last_value = value
            wx.PostEvent(self.entry, DataEntryEvent(value))

    def finish_edit(self, _=None):
        if isinstance(self.entry, wx.Choice):
            if self.after_call.IsRunning():
                self.after_call.Stop()
                self.after_task_func()
            data = self.entry.GetSelection()
            assert data != -1
            enum_data = list(self.enum_names.keys())[data]
            self.data = enum_data
            wx.PostEvent(self.entry, DataEntryEvent(enum_data))
            return
        try:
            data = self.data_type(self.entry.GetValue())
        except ValueError:
            self.entry.SetValue(self.last_value)
            return
        if self.data_type in [int, float]:
            assert isinstance(self.entry, wx.TextCtrl)
            self.entry.SetValue(str(data))
        if self.data_type in [int, float] and self.limits is not None:
            limited_data = max(self.limits[0], min(self.limits[1], data))
            if data != limited_data:
                self.entry.SetValue(str(limited_data))
                data = limited_data
        self.data = data
        if str(data) == str(self.last_value):
            return
        logger.debug(f"Data Entry ({self.label.GetLabel()}) 数据改变 {self.last_value} -> {data}")
        self.last_value = data
        event = DataEntryEvent(data)
        wx.PostEvent(self.entry, event)

    def set_value(self, value: str | int | float | bool | Enum):
        self.data = value
        self.last_value = value
        if self.data_type in [int, float]:
            assert isinstance(self.entry, wx.TextCtrl)
            self.entry.SetValue(str(value))
            return
        if issubclass(self.data_type, Enum):
            def at():
                self.entry.SetSelection(list(self.enum_names.keys()).index(value))

            if self.after_call.IsRunning():
                self.after_tasks.append(at)
            else:
                at()
            return
        self.entry.SetValue(value)

    def enable(self):
        self.entry.Enable()

    def disable(self):
        self.entry.Disable()

    def set_depend(self, depend_entry: 'DataEntry'):
        self.depend_entry = depend_entry
        if depend_entry.data is not True:
            self.disable()
        self.depend_entry.entry.Bind(EVT_DATA_UPDATE, self.depend_callback)

    def depend_callback(self, event: DataEntryEvent):
        event.Skip()
        if event.data is True:
            self.enable()
        else:
            self.disable()


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


class EnumEntry(DataEntry):
    def __init__(self, parent: wx.Window, label: str, enum_names: dict[Enum, str], use_sizer=False):
        super().__init__(parent, label, Enum, enum_names=enum_names, use_sizer=use_sizer)
