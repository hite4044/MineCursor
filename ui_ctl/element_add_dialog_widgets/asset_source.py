import re
from enum import Enum
from io import BytesIO
from typing import Optional
from zipfile import ZipFile

import wx
from PIL import Image, UnidentifiedImageError
from PIL.Image import Resampling

from lib.cursor.setter import CursorKind
from lib.data import AssetSources, AssetsChoicerAssetInfo
from lib.image_pil2wx import PilImg2WxImg
from lib.log import logger
from ui.element_add_dialog import ElementSelectListUI, AssetSource
from ui_ctl.element_add_dialog_widgets.source_assets_manager import SourceAssetsManager
from widget.data_dialog import DataDialog, DataLineParam, DataLineType
from widget.ect_menu import EtcMenu


def translate_item_icon(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    if image.size == (16, 16):
        return image
    elif image.size == (18, 18):  # 效果图标
        return image.crop((1, 1, 17, 17))
    t_width = min(image.width, 16)
    t_height = min(image.height, 16)
    image = image.resize((t_width, t_height), Resampling.BICUBIC)
    if image.size == (16, 16):
        return image
    base = Image.new("RGBA", (16, 16))
    base.paste(image, (int((16 - image.width) / 2), int((16 - image.height) / 2)))  # 居中粘贴
    return base


def get_item_children(tree_view, item: wx.TreeItemId) -> list[wx.TreeItemId]:
    subitems = []
    child, cookie = tree_view.GetFirstChild(item)
    while child:
        subitems.append(child)
        child, cookie = tree_view.GetNextChild(child, cookie)
    return subitems


class SourceSwitchDataDialog(DataDialog):
    def __init__(self, parent: wx.Window, now_source: AssetSource):
        SourceEnum = Enum("SourceEnum", tuple(source.id for source in AssetSources.get_sources()))
        super().__init__(parent, "切换素材源", DataLineParam("source_id", "素材源", DataLineType.CHOICE,
                                                             getattr(SourceEnum, now_source.id),
                                                             enum_names={
                                                                 getattr(SourceEnum, source.id): source.name \
                                                                 for source in AssetSources.get_sources()
                                                             }))

    def get_result(self):
        return AssetSources.get_source_by_id(self.datas["source_id"].name)


ES_DIR = 0
ES_SHOWER = 1
ES_MUTIL_DIR = 3

NUM_PATTER = re.compile(r'\d+$')
ANIM_FRAME_PATTER = re.compile(r"\d+\.\w+$")


class ElementSelectList(ElementSelectListUI):
    SHOW_SWITCH_CHOICE = False

    def __init__(self, parent: wx.Window, source: AssetSource, kind: CursorKind):
        super().__init__(parent, source, kind)
        self.zip_file: ZipFile | None = None
        self.showing_item = None
        self.assets = SourceAssetsManager(source.textures_zip, self.assets_tree, self.tree_image_list)
        self.assets_map: dict[wx.TreeItemId, str] = {}
        self.loaded_roots: list[wx.TreeItemId] = []
        self.dir_image_list: wx.ImageList | None = None

        self.load_source()
        self.assets_tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_expand_root)
        self.assets_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_select_item)
        self.assets_tree.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.assets_tree.Bind(wx.EVT_RIGHT_DOWN, self.on_menu)
        self.assets_tree.Expand(self.assets.assets_roots[0])  # 再次展开触发加载缩略图

    def on_menu(self, event: wx.MouseEvent):
        event.Skip()
        menu = EtcMenu()
        menu.Append(f"当前素材源: {self.source.name}").Enable(False)
        menu.Append("切换素材源", self.on_switch_source)
        self.PopupMenu(menu)

    def on_switch_source(self):
        dialog = SourceSwitchDataDialog(self, self.source)
        if dialog.ShowModal() == wx.ID_OK:
            self.source = dialog.get_result()
            self.load_source()

    def load_source(self):
        self.tree_image_list.RemoveAll()
        self.assets_tree.DeleteAllItems()
        self.loaded_roots.clear()

        assets_map: dict[wx.TreeItemId, str] = self.assets.load_source(self.source, self.kind)

        self.assets_map = assets_map
        self.zip_file = self.assets.file

    def on_expand_root(self, event: wx.TreeEvent):  # 展开根节点时, 加载根节点下所有节点的缩略图
        event.Skip()
        root = event.GetItem()
        if root in self.loaded_roots:
            return
        root_parent = self.assets_tree.GetItemParent(root)
        if self.real_root != root_parent and root not in self.assets.assets_roots:  # 必须是根节点的子节点
            return
        for child in get_item_children(self.assets_tree, root):
            try:
                image_io = BytesIO(self.zip_file.read(self.assets_map[child]))
            except KeyError:  # 适配推荐树
                logger.error(f"错误路径: {self.assets_map[child]}")
                continue
            try:
                pil_image = translate_item_icon(Image.open(image_io))
            except UnidentifiedImageError:  # 真TM奇怪的错误
                logger.info(f"图片读取错误: {self.assets_map[child]}")
                continue
            image = self.tree_image_list.Add(PilImg2WxImg(pil_image).ConvertToBitmap())
            self.assets_tree.SetItemImage(child, image)
        self.loaded_roots.append(root)

    def on_click(self, event: wx.MouseEvent):
        event.Skip()
        item, flag = self.assets_tree.HitTest(event.GetPosition())
        if flag in [wx.TREE_HITTEST_ONITEMICON, wx.TREE_HITTEST_ONITEMLABEL]:
            self.load_item(item)

    def on_select_item(self, event: wx.TreeEvent):
        event.Skip()
        item = event.GetItem()
        self.load_item(item)

    def load_item(self, item: wx.TreeItemId):
        if any([item not in self.assets_map,
                self.assets_tree.GetItemParent(item) == self.real_root,
                item == self.showing_item]):
            return
        self.showing_item = item
        if self.assets_tree.ItemHasChildren(item):  # 多帧动画
            self.note.switch_page(ES_DIR)
            self.dir_view.ClearAll()
            if self.dir_image_list:
                self.dir_image_list.Destroy()
            children: list[wx.TreeItemId] = get_item_children(self.assets_tree, item)

            # 按照图片序号排序
            paths: list[str] = [self.assets_map[child] for child in children]
            mapping = {k: v for k, v in zip(paths, children)}
            try:
                paths.sort(key=lambda v: int(re.findall(NUM_PATTER, v.split('.')[0])[0]))
            except IndexError:
                print(paths)
                raise
            children: list[wx.TreeItemId] = [mapping[path] for path in paths]

            image_io = BytesIO(self.zip_file.read(self.assets_map[children[0]]))
            first_image = Image.open(image_io)
            self.dir_image_list = wx.ImageList(first_image.width * ES_MUTIL_DIR, first_image.height * ES_MUTIL_DIR)
            self.dir_view.AssignImageList(self.dir_image_list, wx.IMAGE_LIST_SMALL)
            for i, child in enumerate(children):
                image_io = BytesIO(self.zip_file.read(self.assets_map[child]))
                pil_image = Image.open(image_io).resize(
                    (first_image.width * ES_MUTIL_DIR, first_image.height * ES_MUTIL_DIR),
                    Resampling.NEAREST)
                image = self.dir_image_list.Add(PilImg2WxImg(pil_image).ConvertToBitmap())
                self.dir_view.InsertItem(i, self.assets_tree.GetItemText(child), image)
            return

        # 单帧图片
        image_io = BytesIO(self.zip_file.read(self.assets_map[item]))
        pil_image = Image.open(image_io)
        self.note.switch_page(ES_SHOWER)
        self.set_shower_bitmap(pil_image)
        self.note.switch_page(ES_SHOWER)

    def set_shower_bitmap(self, image: Image.Image):
        image = image.convert("RGBA")
        shower_size = self.asset_shower.GetSize()
        mutil = 1
        while True:
            if image.width * mutil > shower_size[0] or image.height * mutil > shower_size[1]:
                break
            mutil += 1
        mutil -= 1
        if mutil < 1:
            image.thumbnail(shower_size)
            pil_image = image
        else:
            width, height = image.width * mutil, image.height * mutil
            pil_image = image.resize((max(1, round(width)), max(1, round(height))), Resampling.NEAREST)
        self.asset_shower.SetBitmap(PilImg2WxImg(pil_image))

    def get_element_info(self, single_frame: bool = False) -> Optional[AssetsChoicerAssetInfo]:
        if self.showing_item is None:
            return None
        if self.showing_item.IsOk():
            if self.assets_tree.ItemHasChildren(self.showing_item):
                children = get_item_children(self.assets_tree, self.showing_item)
                if single_frame and self.dir_view.IsShown():
                    index = self.dir_view.GetFirstSelected()
                    children = [children[index]]
                paths = [self.assets_map[child] for child in children]
                paths.sort(key=lambda v: int(v.split("_")[-1].split(".")[0]))
                return AssetsChoicerAssetInfo(
                    [(Image.open(BytesIO(self.zip_file.read(path))).convert("RGBA"), path)
                     for path in paths], self.source.id)
            zip_path = self.assets_map[self.showing_item]
            image_io = BytesIO(self.zip_file.read(zip_path))
            return AssetsChoicerAssetInfo([(Image.open(image_io).convert("RGBA"), zip_path)], self.source.id)
        else:
            return None
