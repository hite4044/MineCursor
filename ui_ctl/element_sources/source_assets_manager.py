import json
import re
import typing
from enum import Enum
from os.path import expandvars, isfile
from zipfile import ZipInfo

import wx
from win32gui import ExtractIconEx

from lib.cursor.setter import CursorKind
from lib.data import AssetSource, source_manager
from lib.log import logger


class AssetRootLoadWay(Enum):
    FLAT_EXPAND = 0
    AS_TREE = 1
    AS_RECOMMEND = 2


ROOT_IMAGES = {
    "推荐": "assets/icons/asset_types/Recommend.png",
    "block": "assets/icons/asset_types/Block.png",
    "entity": "assets/icons/asset_types/Entity.png",
    "environment": "assets/icons/asset_types/Environment.png",
    "gui": "assets/icons/asset_types/Gui.png",
    "item": "assets/icons/asset_types/Item.png",
    "map": "assets/icons/asset_types/Map.png",
    "misc": "assets/icons/asset_types/Misc.png",
    "mob_effect": "assets/icons/asset_types/Effect.png",
    "painting": "assets/icons/asset_types/Painting.png",
    "particle": "assets/icons/asset_types/Particle.png"
}

ROOT_TEXTS = {
    "推荐": "推荐",
    "block": "方块",
    "entity": "实体",
    "environment": "环境",
    "gui": "界面",
    "item": "物品",
    "map": "地图",
    "misc": "遮罩",
    "mob_effect": "状态效果",
    "painting": "画",
    "particle": "粒子"
}

ROOT_LOADING_WAYS = {
    "推荐": AssetRootLoadWay.AS_RECOMMEND,
    "block": AssetRootLoadWay.FLAT_EXPAND,
    "entity": AssetRootLoadWay.FLAT_EXPAND,
    "environment": AssetRootLoadWay.FLAT_EXPAND,
    "gui": AssetRootLoadWay.AS_TREE,
    "item": AssetRootLoadWay.FLAT_EXPAND,
    "map": AssetRootLoadWay.FLAT_EXPAND,
    "misc": AssetRootLoadWay.FLAT_EXPAND,
    "mob_effect": AssetRootLoadWay.FLAT_EXPAND,
    "painting": AssetRootLoadWay.FLAT_EXPAND,
    "particle": AssetRootLoadWay.FLAT_EXPAND,
}

NUM_PATTER = re.compile(r'_?\d+')
ANIM_FRAME_PATTER = re.compile(r'\d+\.\w+$')


class DirTree:
    def __init__(self, name: str):
        self.name = name
        self.dirs: dict[str, 'DirTree'] = {}
        self.files: list[str] = []

    def find(self, dir_names: list[str]):
        if len(dir_names) == 0:
            return self
        crt_name = dir_names.pop(0)
        return self.dirs[crt_name].find(dir_names) if self.dirs.get(crt_name) else None

    def create_dir(self, dir_names: list[str]):
        if len(dir_names) == 0:
            return self
        crt_name = dir_names.pop(0)
        if crt_name not in self.dirs:
            self.dirs[crt_name] = DirTree(crt_name)
        return self.dirs[crt_name].create_dir(dir_names)

    @staticmethod
    def load(name: str, filelist: list[ZipInfo]):
        root_dir = DirTree(name)
        for info in filelist:
            fp = info.filename.split("/")
            fp.pop(0)
            if info.is_dir():
                root_dir.create_dir(fp[:-1])
            else:
                filename = fp.pop(-1)
                crt_root = root_dir.find(fp.copy())
                if crt_root is None:
                    crt_root = root_dir.create_dir(fp)
                crt_root.files.append(filename)
        return root_dir

    def full_data(self, tree_ctrl: wx.TreeCtrl, root: wx.TreeItemId, assets_roots: list[wx.TreeItemId],
                  dir_path: str = "", assets_map: dict[wx.TreeItemId, str] = None, dir_image: int = -1):
        if assets_map is None:
            assets_map: dict[wx.TreeItemId, str] = {}
            dir_path = f"{self.name}"

        assets_roots.append(root)

        for dir_name, dir_tree in self.dirs.items():
            dir_root = tree_ctrl.AppendItem(root, dir_name, dir_image)
            dir_tree.full_data(tree_ctrl, dir_root, assets_roots, f"{dir_path}/{dir_name}", assets_map, dir_image)
        for file_name in self.files:
            fp = f"{dir_path}/{file_name}"
            item = tree_ctrl.AppendItem(root, file_name)
            assets_map[item] = fp
        return assets_map


