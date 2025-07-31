from enum import Enum
from typing import cast

import wx


class PadDir(Enum):
    LEFT_RIGHT = (1, 1)


def pad(window: wx.Window, direction: PadDir, padx: int = 10, pady: int = 10):
    parent = window.GetParent()
    def on_size(event: wx.SizeEvent | None):
        if event:
            event.Skip()
        w, h = cast(tuple[int, int], parent.GetClientSize())
        bw, bh = cast(tuple[int, int], window.GetSize())
        window.SetPosition((w - padx - bw, h - pady - bh))
        window.Refresh()

    parent.Bind(wx.EVT_SIZE, on_size)
    return on_size
