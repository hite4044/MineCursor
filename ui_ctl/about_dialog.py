import webbrowser

import wx
from PIL import Image

from lib.image_pil2wx import PilImg2WxImg
from lib.info import *
from widget.center_text import CenteredText
from widget.font import ft
from widget.win_icon import set_multi_size_icon


def open_github(_):
    webbrowser.open("https://github.com/hite4044/MineCursor")


class AboutDialog(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, title=f"MineCursor {VERSION} - 关于", size=(420, 520),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        if parent:
            self.SetFont(parent.GetFont())

        self.icon = wx.StaticBitmap(self, bitmap=PilImg2WxImg(Image.open(r"assets\icon.png").resize((128, 128))))
        self.title = CenteredText(self, label=f"MineCursor {VERSION}", x_center=True, y_center=False)
        self.open_project_github = wx.Button(self, label="项目Github主页")
        self.info = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.title.SetFont(ft(36))
        self.open_project_github.SetFont(ft(18))
        self.info.SetValue(INFO)
        self.info.SetMinSize((-1, 400))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.icon, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        sizer.Add(self.title, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(self.open_project_github, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(self.info, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 10)
        self.SetSizer(sizer)
        self.Fit()

        self.open_project_github.Bind(wx.EVT_BUTTON, open_github)
        set_multi_size_icon(self, "assets/icons/action/about.png")


if __name__ == "__main__":
    app = wx.App()
    AboutDialog(None).ShowModal()
    app.MainLoop()
