import wx
from PIL import Image, ImageOps

from lib.image_pil2wx import PilImg2WxImg


def set_multi_size_icon(frame: wx.TopLevelWindow, icon_path: str,
                        resampling: Image.Resampling = Image.Resampling.NEAREST):
    image = Image.open(icon_path)
    scale_list = [1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3, 4, 8]
    bundle = wx.IconBundle()
    for i, data in enumerate(scale_list):
        if isinstance(data, float):
            sized_image = image.resize((int(data) * 16, int(data) * 16), resampling)
        else:
            sized_image = image.resize((int(data * 16), int(data * 16)), resampling)

        if isinstance(data, float):
            exp_width = int((data - int(data)) * image.width // 2)
            sized_image = ImageOps.expand(image, exp_width, (255, 255, 255, 0))

        bitmap = PilImg2WxImg(sized_image).ConvertToBitmap()
        icon = wx.Icon(bitmap)
        bundle.AddIcon(icon)
    frame.SetIcons(bundle)
