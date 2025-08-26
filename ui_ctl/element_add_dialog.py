import re

import wx

from lib.cursor.setter import CursorKind
from lib.data import CursorElement, AssetSources, AssetSourceInfo, AssetType
from lib.ui_interface import ui_class
from ui.element_add_dialog import ElementSelectListUI, ElementAddDialogUI, AssetSource
from ui_ctl.element_sources.asset_source import ElementSelectList
from ui_ctl.element_sources.image_source import ImageElementSource
from ui_ctl.element_sources.rect_source import RectElementSource
from widget.win_icon import set_multi_size_icon

ROOT_IMAGES = {
    "推荐": "assets/resource_type_icons/Recommend.png",
    "block": "assets/resource_type_icons/Block.png",
    "mob_effect": "assets/resource_type_icons/Effect.png",
    "entity": "assets/resource_type_icons/Entity.png",
    "item": "assets/resource_type_icons/Item.png",
    "painting": "assets/resource_type_icons/Painting.png",
    "particle": "assets/resource_type_icons/Particle.png"
}

ROOT_TEXTS = {
    "推荐": "推荐",
    "block": "方块",
    "mob_effect": "状态效果",
    "entity": "实体",
    "item": "物品",
    "painting": "画",
    "particle": "粒子"
}


class ElementAddDialog(ElementAddDialogUI):
    def __init__(self, parent: wx.Window, cursor_kind: CursorKind):
        super().__init__(parent)
        self.element: CursorElement | None = None
        source: AssetSource
        for nam, source_enum in AssetSources.members().items():
            source = source_enum.value
            selector = ui_class(ElementSelectListUI)(self.sources_notebook, source, cursor_kind)
            self.sources_notebook.AddPage(selector, source.name, select=(source_enum == AssetSources.DEFAULT))
        self.rect_element_source = RectElementSource(self.sources_notebook)
        self.image_element_source = ImageElementSource(self.sources_notebook)
        self.sources_notebook.AddPage(self.rect_element_source, "矩形")
        self.sources_notebook.AddPage(self.image_element_source, "图像")
        self.ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.cancel.Bind(wx.EVT_BUTTON, self.on_close)
        set_multi_size_icon(self, "assets/icons/element/add.png")

    def on_ok(self, _):
        if self.sources_notebook.GetCurrentPage() is self.rect_element_source:
            self.proc_rect_page()
        elif self.sources_notebook.GetCurrentPage() is self.image_element_source:
            self.proc_image_page()
        else:
            self.proc_source_page()
        self.EndModal(wx.ID_OK)

    def proc_image_page(self):
        self.element = self.image_element_source.get_element()

    def proc_rect_page(self):
        self.element = self.rect_element_source.get_element()

    def proc_source_page(self):
        active_selector: ElementSelectList = self.sources_notebook.GetCurrentPage()
        info = active_selector.get_element_info()
        if info is None:
            wx.MessageBox("请选择一个元素", "错误")
            return
        element_name = info.frames[0][1].split("/")[-1].split(".")[0].replace("_", " ").title()
        element_name = re.sub(r'\d+$', '', element_name).rstrip()
        frames = [f for f, p in info.frames]
        source_infos = [AssetSourceInfo(AssetType.ZIP_FILE, info.source_id, p) for f, p in info.frames]
        self.element = CursorElement(element_name, frames, source_infos)
        if len(frames) > 1:
            self.element.animation_length = len(frames)

    def on_close(self, _):
        self.EndModal(wx.ID_CANCEL)


if __name__ == "__main__":
    from widget.font import ft

    app = wx.App()
    win = wx.Frame(None)
    win.SetFont(ft(11))
    dlg = ElementAddDialog(win, CursorKind.ARROW)
    win.Show()
    dlg.ShowModal()
    app.MainLoop()