RecommendData = dict[str, list[str]]


class SourceAssetsManager:
    def __init__(self, source_id: str, tree_ctrl: wx.TreeCtrl, image_list: wx.ImageList):
        self.cur_kind: CursorKind | None = None
        self.tree_ctrl = tree_ctrl
        self.image_list = image_list
        self.file = source_manager.load_zip(source_id)
        self.root_files_map: dict[str, list[ZipInfo]] = {}  # 从根节点名称 -> 文件列表
        self.assets_roots: dict[wx.TreeItemId, str] = {}  # 从根节点 -> 根节点名称
        self.sub_assets_roots: list[wx.TreeItemId] = []
        self.source: AssetSource | None = None

        self.real_root = self.tree_ctrl.GetRootItem()
        with open("assets/sources/recommend.json") as f:  # 公用推荐
            self.public_recommend: RecommendData = json.load(f)

        try:
            icon_large, icon_small = ExtractIconEx(expandvars("%SystemRoot%/System32/Shell32.dll"), 4, 1)
            icon_small = icon_small[0]
            self.dir_icon = wx.Icon()
            self.dir_icon.CreateFromHICON(icon_small)
            self.dir_image = self.image_list.Add(self.dir_icon)
        except Exception as e:
            logger.error(f"无法提取系统文件夹图标 -> {e.__class__.__qualname__}: {e}")
            self.dir_icon = None
            self.dir_image = -1

    def current_recommend(self):  # 将公用推荐与源自定义推荐合并
        recommend_data: RecommendData = self.public_recommend.copy()
        if self.source.recommend_file and isfile(self.source.recommend_file):
            with open(self.source.recommend_file) as f:
                custom_rmd_data: RecommendData = json.load(f)
            for kind, assets_list in custom_rmd_data.items():
                if kind not in recommend_data:
                    recommend_data[kind] = []
                recommend_data[kind].extend(assets_list)
        return recommend_data

    def load_source(self, source: AssetSource, kind: CursorKind):  # 以指定的指针类型加载一个源
        self.source = source
        self.cur_kind = kind
        self.file = source_manager.load_zip(source.id)
        self.sub_assets_roots.clear()
        if self.dir_icon:
            self.dir_image = self.image_list.Add(self.dir_icon)

        # Step1 -> 提取所有根节点
        root_names: list[str] = []
        self.root_files_map = {}
        for _, info in self.file.NameToInfo.items():
            fp = info.filename.split("/")
            if fp[-1].endswith(".mcmeta"):  # 筛选掉 .mcmeta文件
                continue
            root_name = fp[0]
            if info.is_dir():
                fp.pop(-1)
                if len(fp) == 1:
                    root_names.append(root_name)
            else:
                if root_name not in self.root_files_map:
                    self.root_files_map[root_name] = []
                self.root_files_map[root_name].append(info)

        # Step2 -> 加载根节点
        self.assets_roots.clear()
        for root_name in ["推荐"] + root_names:
            if root_name in ROOT_IMAGES:
                image = self.image_list.Add(wx.Bitmap(ROOT_IMAGES[root_name]))
            else:
                image = self.dir_image
            asset_root = self.tree_ctrl.AppendItem(self.real_root, ROOT_TEXTS.get(root_name, root_name), image)
            self.tree_ctrl.AppendItem(asset_root, "加载中...")
            self.assets_roots[asset_root] = root_name
            if root_name == "推荐":
                self.load_asset_root(asset_root, "推荐", None)

    def load_recommend_root(self, root_item: wx.TreeItemId):
        if not self.source.recommend_file:
            self.tree_ctrl.Delete(root_item)
            return {}
        assets_map: dict[wx.TreeItemId, str] = {}
        recommend_data: RecommendData = self.current_recommend()

        def load_sub_root(root: wx.TreeItemId, files_t: list[str]):  # 加载一个文本列表为一个树节点的子节点
            for fp in files_t:
                item_t = self.tree_ctrl.AppendItem(root, fp.split("/")[-1])
                assets_map[item_t] = fp

        crt_kind_name = typing.cast(str, self.cur_kind.value)
        if crt_kind_name in recommend_data:  # 如果包含这个类型的指针推荐
            folded_root = -1
            if len(recommend_data) > 1:
                folded_root = self.tree_ctrl.AppendItem(root_item, "更多", self.dir_image)  # 收进一个单独的文件夹
            load_sub_root(root_item, recommend_data[crt_kind_name])
            recommend_data.pop(crt_kind_name)  # 从待加载列表中移除
        else:  # 不然就用传入的根节点
            folded_root = root_item
        for kind_name, files in recommend_data.items():
            kind_root = self.tree_ctrl.AppendItem(folded_root, CursorKind(kind_name).kind_name, self.dir_image)
            load_sub_root(kind_root, files)
            self.sub_assets_roots.append(kind_root)
        return assets_map

    def load_flat_expand_root(self, root_item: wx.TreeItemId, filelist: list[ZipInfo]):
        assets_map: dict[wx.TreeItemId, str] = {}

        asset_list = []
        animation_frames: dict[str, dict[int, str]] = {}
        # 初步筛选出动画帧
        for info in filelist:
            full_path = info.filename
            filename = info.filename.split("/")[-1]

            if re.findall(ANIM_FRAME_PATTER, filename):  # 如果文件名以数字结尾
                no_num_path = re.sub(NUM_PATTER, "", full_path)
                number = int(re.findall(NUM_PATTER, filename)[0].lstrip("_"))
                if no_num_path not in animation_frames:
                    animation_frames[no_num_path] = {number: full_path}
                else:
                    animation_frames[no_num_path][number] = full_path
            asset_list.append(full_path)

        # 排除被误判的动画帧 + 排序帧
        for no_num_path, frames in animation_frames.copy().items():
            if len(frames) == 1:  # 只有一帧, pass
                animation_frames.pop(no_num_path)
                continue
            numbers = [number for number, _ in frames.items()]
            numbers.sort()
            if list(range(len(frames))) != numbers:  # 不是有序序列, pass
                animation_frames.pop(no_num_path)
                continue
            # 删除+更新
            first_index = asset_list.index(frames[0])
            [asset_list.remove(path) for path in frames.values()]
            asset_list.insert(first_index, no_num_path)
            # 替换排序过的帧列表
            paths = [frames[number] for number in numbers]
            animation_frames[no_num_path] = {number: path for number, path in zip(numbers, paths)}

        # 填充数据
        for file_path in asset_list:
            if file_path in animation_frames:  # 加载动画帧
                animation_root = self.tree_ctrl.AppendItem(root_item, file_path.split("/")[-1])  # 文件名当标签
                self.sub_assets_roots.append(animation_root)
                assets_map[animation_root] = animation_frames[file_path][0]  # 使用第一帧作为动画根节点的缩略图
                for _, frame_path in animation_frames[file_path].items():
                    filename = frame_path.split("/")[-1]
                    item = self.tree_ctrl.AppendItem(animation_root, filename)
                    assets_map[item] = frame_path
                continue
            # 加载单帧动画
            item = self.tree_ctrl.AppendItem(root_item, file_path.split("/")[-1])  # 文件名当标签
            assets_map[item] = file_path
        return assets_map

    def load_asset_root(self, root_item: wx.TreeItemId, root_name: str, filelist: list[ZipInfo] | None):
        way = ROOT_LOADING_WAYS.get(root_name, AssetRootLoadWay.AS_TREE)
        assets_map: dict[wx.TreeItemId, str] = {}
        if way == AssetRootLoadWay.AS_RECOMMEND:
            assets_map = self.load_recommend_root(root_item)
        elif way == AssetRootLoadWay.FLAT_EXPAND:
            assets_map = self.load_flat_expand_root(root_item, filelist)
        elif way == AssetRootLoadWay.AS_TREE:  # 这个写的爽, 啥也不用做直接开始遍历
            dir_tree = DirTree.load(root_name, filelist)
            assets_map = dir_tree.full_data(self.tree_ctrl, root_item, self.sub_assets_roots, dir_image=self.dir_image)
        return assets_map
