import wx
from PIL import Image
from PIL.Image import Resampling

from lib.cursor.setter import CursorKind
from lib.data import AssetSource
from lib.dpi import TS
from widget.center_text import CenteredText
from widget.data_entry import StringEntry, IntEntry, EnumEntry
from widget.font import ft
from widget.no_tab_notebook import NoTabNotebook


class ElementAddDialogUI(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, size=TS(1200, 800), title="添加素材", style=wx.DEFAULT_FRAME_STYLE)
        self.SetFont(parent.GetFont())
        self.sources_notebook = wx.Notebook(self)
        self.ok = wx.Button(self, label="确定")
        self.cancel = wx.Button(self, label="取消")

        btn_panel = wx.BoxSizer(wx.HORIZONTAL)
        btn_panel.AddStretchSpacer()
        btn_panel.Add(self.ok, 0)
        btn_panel.AddSpacer(10)
        btn_panel.Add(self.cancel, 0)
        btn_panel.AddSpacer(10)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.sources_notebook, 1, wx.EXPAND)
        sizer.AddSpacer(5)
        sizer.Add(btn_panel, 0, wx.EXPAND)
        sizer.AddSpacer(10)
        self.SetSizer(sizer)


class RectElementSourceUI(wx.Panel):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.name = StringEntry(self, "名称")
        self.size_width = IntEntry(self, "宽度")
        self.size_height = IntEntry(self, "高度")
        self.color_r = IntEntry(self, "R", limits=(0, 255))
        self.color_g = IntEntry(self, "G", limits=(0, 255))
        self.color_b = IntEntry(self, "B", limits=(0, 255))
        self.color_a = IntEntry(self, "A", limits=(0, 255))
        self.color_a.set_value(255)
        self.picker_label = CenteredText(self, label="选择颜色")
        self.picker = wx.ColourPickerCtrl(self, colour=wx.Colour(255, 255, 255))

        sizer = wx.FlexGridSizer(8, 2, 5, 5)
        sizer.AddGrowableCol(1, 1)
        entries = [
            self.name,
            self.size_width,
            self.size_height,
            self.color_r,
            self.color_g,
            self.color_b,
            self.color_a
        ]
        for entry in entries:
            sizer.Add(entry.label, 0, wx.EXPAND)
            sizer.Add(entry.entry, 1, wx.EXPAND)
        sizer.Add(self.picker_label, 0, wx.EXPAND)
        sizer.Add(self.picker, 1, wx.EXPAND)
        self.SetSizer(sizer)


class ImageElementSourceUI(wx.Panel):
    RESAMPLE_MAP = {
        Resampling.NEAREST: "最近邻",
        Resampling.BILINEAR: "双线性",
        Resampling.HAMMING: "汉明",
        Resampling.BICUBIC: "双三次",
        Resampling.LANCZOS: "Lanczos"
    }

    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.active_image: Image.Image | None = None

        self.path_entry = wx.TextCtrl(self)
        self.chs_file_btn = wx.Button(self, label="选择")
        self.load_paste_board = wx.Button(self, label="加载剪切板")
        self.file_drag_wnd = CenteredText(self, label="拖放图片文件至此", style=wx.SIMPLE_BORDER)
        self.name = StringEntry(self, "元素名称")
        self.resize_width = IntEntry(self, "缩放至宽度")
        self.resize_height = IntEntry(self, "缩放至高度")
        self.resize_resample = EnumEntry(self, "缩放方法", self.RESAMPLE_MAP)
        self.preview_bitmap = wx.StaticBitmap(self)

        self.file_drag_wnd.SetFont(ft(24))
        self.file_drag_wnd.SetSize((350, 175))
        self.file_drag_wnd.SetMinSize(self.file_drag_wnd.GetSize())
        self.name.set_value("新图像")

        sizer = wx.BoxSizer(wx.VERTICAL)
        fp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        fp_sizer.Add(CenteredText(self, label="文件路径: "), 0, wx.EXPAND)
        fp_sizer.Add(self.path_entry, 1, wx.EXPAND)
        fp_sizer.Add(self.chs_file_btn, 0, wx.EXPAND)
        fp_sizer.Add(self.load_paste_board, 0, wx.EXPAND)
        sizer.Add(fp_sizer, 0, wx.EXPAND)
        sizer.Add(self.file_drag_wnd, 0, wx.TOP | wx.BOTTOM, 5)
        grid_sizer = wx.FlexGridSizer(4, 2, 5, 5)
        entries = [
            self.name,
            self.resize_width,
            self.resize_height,
            self.resize_resample
        ]
        for entry in entries:
            grid_sizer.Add(entry.label, 0, wx.EXPAND)
            grid_sizer.Add(entry.entry, 1, wx.EXPAND)
        sizer.Add(grid_sizer)
        sizer.Add(self.preview_bitmap, 1, wx.EXPAND)
        self.SetSizer(sizer)



class ElementSelectListUI(wx.SplitterWindow):
    def __init__(self, parent: wx.Window, source: AssetSource, kind: CursorKind):
        super().__init__(parent)
        self.source = source
        self.kind = kind
        self.tree_image_list = wx.ImageList(16, 16)
        self.assets_tree = wx.TreeCtrl(self, style=wx.TR_HIDE_ROOT | wx.TR_DEFAULT_STYLE)
        self.note = NoTabNotebook(self)
        self.dir_view = wx.ListCtrl(self.note, style=wx.LC_LIST)
        self.asset_shower = wx.StaticBitmap(self.note)
        self.note.add_page(self.dir_view)
        self.note.add_page(self.asset_shower)
        self.note.switch_page(0)
        self.assets_tree.AssignImageList(self.tree_image_list)
        self.real_root = self.assets_tree.AddRoot("Assets")
        self.SetSashGravity(0.25)
        self.SplitVertically(self.assets_tree, self.note, 0)
        wx.CallLater(1000, self.SetMinimumPaneSize, 50)


if __name__ == "__main__":
    app = wx.App()
    win = wx.Frame(None)
    win.SetFont(ft(11))
    dlg = ElementAddDialogUI(win)
    win.Show()
    dlg.ShowModal()
    app.MainLoop()
