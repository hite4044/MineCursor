import wx

from lib.data import CursorElement

mcEVT_ELEMENT_SELECTED = wx.NewEventType()
EVT_ELEMENT_SELECTED = wx.PyEventBinder(mcEVT_ELEMENT_SELECTED, 1)
mcEVT_PROJECT_UPDATED = wx.NewEventType()
EVT_PROJECT_UPDATED = wx.PyEventBinder(mcEVT_PROJECT_UPDATED, 1)
mcEVT_SCALE_UPDATED = wx.NewEventType()
EVT_SCALE_UPDATED = wx.PyEventBinder(mcEVT_SCALE_UPDATED, 1)


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
