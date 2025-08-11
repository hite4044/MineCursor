from enum import Enum

import wx

from lib.data import CursorElement

mcEVT_ANIMATION_MODE_CHANGE = wx.NewEventType()
EVT_ANIMATION_MODE_CHANGE = wx.PyEventBinder(mcEVT_ANIMATION_MODE_CHANGE)
mcEVT_FRAME_COUNTER_CHANGE = wx.NewEventType()
EVT_FRAME_COUNTER_CHANGE = wx.PyEventBinder(mcEVT_FRAME_COUNTER_CHANGE, 1)
mcEVT_ELEMENT_SELECTED = wx.NewEventType()
EVT_ELEMENT_SELECTED = wx.PyEventBinder(mcEVT_ELEMENT_SELECTED, 1)
mcEVT_PROJECT_UPDATED = wx.NewEventType()
EVT_PROJECT_UPDATED = wx.PyEventBinder(mcEVT_PROJECT_UPDATED, 1)
mcEVT_SCALE_UPDATED = wx.NewEventType()
EVT_SCALE_UPDATED = wx.PyEventBinder(mcEVT_SCALE_UPDATED, 1)


class AnimationMode(Enum):
    NORMAL = 0
    MANUAL = 1


class AnimationModeChangeEvent(wx.PyCommandEvent):
    def __init__(self, mode: AnimationMode, frame_count: int = 0):
        super().__init__(mcEVT_ANIMATION_MODE_CHANGE)
        self.mode = mode
        self.frame_index = frame_count


class FrameCounterChangeEvent(wx.PyCommandEvent):
    def __init__(self, frame_count: int):
        super().__init__(mcEVT_FRAME_COUNTER_CHANGE)
        self.frame_counter = frame_count


class ElementSelectedEvent(wx.PyCommandEvent):
    def __init__(self, element: CursorElement | None):
        super().__init__(mcEVT_ELEMENT_SELECTED)
        self.element = element


class ProjectUpdatedEvent(wx.PyCommandEvent):
    def __init__(self):
        super().__init__(mcEVT_PROJECT_UPDATED)


class ScaleUpdatedEvent(wx.PyCommandEvent):
    def __init__(self, scale: float):
        super().__init__(mcEVT_SCALE_UPDATED)
        self.scale = scale
