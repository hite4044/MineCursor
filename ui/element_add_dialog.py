import wx

from lib.cursor.setter import CursorKind
from lib.data import AssetSource
from widget.center_text import CenteredText
from widget.data_entry import StringEntry, IntEntry
from widget.font import ft
from widget.no_tab_notebook import NoTabNotebook


class ElementAddDialogUI(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, size=(1200, 800), title="添加素材", style=wx.DEFAULT_FRAME_STYLE)
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
