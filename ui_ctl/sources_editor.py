from io import BytesIO
from os import rename, makedirs
from os.path import expandvars, join
from zipfile import ZipFile, ZIP_DEFLATED

import toml
import wx
from PIL import Image

from lib.config import config
from lib.data import source_manager, AssetSource
from lib.datas.base_struct import generate_id
from lib.datas.data_dir import path_user_sources
from widget.data_dialog import DataDialog, DataLineParam, DataLineType
from widget.ect_menu import EtcMenu


class SourceDialog(DataDialog):
    def __init__(self, parent: wx.Window, is_create: bool, source: AssetSource):
        super().__init__(parent, "创建新素材源" if is_create else "编辑素材源",
                         DataLineParam("name", "名称", DataLineType.STRING, source.name),
                         DataLineParam("note", "备注", DataLineType.STRING, source.id))
        self.source = source

    def get_result(self) -> AssetSource:
        self.source.name = self.datas["name"]
        return self.source


NOTE_TEMP = """模组协议: {}"""

def load_jar2source(fp: str, extract_dir: str = None):
    jar = ZipFile(fp)
    info_bytes = jar.read("META-INF/mods.toml")
    info = toml.loads(info_bytes.decode("utf-8"))

    # 提取模组信息
    mods = info["mods"][0]
    mod_id = mods["modId"]
    name = mods.get("displayName", "新素材源")
    version = mods.get("version", "未知")
    authors = mods.get("authors", "未知")
    description = mods.get("description", "未知")
    note = NOTE_TEMP.format(info["license"]) if info.get("license") else "未知"
    source_id = f"{name}-{version}-{hex(hash(info_bytes))[2:2+8]}"

    # 保存图标
    if icon := mods.get("logoFile"):
        image = Image.open(BytesIO(jar.read(icon)))
        image = image.convert("RGBA")
        image.save(join(extract_dir, "icon.png"), "PNG")

    # 提取贴图
    assets_zip = ZipFile(join(extract_dir, "textures.zip"), "x", ZIP_DEFLATED, compresslevel=1)
    assets_root = f"assets/{mod_id}/textures/"
    for path, info in jar.NameToInfo.items():
        if path.startswith(assets_root) and path != assets_root:
            if info.is_dir():
                info.filename = info.filename.replace(assets_root, "")
                info.orig_filename = info.orig_filename.replace(assets_root, "")
                assets_zip.filelist.append(info)
            else:
                assets_zip.writestr(path.replace(assets_root, ""), jar.read(path))

    assets_zip.close()

    source = AssetSource(name, source_id, version, authors, description, note, extract_dir)
    source.save()
    config.enabled_sources.append(source.id)

    return source


def load_zip2source(fp: str, extract_dir: str = None):
    pass


class SourcesEditor(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, title="素材源编辑器", style=wx.DEFAULT_FRAME_STYLE)
        self.on_loading_source = False

        self.SetFont(parent.GetFont())
        self.ctrl = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.ctrl.AppendColumn("名称", width=wx.COL_WIDTH_AUTOSIZE)
        self.ctrl.EnableCheckBoxes()
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.ctrl, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.line_to_source: dict[int, AssetSource] = {}

        self.ctrl.Bind(wx.EVT_RIGHT_DOWN, self.on_menu)
        self.ctrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_menu)
        self.ctrl.Bind(wx.EVT_LIST_ITEM_CHECKED, self.on_item_check)

        self.load_sources()

    def load_sources(self):
        self.on_loading_source = True
        self.line_to_source.clear()
        self.ctrl.DeleteAllItems()
        for i, source in enumerate(source_manager.sources):
            item = self.ctrl.InsertItem(i, source.name)
            if source.id in config.enabled_sources:
                self.ctrl.CheckItem(item)
            if source.internal_source:
                self.ctrl.SetItemBackgroundColour(item, wx.Colour(200, 200, 255))
            self.line_to_source[item] = source
        self.on_loading_source = False

    def on_item_menu(self, event: wx.ListEvent):
        item = event.GetIndex()
        source = self.line_to_source[item]
        menu = EtcMenu()
        menu.Append("添加 (&A)", self.on_add_source, icon="source/add.png")
        menu.Append("编辑 (&E)", self.on_edit_source, icon="source/edit.png")

        self.PopupMenu(menu)

    def on_item_check(self, event: wx.ListEvent):
        if self.on_loading_source:
            return
        item = event.GetIndex()
        source = self.line_to_source[item]

        if self.ctrl.IsItemChecked(item) and source.id not in config.enabled_sources:
            config.enabled_sources.append(source.id)
        elif source.id in config.enabled_sources:
            config.enabled_sources.remove(source.id)

        self.load_sources()


    def on_menu(self, event: wx.MouseEvent):
        if self.ctrl.HitTest(event.GetPosition()) != -1:
            event.Skip()
            return

        menu = EtcMenu()
        menu.Append("添加 (&A)", self.on_add_source, icon="source/add.png")
        menu.Append("编辑 (&E)", self.on_edit_source, icon="source/edit.png")

        self.PopupMenu(menu)


    def on_add_source(self):
        dialog = wx.FileDialog(
            self, "新增素材源 (模组Jar/材质包/MineCursor 素材源文件)",
            wildcard="|".join(["模组Jar (*.jar)|*.jar",
                               "材质包 (*.zip)|*.zip",
                               "MineCursor 素材源文件 (*.mcsource)|*.mcsource"]),
            style=wx.FD_OPEN)
        if dialog.ShowModal() != wx.ID_OK:
            return
        fp = dialog.GetPath()
        source_dir = join(path_user_sources, f"SOURCE-EXTRACT-TEMP-{generate_id(4)}")
        makedirs(source_dir, exist_ok=True)
        if fp.endswith(".jar"):
            source = load_jar2source(fp, source_dir)
        elif fp.endswith(".zip"):
            return
        elif fp.endswith(".mcsource"):
            return
        else:
            return
        source.source_dir = join(path_user_sources, source.id)
        rename(source_dir, source.source_dir)
        source_manager.user_sources.append(source)
        self.load_sources()

    # dialog = SourceDialog(self, True, AssetSource())

    def on_edit_source(self, source: AssetSource):
        pass

    def on_delete_source(self, source: AssetSource):
        if source.internal_source:
            wx.MessageBox("内置素材源不能删除", "错误")
            return
        ret = wx.MessageBox("是否删除素材源?", "确认", wx.ICON_WARNING | wx.YES_NO)
        if ret == wx.YES:
            source_manager.user_sources.remove(source)
            source_manager.save_user_source()
            if source.id in config.enabled_sources:
                config.enabled_sources.remove(source.id)
            self.load_sources()
