import json
import re
from io import BytesIO
from os.path import isfile
from typing import Optional

import wx
from PIL import Image, UnidentifiedImageError
from PIL.Image import Resampling

from lib.cursor.setter import CursorKind
from lib.data import CursorElement, AssetSources, AssetsChoicerAssetInfo, AssetSourceInfo, AssetType
from lib.image_pil2wx import PilImg2WxImg
from lib.ui_interface import ui_class
from ui.element_add_dialog import ElementSelectListUI, ElementAddDialogUI, AssetSource, RectElementSourceUI, \
    ImageElementSourceUI
from widget.data_entry import DataEntryEvent, EVT_DATA_UPDATE

ROOT_IMAGES = {
    "推荐": "assets/resource_type_icons/Recommend.png",
    "block": "assets/resource_type_icons/Block.png",
    "mob_effect": "assets/resource_type_icons/Effect.png",
    "entity": "assets/resource_type_icons/Entity.png",
    "item": "assets/resource_type_icons/Item.png",
    "painting": "assets/resource_type_icons/Painting.png",
    "particle": "assets/resource_type_icons/Particle.png"
}


class ElementAddDialog(ElementAddDialogUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.element: CursorElement | None = None
        source: AssetSource
        for source in map(lambda n: n.value, AssetSources.__members__.values()):
            selector = ui_class(ElementSelectListUI)(self.sources_notebook, source, CursorKind.ARROW)
            self.sources_notebook.AddPage(selector, source.name)
        self.rect_element_source = RectElementSource(self.sources_notebook)
        self.image_element_source = ImageElementSource(self.sources_notebook)
        self.sources_notebook.AddPage(self.rect_element_source, "矩形")
        self.sources_notebook.AddPage(self.image_element_source, "图像")
        self.ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.cancel.Bind(wx.EVT_BUTTON, self.on_close)

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


class RectElementSource(RectElementSourceUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.name.set_value("矩形")
        self.size_width.set_value(16)
        self.size_height.set_value(16)
        self.color_r.set_value(255)
        self.color_g.set_value(255)
        self.color_b.set_value(255)
        self.color_a.set_value(255)
        self.picker.SetColour(wx.Colour(255, 255, 255))
        self.picker.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_pick_color)

    def on_pick_color(self, event: wx.Event):
        event.Skip()
        color = self.picker.GetColour()
        self.color_r.set_value(color.Red())
        self.color_g.set_value(color.Green())
        self.color_b.set_value(color.Blue())

    def get_element(self):
        size = (self.size_width.data, self.size_height.data)
        color = (self.color_r.data, self.color_g.data, self.color_b.data, self.color_a.data)
        frame = Image.new("RGBA", size, color)
        return CursorElement(self.name.data, [frame], [AssetSourceInfo(AssetType.RECT, size=size, color=color)])


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

    def on_data_change(self, event: DataEntryEvent):
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


def translate_item_icon(image: Image.Image) -> Image.Image:
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

NUM_PATTER = re.compile(r'\d+$')

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
        self.tree_image_list.RemoveAll()
        self.assets_tree.DeleteAllItems()

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
                    no_num_path = re.sub(NUM_PATTER, '', no_fix_path).rstrip("_") + "." + end_fix
                    number = re.findall(NUM_PATTER, no_fix_path)[0]
                    if no_num_path not in animation_root_map:
                        ani_root = self.assets_tree.AppendItem(root, no_num_path.split("/")[-1])
                        animation_root_map[no_num_path] = (ani_root, int(number))
                        assets_map[ani_root] = full_path
                    else:
                        ani_root = animation_root_map[no_num_path][0]
                        animation_root_map[no_num_path] = (ani_root, int(number))
                    item = self.assets_tree.AppendItem(ani_root, number)
                    assets_map[item] = full_path
                    continue
                file_name = full_path.split("/")[-1]
                item = self.assets_tree.AppendItem(root, file_name)
                assets_map[item] = full_path
        # 筛选被误判的数字结尾的素材
        for sub_root in get_item_children(self.assets_tree, self.real_root):
            for node in get_item_children(self.assets_tree, sub_root):
                # 遍历所有项
                if not self.assets_tree.ItemHasChildren(node):
                    continue
                children = get_item_children(self.assets_tree, node)
                try:
                    numbers = [int(re.findall(NUM_PATTER, assets_map[child].split(".")[0])[0]) for child in children]
                except IndexError:
                    continue
                numbers.sort()
                if len(numbers) == 1 or list(range(min(numbers), max(numbers)+1)) != numbers:
                    for child in children[::-1]:
                        full_path = assets_map.pop(child)
                        file_name = full_path.split("/")[-1]
                        item = self.assets_tree.InsertItem(sub_root, node, file_name)
                        assets_map[item] = full_path
                    self.assets_tree.Delete(node)

        # 填充推荐列表
        image = self.tree_image_list.Add(PilImg2WxImg(Image.open(ROOT_IMAGES["推荐"])).ConvertToBitmap())
        recommend_root = self.assets_tree.InsertItem(self.real_root, 0, "推荐", image)
        with open(self.source.recommend_file) as recommend_file:
            recommend_list = json.loads(recommend_file.read())[self.kind.value]
            for recommend_path in recommend_list:
                image_io = BytesIO(file.read(recommend_path))
                pil_image = translate_item_icon(Image.open(image_io))
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
                    pil_image = translate_item_icon(Image.open(image_io))
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
            children: list[wx.TreeItemId] = get_item_children(self.assets_tree, item)

            # 按照图片序号排序
            paths: list[str] = [self.assets_map[child] for child in children]
            mapping = {k: v for k, v in zip(paths, children)}
            try:
                paths.sort(key=lambda v: int(re.findall(NUM_PATTER, v.split('.')[0])[0]))
            except IndexError:
                print(paths)
                exit(0)
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
        pil_image = image.resize((image.width * mutil, image.height * mutil), Resampling.NEAREST)
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


if __name__ == "__main__":
    from widget.font import ft

    app = wx.App()
    win = wx.Frame(None)
    win.SetFont(ft(11))
    dlg = ElementAddDialog(win)
    win.Show()
    dlg.ShowModal()
    app.MainLoop()
