import wx

from lib.cursor.setter import CursorKind
from lib.data import CursorElement, AssetType, AssetSources, AssetSourceInfo
from lib.image_pil2wx import PilImg2WxImg
from ui_ctl.element_add_dialog import ElementAddDialog, ElementSelectList, RectElementSource, ImageElementSource
from widget.ect_menu import EtcMenu
from widget.no_tab_notebook import NoTabNotebook
from widget.win_icon import set_multi_size_icon


class C_ElementSelectList(ElementSelectList):
    SHOW_SWITCH_CHOICE = True


class SourceInfoEditDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, element: CursorElement, proj_kind: CursorKind):
        super().__init__(parent, title="编辑元素源信息", size=(1196, 795), style=wx.DEFAULT_FRAME_STYLE)
        self.SetFont(parent.GetFont())
        set_multi_size_icon(self, "assets/icons/element/edit_info.png")
        self.element = element
        self.proj_kind = proj_kind
        self.active_index = 0

        warp = wx.SplitterWindow(self)
        self.source_lc = wx.ListCtrl(warp, style=wx.LC_REPORT)
        self.source_lc.AppendColumn("", width=24)
        self.source_lc.AppendColumn("类型", width=75)
        self.source_lc.AppendColumn("数据", width=275)
        self.load_source_lc()

        right_panel = wx.Panel(warp)
        self.notebook = NoTabNotebook(right_panel)
        self.mc_source = C_ElementSelectList(self.notebook, AssetSources.DEFAULT.value, proj_kind)
        self.rect_source = RectElementSource(self.notebook)
        self.image_source = ImageElementSource(self.notebook)
        self.apply_btn = wx.Button(right_panel, label="应用到所选源信息")

        self.notebook.add_page(self.mc_source)
        self.notebook.add_page(self.rect_source)
        self.notebook.add_page(self.image_source)
        self.notebook.switch_page(0)

        right_sizer = wx.BoxSizer(wx.VERTICAL)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.apply_btn, 0, wx.ALL, 5)
        right_sizer.Add(self.notebook, 1, wx.EXPAND)
        right_sizer.Add(btn_sizer, 0, wx.EXPAND)
        right_panel.SetSizer(right_sizer)
        warp.SplitVertically(self.source_lc, right_panel, 375)
        self.mc_source.SetSashGravity(3 / 8)
        wx.CallLater(1000, warp.SetMinimumPaneSize, 50)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(warp, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.source_lc.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select_source)
        self.source_lc.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_menu)
        self.source_lc.Bind(wx.EVT_RIGHT_DOWN, self.on_menu)
        self.source_lc.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.Bind(wx.EVT_BUTTON, self.on_apply, self.apply_btn)

        self.source_lc.Select(0, False)
        self.source_lc.Select(0, True)

    def on_key(self, event: wx.KeyEvent):
        if event.GetKeyCode() == wx.WXK_UP and event.GetModifiers() == wx.MOD_SHIFT:
            self.exchange_item(self.source_lc.GetFirstSelected(), -1)
        elif event.GetKeyCode() == wx.WXK_DOWN and event.GetModifiers() == wx.MOD_SHIFT:
            self.exchange_item(self.source_lc.GetFirstSelected(), 1)
        else:
            event.Skip()

    def exchange_item(self, index: int, offset: int):
        if not (0 <= index + offset < self.source_lc.GetItemCount()) or index == -1:
            return
        temp = self.element.source_infos[index + offset]
        self.element.source_infos[index + offset] = self.element.source_infos[index]
        self.element.source_infos[index] = temp
        self.load_source_lc()

        self.source_lc.Select(index + offset)
        self.source_lc.EnsureVisible(index + offset)
        self.on_select_source(None)

    def on_menu(self, event: wx.ListEvent | wx.MouseEvent):
        menu = EtcMenu()
        menu.Append("添加 (&A)", self.on_add, icon="element/add.png")
        menu.AppendSeparator()
        if isinstance(event, wx.ListEvent):
            event.Veto()
            index = event.GetIndex()
            menu.Append("上移 (&W)", self.exchange_item, index, -1, icon="action/up.png")
            menu.Append("下移 (&S)", self.exchange_item, index, 1, icon="action/down.png")
            menu.AppendSeparator()
        menu.Append("删除 (&D)", self.on_delete, icon="action/delete.png")
        self.PopupMenu(menu)

    def on_apply(self, _):
        source_win = self.notebook.now_window
        if source_win is self.mc_source:
            if self.mc_source.get_element_info():
                info = self.mc_source.get_element_info(single_frame=True)
                self.element.frames[self.active_index] = info.frames[0][0]
                self.element.source_infos[self.active_index] = AssetSourceInfo(
                    type_=AssetType.ZIP_FILE,
                    source_id=info.source_id,
                    source_path=info.frames[0][1]
                )
            else:
                return
        elif source_win is self.rect_source:
            self.element.source_infos[self.active_index] = AssetSourceInfo(
                type_=AssetType.RECT,
                color=(
                    self.rect_source.color_r.data,
                    self.rect_source.color_g.data,
                    self.rect_source.color_b.data,
                    self.rect_source.color_a.data
                ),
                size=(
                    self.rect_source.size_width.data,
                    self.rect_source.size_height.data
                )
            )
            self.element.frames[self.active_index] = self.element.source_infos[self.active_index].load_frame()
        elif source_win is self.image_source:
            if self.image_source.get_element():
                element = self.image_source.get_element()
                self.element.source_infos[self.active_index] = element.source_infos[0]
                self.element.frames[self.active_index] = element.source_infos[0].load_frame()
            else:
                return
        self.load_source_lc()

    def on_delete(self):
        if len(self.element.source_infos) <= 1:
            wx.MessageBox("至少保留一个源信息", "删除源信息", wx.ICON_ERROR)
            return
        ret = wx.MessageBox("真的要删除源信息吗?", "删除源信息", wx.ICON_QUESTION | wx.YES_NO)
        if ret != wx.YES:
            return
        self.element.source_infos.pop(self.active_index)
        self.element.frames.pop(self.active_index)
        self.active_index = 0
        self.load_source_lc()

    def on_add(self):
        dialog = ElementAddDialog(self, self.proj_kind)
        dialog.ShowModal()
        if not dialog.element:
            return
        if len(dialog.element.source_infos) > 1:
            ret = wx.MessageBox("真的添加多个源信息吗?\n选不会取消哦\n听一听 Kittens Express - Tenkitsune 吧, 很好听的",
                                "添加源信息", wx.ICON_QUESTION | wx.YES_NO)
            if ret != wx.YES:
                return
        for i in range(len(dialog.element.source_infos)):
            self.element.source_infos.append(dialog.element.source_infos[i])
            self.element.frames.append(dialog.element.frames[i])
        self.load_source_lc()

    def on_select_source(self, _):
        self.active_index = int(self.source_lc.GetFirstSelected())
        source_info = self.element.source_infos[self.active_index]
        if source_info.type == AssetType.ZIP_FILE:
            if self.mc_source.source != AssetSources.get_source_by_id(source_info.source_id):
                self.mc_source.source = AssetSources.get_source_by_id(source_info.source_id)
                self.mc_source.load_source()
            assets_map_res = {v: k for k, v in self.mc_source.assets_map.items()}
            item = assets_map_res[source_info.source_path]
            self.mc_source.load_item(item)
            while True:
                parent = self.mc_source.assets_tree.GetItemParent(item)
                self.mc_source.assets_tree.Expand(parent)
                if parent in self.mc_source.loaded_roots:
                    break
                item = parent
            self.mc_source.assets_tree.SelectItem(item)
            self.notebook.switch_page(0)
        elif source_info.type == AssetType.RECT:
            self.rect_source.color_r.set_value(source_info.color[0])
            self.rect_source.color_g.set_value(source_info.color[1])
            self.rect_source.color_b.set_value(source_info.color[2])
            self.rect_source.color_a.set_value(source_info.color[3])
            self.rect_source.size_width.set_value(source_info.size[0])
            self.rect_source.size_height.set_value(source_info.size[1])
            self.notebook.switch_page(1)
        elif source_info.type == AssetType.IMAGE:
            self.image_source.resize_width.set_value(source_info.size[0])
            self.image_source.resize_height.set_value(source_info.size[1])
            self.image_source.preview_bitmap.SetBitmap(PilImg2WxImg(source_info.image).ConvertToBitmap())
            self.image_source.active_image = source_info.image.copy()
            self.notebook.switch_page(2)

    def load_source_lc(self):
        name_map = {
            AssetType.ZIP_FILE: "MC贴图",
            AssetType.RECT: "矩形",
            AssetType.IMAGE: "图像"
        }
        item = self.source_lc.GetFirstSelected()
        self.source_lc.DeleteAllItems()
        for i, source_info in enumerate(self.element.source_infos):
            self.source_lc.InsertItem(i, "")
            self.source_lc.SetItem(i, 1, name_map[source_info.type])
            if source_info.type == AssetType.ZIP_FILE:
                self.source_lc.SetItem(i, 2, source_info.source_path)
            elif source_info.type == AssetType.RECT:
                self.source_lc.SetItem(i, 2, f"{source_info.color} {source_info.size[0]}x{source_info.size[1]}")
            elif source_info.type == AssetType.IMAGE:
                self.source_lc.SetItem(i, 2, f"Image: {source_info.size[0]}x{source_info.size[1]}")

        if item != -1:
            self.source_lc.Unbind(wx.EVT_LIST_ITEM_SELECTED)
            self.source_lc.Select(item)
            self.source_lc.EnsureVisible(item)
            self.source_lc.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select_source)


