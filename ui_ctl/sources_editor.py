import typing
from os import rename, makedirs
from os.path import join, isfile
from shutil import copytree, rmtree

import wx
from PIL import Image, ImageOps

from lib.config import config
from lib.data import source_manager, AssetSource
from lib.datas.base_struct import generate_id
from lib.datas.data_dir import path_user_sources
from lib.dialog_fix import register_close
from lib.dpi import TS
from lib.image_pil2wx import PilImg2WxImg
from lib.perf import Counter
from lib.round_corner import add_rounded_corners
from lib.source_cvt import load_jar2source, load_zip2source
from widget.data_dialog import DataDialog, DataLineParam, DataLineType
from widget.ect_menu import EtcMenu
from widget.win_icon import set_multi_size_icon


class SourceDialog(DataDialog):
    def __init__(self, parent: wx.Window, is_create: bool, source: AssetSource, is_edit: bool = True):
        params = [DataLineParam("name", "名称", DataLineType.STRING, source.name),
                  DataLineParam("id", "ID", DataLineType.STRING, source.id, disabled=not is_create),
                  DataLineParam("version", "版本", DataLineType.STRING, source.version),
                  DataLineParam("authors", "作者", DataLineType.STRING, source.authors),
                  DataLineParam("description", "描述", DataLineType.STRING, source.description),
                  DataLineParam("note", "备注", DataLineType.STRING, source.note, multilined=True)]
        if not is_edit:
            for param in params:
                param.disabled = True
        super().__init__(parent, "创建新素材库" if is_create else "编辑素材库", *params)
        if is_create:
            self.set_icon("source/add.png")
        else:
            self.set_icon("source/edit_info.png")
        self.is_create = is_create
        self.source = source

    def get_result(self) -> AssetSource:
        self.source.name = self.datas["name"]
        self.source.version = self.datas["version"]
        self.source.authors = self.datas["authors"]
        self.source.description = self.datas["description"]
        self.source.note = self.datas["note"]
        if self.is_create:
            self.source.id = self.datas["id"]
        return self.source


class DropTarget(wx.FileDropTarget):
    def __init__(self):
        super().__init__()
        self.func = lambda path: None

    def OnDropFiles(self, x, y, filenames):
        self.func(filenames[0])
        return True


