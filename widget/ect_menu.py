from typing import Callable

import wx

from lib.dpi import SCALE
from lib.image_pil2wx import PilImg2WxImg


class EtcMenu(wx.Menu):
    """绑定事件如同过ETC一样快！"""
    def __init__(self):
        super().__init__()

    def Append(self, label: str, handler: Callable = lambda : None, *args, icon: str = None) -> wx.MenuItem:
        menu_item = super().Append(wx.ID_ANY, label)
        if icon:
            icon = "assets/icons/" + icon
            image = wx.Image(icon)
            image.Rescale(int(SCALE) * 16, int(SCALE) * 16, wx.IMAGE_QUALITY_NEAREST)
            menu_item.SetBitmap(image.ConvertToBitmap())
        self.Bind(wx.EVT_MENU, lambda _: handler(*args), id=menu_item.GetId())
        return menu_item
