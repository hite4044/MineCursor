import json
import re
from enum import Enum
from io import BytesIO

import wx
from PIL import Image, UnidentifiedImageError
from PIL.Image import Resampling

from typing import Optional
from lib.image_pil2wx import PilImg2WxImg
from lib.setter import CursorKind
from lib.ui_interface import ui_class
from ui.element_add_dialog import ElementSelectListUI, ElementAddDialogUI, AssetSource

ROOT_IMAGES = {
    "推荐": "assets/resource_type_icons/Recommend.png",
    "block": "assets/resource_type_icons/Block.png",
    "mob_effect": "assets/resource_type_icons/Effect.png",
    "entity": "assets/resource_type_icons/Entity.png",
    "item": "assets/resource_type_icons/Item.png",
    "painting": "assets/resource_type_icons/Painting.png",
    "particle": "assets/resource_type_icons/Particle.png"
}


class AssetSources(Enum):
    MINECRAFT_1_21_5 = AssetSource("Minecraft 1.21.5",
                                   r"assets/sources/1.21.5/recommend.json",
                                   r"assets/sources/1.21.5/textures.zip")


class ElementAddDialog(ElementAddDialogUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        source: AssetSource
        for source in map(lambda n: n.value, AssetSources.__members__.values()):
            selector = ui_class(ElementSelectListUI)(self.sources_notebook, source, CursorKind.ARROW)
            self.sources_notebook.AddPage(selector, source.name)


def translate_image(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    if image.size == (16, 16):
        return image
    elif image.size == (18, 18):  # 效果图标
        return image.crop((1, 1, 17, 17))
    t_width = min(image.width, 16)
    t_height = min(image.height, 16)
    image = image.resize((t_width, t_height), Resampling.NEAREST)
    if image.size == (16, 16):
        return image
    base = Image.new("RGBA", (16, 16))
    base.paste(image, (int((16 - image.width) / 2), int((16 - image.height) / 2)))  # 居中粘贴
    return base


def get_item_children(tree_view, item: wx.TreeItemId):
    subitems = []
    child, cookie = tree_view.GetFirstChild(item)
    while child:
        subitems.append(child)
        child, cookie = tree_view.GetNextChild(child, cookie)
    return subitems


ES_DIR = 0
ES_SHOWER = 1
ES_MUTIL_DIR = 3


class ElementSelectList(ElementSelectListUI):
    def __init__(self, parent: wx.Window, source: AssetSource, kind: CursorKind):
        super().__init__(parent, source, kind)
        self.zip_file = None
        self.showing_item = None
        self.assets_map: dict[wx.TreeItemId, str] = {}
        self.loaded_roots: list[wx.TreeItemId] = []
        self.dir_image_list: wx.ImageList | None = None
        self.load_source()
        self.assets_tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_expand_root)
        self.assets_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_select_item)
        self.assets_tree.Bind(wx.EVT_LEFT_DOWN, self.on_click)

    def load_source(self):
        from zipfile import ZipFile
        file = ZipFile(self.source.textures_zip)
        root_map: dict[str, wx.TreeItemId] = {}
        animation_root_map: dict[str, tuple[wx.TreeItemId, int]] = {}
        assets_map: dict[wx.TreeItemId, str] = {}
        for full_path, info in file.NameToInfo.items():
            if full_path.count(".") > 1:
                continue
            root_name = full_path.split("/")[0]
            if full_path.endswith("/"):
                if full_path.count("/") != 1:
                    continue
                image = self.tree_image_list.Add(PilImg2WxImg(Image.open(ROOT_IMAGES[root_name])).ConvertToBitmap())
                root = self.assets_tree.AppendItem(self.real_root, full_path[:-1], image)
                root_map[root_name] = root
            else:
                root = root_map[root_name]
                if full_path.split(".")[0][-1] in "0123456789":  # 数字结尾
                    no_fix_path, end_fix = full_path.split(".")
                    no_num_path = re.sub(r'\d+$', '', no_fix_path).rstrip("_") + "." + end_fix
                    number = re.findall(r'\d+$', no_fix_path)[0]
                    if no_num_path not in animation_root_map:
                        ani_root = self.assets_tree.AppendItem(root, no_num_path.split("/")[-1])
                        animation_root_map[no_num_path] = (ani_root, int(number))
                        assets_map[ani_root] = full_path
                        print(f"Create Root: {no_num_path.split('/')[-1]}, {ani_root.ID}")
                    else:
                        ani_root = animation_root_map[no_num_path][0]
                        print(f"Add Animation: {number}, {ani_root.ID}")
                        animation_root_map[no_num_path] = (ani_root, int(number))
                    item = self.assets_tree.AppendItem(ani_root, number)
                    assets_map[item] = full_path
                    continue
                file_name = full_path.split("/")[-1]
                item = self.assets_tree.AppendItem(root, file_name)
                assets_map[item] = full_path

        image = self.tree_image_list.Add(PilImg2WxImg(Image.open(ROOT_IMAGES["推荐"])).ConvertToBitmap())
        recommend_root = self.assets_tree.InsertItem(self.real_root, 0, "推荐", image)
        with open(self.source.recommend_file) as recommend_file:
            recommend_list = json.loads(recommend_file.read())[self.kind.value]
            for recommend_path in recommend_list:
                image_io = BytesIO(file.read(recommend_path))
                pil_image = translate_image(Image.open(image_io))
                image = self.tree_image_list.Add(PilImg2WxImg(pil_image).ConvertToBitmap())
                item = self.assets_tree.AppendItem(recommend_root, recommend_path.split("/")[-1], image)
                assets_map[item] = recommend_path
        self.loaded_roots.append(recommend_root)
        self.assets_tree.Expand(recommend_root)
        self.assets_map = assets_map
        self.zip_file = file

    def on_expand_root(self, event: wx.TreeEvent):
        event.Skip()
        root = event.GetItem()
        if root in self.loaded_roots:
            return
        root_path = self.assets_tree.GetItemText(root)
        if self.real_root != self.assets_tree.GetItemParent(root):
            return
        for item, path in self.assets_map.items():
            if path.startswith(root_path + "/"):
                image_io = BytesIO(self.zip_file.read(path))
                try:
                    pil_image = translate_image(Image.open(image_io))
                except UnidentifiedImageError:
                    continue
                image = self.tree_image_list.Add(PilImg2WxImg(pil_image).ConvertToBitmap())
                self.assets_tree.SetItemImage(item, image)
        self.loaded_roots.append(root)

    def on_click(self, event: wx.MouseEvent):
        event.Skip()
        wx.CallLater(100, self.on_click_delay)

    def on_click_delay(self):
        if self.assets_tree.GetSelection().IsOk():
            self.load_item(self.assets_tree.GetSelection())

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
            children = get_item_children(self.assets_tree, item)
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
        pil_image = image.resize((image.width * mutil, image.height * mutil), Resampling.NEAREST)
        self.asset_shower.SetBitmap(PilImg2WxImg(pil_image))

    def get_element_info(self) -> Optional[list[tuple[Image.Image, str]]]:
        if self.showing_item.IsOk():
            if self.assets_tree.ItemHasChildren(self.showing_item):
                children = get_item_children(self.assets_tree, self.showing_item)
                return [(Image.open(BytesIO(self.zip_file.read(self.assets_map[child]))), self.assets_map[child])
                       for child in children]
            zip_path = self.assets_map[self.showing_item]
            image_io = BytesIO(self.zip_file.read(zip_path))
            return [(Image.open(image_io), zip_path)]
        else:
            return []


if __name__ == "__main__":
    from ui.widget.font import ft

    app = wx.App()
    win = wx.Frame(None)
    win.SetFont(ft(11))
    dlg = ElementAddDialog(win)
    win.Show()
    dlg.ShowModal()
    app.MainLoop()
