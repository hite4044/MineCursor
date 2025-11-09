import re
from time import perf_counter

import wx

from lib.config import config
from lib.cursor.setter import CursorKind
from lib.data import CursorElement, source_manager, AssetSourceInfo, AssetType, SubProjectFrames
from lib.log import logger
from lib.perf import Counter
from lib.ui_interface import ui_class
from ui.element_add_dialog import ElementSelectListUI, ElementAddDialogUI, AssetSource
from ui_ctl.element_sources.asset_source import ElementSelectList
from ui_ctl.element_sources.image_source import ImageElementSource
from ui_ctl.element_sources.project_source import ProjectSource
from ui_ctl.element_sources.rect_source import RectElementSource
from ui_ctl.element_sources.temp_source import TemplateSource
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
        timer = Counter()
        super().__init__(parent)
        self.Bind(wx.EVT_WINDOW_CREATE, self.on_window_create)
        self.element: CursorElement | None = None

        bg = self.sources_notebook.GetBackgroundColour()
        self.sources_notebook.SetBackgroundColour(wx.Colour(255, 255, 255))
        source: AssetSource
        for source in source_manager.sources:
            if not source.id in config.enabled_sources:
                continue
            selector = ui_class(ElementSelectListUI)(self.sources_notebook, source, cursor_kind)
            self.sources_notebook.AddPage(selector, source.name, select=(source == source_manager.DEFAULT))
        self.rect_element_source = RectElementSource(self.sources_notebook)
        self.template_source = TemplateSource(self.sources_notebook)
        self.image_element_source = ImageElementSource(self.sources_notebook)
        self.project_source = ProjectSource(self.sources_notebook)
        self.sources_notebook.SetBackgroundColour(bg)

        self.sources_notebook.AddPage(self.rect_element_source, "矩形")
        self.sources_notebook.AddPage(self.template_source, "模板")
        self.sources_notebook.AddPage(self.image_element_source, "图像")
        self.sources_notebook.AddPage(self.project_source, "子项目")

        self.ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        set_multi_size_icon(self, "assets/icons/element/add.png")
        logger.info(f"元素选择器初始化用时: {timer.endT()}")

        self.last_click = perf_counter()
        self.work_timer = 0.0

    def on_window_create(self, event: wx.WindowCreateEvent):
        event.Skip()
        self.load_click_hook(event.GetWindow())

    def load_click_hook(self, window: wx.Window):
        window.Bind(wx.EVT_LEFT_DOWN, self.on_click)

    def on_click(self, event: wx.MouseEvent):
        event.Skip()
        if perf_counter() - self.last_click < 60:
            self.work_timer += perf_counter() - self.last_click
        self.last_click = perf_counter()

    def on_ok(self, _):
        if self.sources_notebook.GetCurrentPage() is self.rect_element_source:
            self.element = self.rect_element_source.get_element()
        elif self.sources_notebook.GetCurrentPage() is self.image_element_source:
            self.element = self.image_element_source.get_element()
        elif self.sources_notebook.GetCurrentPage() is self.project_source:
            self.element = self.project_source.get_element()
        elif self.sources_notebook.GetCurrentPage() is self.template_source:
            if project := self.template_source.get_project():
                element = CursorElement(project.friendly_name, [])
                element.sub_project = project
                element.frames = SubProjectFrames(project)
                self.element = element
            else:
                self.element = None
        else:
            if not self.proc_source_page():
                return
        self.EndModal(wx.ID_OK)
        self.Destroy()

    def proc_source_page(self):
        active_selector: ElementSelectList = self.sources_notebook.GetCurrentPage()
        info = active_selector.get_element_info()
        if info is None:
            wx.MessageBox("请选择一个元素", "错误")
            return False
        element_name = info.frames[0][1].split("/")[-1].split(".")[0].replace("_", " ").title()
        element_name = re.sub(r'\d+$', '', element_name).rstrip()
        frames = [f for f, p in info.frames]
        source_infos = [AssetSourceInfo(AssetType.ZIP_FILE, info.source_id, p) for f, p in info.frames]
        self.element = CursorElement(element_name, frames, source_infos)
        if len(frames) > 1:
            self.element.animation_length = len(frames)
        return True

    def on_cancel(self, _):
        self.EndModal(wx.ID_CANCEL)
        self.Destroy()
    
    def on_close(self, event: wx.CloseEvent):
        self.Destroy()
        event.Skip()


if __name__ == "__main__":
    from widget.font import ft

    app = wx.App()
    win = wx.Frame(None)
    win.SetFont(ft(11))
    dlg = ElementAddDialog(win, CursorKind.ARROW)
    win.Show()
    dlg.ShowModal()
    app.MainLoop()
