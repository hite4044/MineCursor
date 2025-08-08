from os.path import isfile

import wx
from PIL import Image
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

        entries = [
            self.resize_width,
            self.resize_height,
            self.resize_resample
        ]
        for entry in entries:
            entry.Bind(EVT_DATA_UPDATE, self.on_data_change)

    def on_chs_file(self, _):
        fp = wx.FileSelector("选择一个图像文件",
                             wildcard="图像文件|*.jpg;*.jpeg;*.png;*.gif;*.cur;*.ico;*.bmp;*.jiff|所有文件 (*.*)|*.*",
                             flags=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                             parent=self)
        if fp:
            self.load_image(fp)

    def on_path_entry_focus_out(self, event: wx.FocusEvent):
        event.Skip()
        self.load_image(self.path_entry.GetValue())

    def on_drop(self, filenames: list[str]):
        self.load_image(filenames[0])

    def load_image(self, fp):
        if not isfile(fp):
            return False
        try:
            image = Image.open(fp)
        except Exception as e:
            assert e is not None
            return False
        self.active_image = image
        self.resize_width.set_value(image.width)
        self.resize_height.set_value(image.height)
        return True

    def on_data_change(self, _):
        if self.active_image is None:
            if not self.load_image(self.path_entry.GetValue()):
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