class SourcesEditor(wx.Dialog):
    ICON_SIZE = 92

    def __init__(self, parent: wx.Window):
        super().__init__(parent, title="管理素材库", size=TS(700, 700), style=wx.DEFAULT_FRAME_STYLE)
        set_multi_size_icon(self, "assets/icons/source/source.png")
        self.on_loading_source = False

        self.SetFont(parent.GetFont())
        self.ctrl = wx.ListCtrl(self, style=wx.LC_SMALL_ICON | wx.NO_BORDER)
        self.image_list = wx.ImageList(self.ICON_SIZE, self.ICON_SIZE)
        self.ctrl.EnableCheckBoxes()
        self.ctrl.AssignImageList(self.image_list, wx.IMAGE_LIST_SMALL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.ctrl, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.line_to_source: dict[int, AssetSource] = {}

        self.ctrl.Bind(wx.EVT_RIGHT_DOWN, self.on_menu)
        self.ctrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_menu)
        self.ctrl.Bind(wx.EVT_LIST_ITEM_CHECKED, self.on_item_check)
        self.ctrl.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self.on_item_check)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu)
        self.drop_target = DropTarget()
        self.ctrl.SetDropTarget(self.drop_target)
        self.drop_target.func = self.on_drop

        self.load_sources()
        register_close(self)

    def on_drop(self, path: str):
        wx.CallAfter(self.load_from_file, path)

    def load_sources(self):
        self.on_loading_source = True
        self.line_to_source.clear()
        self.ctrl.DeleteAllItems()
        for i, source in enumerate(source_manager.sources):
            if source.icon:
                image = Image.open(source.icon)
                image.thumbnail((self.ICON_SIZE, self.ICON_SIZE))
                x, y = ((self.ICON_SIZE - image.size[0]) // 2, (self.ICON_SIZE - image.size[1]) // 2)
                image = ImageOps.expand(image, (x, y, x, y), fill=(0, 0, 0, 0))
                with Counter():
                    image = add_rounded_corners(image, 12)
                icon = self.image_list.Add(PilImg2WxImg(image).ConvertToBitmap())
            else:
                icon = -1
            item = self.ctrl.InsertItem(i, source.name, icon)
            if source.id in config.enabled_sources:
                self.ctrl.CheckItem(item)
            self.line_to_source[item] = source
        self.on_loading_source = False

    def get_select_sources(self) -> list[AssetSource]:
        first = self.ctrl.GetFirstSelected()
        selections = []
        while first != -1:
            selections.append(self.line_to_source[first])
            first = self.ctrl.GetNextSelected(first)
        return selections

    def on_item_menu(self, event: wx.ListEvent):
        item = event.GetIndex()
        source = self.line_to_source[item]
        sources = self.get_select_sources()

        def mk_end(li: list):
            if len(li) > 1:
                return f" ({len(li)})"
            return ""

        menu = EtcMenu()
        if len(sources) == 1:
            menu.Append("从文件添加 (&A)", self.on_add_from_file, icon="source/add.png")
            menu.Append("从文件夹添加 (&F)", self.on_add_from_dir, icon="source/add.png")
            menu.AppendSeparator()
            menu.Append("编辑 (&E)", self.on_edit_source, source, icon="source/edit_info.png")
            menu.Append("打开源文件夹 (&Z)", wx.LaunchDefaultApplication, source.source_dir, icon="source/open_dir.png")
            menu.AppendSeparator()
        menu.Append("删除 (&D)" + mk_end(sources), self.on_delete_sources, sources, icon="action/delete.png")

        self.PopupMenu(menu)

    def on_item_check(self, event: wx.ListEvent):
        event.Skip()
        if self.on_loading_source:
            return
        item = event.GetIndex()
        source = self.line_to_source[item]

        if self.ctrl.IsItemChecked(item):
            if source.id not in config.enabled_sources:
                config.enabled_sources.append(source.id)
        else:
            while source.id in config.enabled_sources:
                config.enabled_sources.remove(source.id)

        self.load_sources()

    def on_menu(self, event: wx.MouseEvent):
        if typing.cast(tuple, self.ctrl.HitTest(event.GetPosition()))[0] != -1:
            event.Skip()
            return

        menu = EtcMenu()
        menu.Append("从文件添加 (&A)", self.on_add_from_file, icon="source/add.png")
        menu.Append("从文件夹添加 (&F)", self.on_add_from_dir, icon="source/add.png")

        self.PopupMenu(menu)

    def on_add_from_file(self):
        dialog = wx.FileDialog(
            self, "新增素材库 (模组Jar/材质包)",
            wildcard="模组Jar/材质包 (*.jar;*.zip)|*.jar;*.zip",
            style=wx.FD_OPEN)
        if dialog.ShowModal() != wx.ID_OK:
            return
        self.load_from_file(dialog.GetPath())

    def load_from_file(self, fp: str):
        source_dir = join(path_user_sources, f"SOURCE-EXTRACT-TEMP-{generate_id(4)}")
        makedirs(source_dir, exist_ok=True)
        if fp.endswith(".jar"):
            source = load_jar2source(fp, source_dir)
        elif fp.endswith(".zip"):
            source = load_zip2source(fp, source_dir)
        else:
            wx.MessageBox("只能.jar模组或.zip材质包, 因为要根据后缀名选择加载方法", "错误", wx.OK | wx.ICON_ERROR)
            return
        source.source_dir = join(path_user_sources, source.id)
        try:
            rename(source_dir, source.source_dir)
        except FileExistsError:
            wx.MessageBox("源已存在, 请尝试手动修改新素材库的ID", "错误", wx.OK | wx.ICON_ERROR)
            rmtree(source_dir)
            return

        dialog = SourceDialog(self, True, source)
        if dialog.ShowModal() != wx.ID_OK:
            rmtree(source.source_dir)
            return
        source = dialog.get_result()

        source.save()
        config.enabled_sources.append(source.id)
        source_manager.user_sources.append(source)
        self.load_sources()

    def on_add_from_dir(self):
        dialog = wx.DirDialog(self, "新增素材库 (从程序生成的素材库文件夹)", style=wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() != wx.ID_OK:
            return
        dir_path = dialog.GetPath()
        if not isfile(join(dir_path, "source.json")) or not isfile(join(dir_path, "textures.zip")):
            wx.MessageBox("目录下缺少必要的文件 (source.json/textures.zip)", "错误")
            return

        source = AssetSource.from_file(join(dir_path, "source.json"))
        new_dir = str(join(path_user_sources, source.id))
        copytree(dir_path, new_dir)
        source = AssetSource.from_file(join(new_dir, "source.json"))

        dialog = SourceDialog(self, True, source)
        if dialog.ShowModal() != wx.ID_OK:
            return
        source = dialog.get_result()

        source.save()
        config.enabled_sources.append(source.id)
        source_manager.user_sources.append(source)
        self.load_sources()

    def on_edit_source(self, source: AssetSource):
        dialog = SourceDialog(self, False, source, not source.internal_source)
        if dialog.ShowModal() != wx.ID_OK:
            return
        source = dialog.get_result()
        source.save()
        source_manager.save_source()

    def on_delete_sources(self, sources: list[AssetSource]):
        have_alert = False
        have_asked = False
        for source in sources:
            if source.internal_source:
                if not have_alert:
                    wx.MessageBox(f"内置素材库[{source.name}]不能删除", "错误")
                have_alert = True
                continue
            if not have_asked:
                ret = wx.MessageBox("是否删除这些素材库?" if len(sources) > 1 else f"是否删除素材库[{source.name}]?",
                                    "确认", wx.ICON_WARNING | wx.YES_NO)
                if ret != wx.YES:
                    return
                have_asked = True
            rmtree(source.source_dir)
            source_manager.user_sources.remove(source)
            while source.id in config.enabled_sources:
                config.enabled_sources.remove(source.id)
        source_manager.save_source()
        self.load_sources()
