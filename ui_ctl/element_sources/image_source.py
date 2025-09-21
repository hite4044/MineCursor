from os.path import isfile

import wx
from PIL import Image, ImageGrab
from PIL.Image import Resampling

from lib.data import CursorElement, AssetSourceInfo, AssetType
from lib.image_pil2wx import PilImg2WxImg
from ui.element_add_dialog import ImageElementSourceUI
from widget.data_entry import EVT_DATA_UPDATE


class ImageElementSource(ImageElementSourceUI):
    RESAMPLE_MAP = {
        Resampling.NEAREST: "最近邻",
        Resampling.BILINEAR: "双线性",
        Resampling.HAMMING: "汉明",
        Resampling.BICUBIC: "双三次",
        Resampling.LANCZOS: "Lanczos"
    }

    class MyDropTarget(wx.FileDropTarget):
        def __init__(self, cbk):
            super().__init__()
            self.cbk = cbk

        def OnDropFiles(self, x, y, filenames):
            self.cbk(filenames)

    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.active_image: Image.Image | None = None

        self.file_drop_target = self.MyDropTarget(self.on_drop)
        self.file_drag_wnd.SetDropTarget(self.file_drop_target)

        self.resize_width.set_value(0)
        self.resize_height.set_value(0)
        self.resize_resample.set_value(Resampling.BICUBIC)
        self.path_entry.Bind(wx.EVT_KILL_FOCUS, self.on_path_entry_focus_out)
        self.chs_file_btn.Bind(wx.EVT_BUTTON, self.on_chs_file)
        self.load_paste_board.Bind(wx.EVT_BUTTON, self.on_load_paste_board)

        entries = [
            self.resize_width,
            self.resize_height,
            self.resize_resample
        ]
        for entry in entries:
            entry.Bind(EVT_DATA_UPDATE, self.on_data_change)

        self.preview_bitmap.Bind(wx.EVT_LEFT_DOWN,
                                 lambda e: exec("e.Skip()\nself.preview_bitmap.SetFocus()", {"e": e}, {"self": self}))
        self.preview_bitmap.Bind(wx.EVT_CHAR_HOOK, self.key_hook)

    def on_load_paste_board(self, _=None):
        image = ImageGrab.grabclipboard()
        if isinstance(image, Image.Image):
            self.load_image(image)

    def on_chs_file(self, _):
        fp = wx.FileSelector("选择一个图像文件",
                             wildcard="图像文件|*.jpg;*.jpeg;*.png;*.gif;*.cur;*.ico;*.bmp;*.jiff|所有文件 (*.*)|*.*",
                             flags=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                             parent=self)
        if fp:
            self.load_local_file(fp)

    def on_path_entry_focus_out(self, event: wx.FocusEvent):
        event.Skip()
        self.load_local_file(self.path_entry.GetValue())

    def on_drop(self, filenames: list[str]):
        self.load_local_file(filenames[0])

    def load_local_file(self, fp):  # 加载一个本地文件
        if not isfile(fp):
            return False
        try:
            image = Image.open(fp)
        except Exception as e:
            assert e is not None
            return False
        return self.load_image(image)

    def load_image(self, image):  # 加载一个Image.Image对象
        self.active_image = image
        self.resize_width.set_value(image.width)
        self.resize_height.set_value(image.height)
        self.on_data_change()
        self.Layout()
        return True

    def on_data_change(self, _=None):
        if self.active_image is None:
            if not self.load_local_file(self.path_entry.GetValue()):
                return

        image = self.active_image.copy()
        image = image.resize((self.resize_width.data, self.resize_height.data), self.resize_resample.data)
        self.preview_bitmap.SetBitmap(PilImg2WxImg(image).ConvertToBitmap())

    def get_element(self):
        if self.active_image is None:
            return None

        image = self.active_image.copy()
        image = image.resize((self.resize_width.data, self.resize_height.data), self.resize_resample.data)

        return CursorElement(self.name.data, [image],
                             source_infos=[AssetSourceInfo(AssetType.IMAGE, size=image.size, image=image)])

    def key_hook(self, event: wx.KeyEvent):
        if event.GetKeyCode() == ord("C") and event.GetModifiers() == wx.MOD_CONTROL:
            if self.active_image:
                data = wx.ImageDataObject(PilImg2WxImg(self.active_image))
                wx.TheClipboard.SetData(data)
                wx.Bell()
        elif event.GetKeyCode() == ord("V") and event.GetModifiers() == wx.MOD_CONTROL:
            data = wx.BitmapDataObject()
            wx.TheClipboard.GetData(data)

            if not data.GetBitmap().IsOk():
                data = wx.FileDataObject()
                wx.TheClipboard.GetData(data)
                if data.GetFilenames():
                    filename = data.GetFilenames()[0]
                    self.load_image(Image.open(filename).convert("RGBA"))
            else:
                bitmap = data.GetBitmap()
                buffer = bytearray(bitmap.GetWidth() * bitmap.GetHeight() * 4)
                bitmap.CopyToBuffer(buffer, wx.BitmapBufferFormat_RGBA)
                self.load_image(Image.frombuffer("RGBA", bitmap.GetSize().Get(), buffer))
