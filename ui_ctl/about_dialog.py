import webbrowser

import wx
from PIL import Image

from lib.image_pil2wx import PilImg2WxImg
from widget.center_text import CenteredText
from widget.font import ft
from widget.win_icon import set_multi_size_icon

VERSION = "v1.1.1"
INFO = """\
项目贡献者: hite4044
我为这个项目投入了数百小时的时间, 有条件的话请Star吧！

项目开源协议: MPL-2.0

项目引用或使用内容条款:
- Mojang Minecraft
https://www.minecraft.net/
- 部分游戏贴图、粒子等内容
https://www.minecraft.net/usage-guidelines

更新日志
v1.0
程序基本完成！
v1.1
更新了主题文件格式, 不兼容以前的压缩格式
"""

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

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.icon, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        sizer.Add(self.title, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(self.open_project_github, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(self.info, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 10)
        self.SetSizer(sizer)

        self.open_project_github.Bind(wx.EVT_BUTTON, open_github)
        set_multi_size_icon(self, "assets/icons/action/about.png")


if __name__ == "__main__":
    app = wx.App()
    AboutDialog(None).ShowModal()
    app.MainLoop()