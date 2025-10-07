import wx
from PIL import Image


def PilImg2WxImg(image: Image.Image) -> wx.Image:
    """PIL的Image转化为wxImage"""
    bitmap: wx.Image = wx.Image(image.size[0], image.size[1])
    bitmap.SetData(image.convert("RGB").tobytes())
    bitmap.alpha_buffer = image.convert("RGBA").getchannel("A").tobytes()
    bitmap.SetAlphaBuffer(bitmap.alpha_buffer)
    return bitmap

