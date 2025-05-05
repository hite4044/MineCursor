import wx
from PIL import Image
from PIL.Image import Resampling

from lib.data import CursorProject, CursorElement, Position, Scale2D
from lib.image_pil2wx import PilImg2WxImg
from ui.widget.font import ft
from ui_ctl.cursor_editor import CursorEditor


class MineCursorUI(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Mine Cursor", size=(1130, 660))
        self.load_icon()
        self.SetFont(ft(11))
        sizer = wx.BoxSizer(wx.VERTICAL)
        project = CursorProject("Test", (32, 32))
        project.scale = 2.0
        project.frame_count = 64
        project.ani_rate = 50
        project.add_element(
            CursorElement("Diamond Sword", [Image.open("diamond_sword.png").convert("RGBA")], scale=Scale2D(2.0, 2.0),
                          reverse_x=True))

        element = CursorElement("Clock", [])
        element.position = Position(17, 0)
        for f_index in range(64):
            fp = rf"assets_test\clock_{str(f_index).zfill(2)}.png"
            element.frames.append(Image.open(fp).convert("RGBA"))
        element.animation_length = 64
        project.add_element(element)

        editor = CursorEditor(self, project)
        sizer.Add(editor, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def load_icon(self):
        image = Image.open(r"assets\icon.png")
        size_list = [16, 24, 32, 64, 128, 256, 512]
        bundle = wx.IconBundle()
        for size in size_list:
            sized_image = image.resize((size, size), Resampling.HAMMING)
            bitmap = PilImg2WxImg(sized_image).ConvertToBitmap()
            icon = wx.Icon()
            icon.CopyFromBitmap(bitmap)
            bundle.AddIcon(icon)
        self.SetIcons(bundle)


if __name__ == "__main__":
    app = wx.App()
    frame = MineCursorUI()
    frame.Show()
    app.MainLoop()
