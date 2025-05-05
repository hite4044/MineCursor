from dataclasses import dataclass

import wx

from lib.setter import CursorKind
from ui.widget.font import ft
from ui.widget.no_tab_notebook import NoTabNotebook


@dataclass
class AssetSource:
    name: str
    recommend_file: str
    textures_zip: str


class ElementAddDialogUI(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, size=(1200, 800), title="素材选择器", style=wx.DEFAULT_FRAME_STYLE)
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
