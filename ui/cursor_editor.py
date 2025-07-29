from typing import cast

import wx
from PIL.Image import Resampling

from lib.cursor.setter import CURSOR_KIND_NAME_OFFICIAL
from lib.data import CursorProject, ReverseWay
from lib.ui_interface import ui_class
from widget.center_text import CenteredText
from widget.data_entry import IntEntry, FloatEntry, DataEntry, StringEntry, BoolEntry, EnumEntry
from widget.font import ft
from widget.no_tab_notebook import NoTabNotebook

ID_POS = 0
ID_RECT = 1
ID_CANVAS = 2
ID_OUTPUT = 3
ID_NONE = 4
ID_SCALE = 5


class CursorEditorUI(wx.Frame):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, size=(1320, 720),
                         title=f"光标项目编辑器 - {project.name if project.name else project.kind.kind_name}")
        self.SetFont(ft(11))

        self.elements_lc = ui_class(ElementListCtrlUI)(self, project)
        self.canvas = ui_class(ElementCanvasUI)(self, project)
        self.info_editor = ui_class(InfoEditorUI)(self, project)
        self.bar = wx.StatusBar(self)
        self.bar.SetFieldsCount(6)
        self.bar.SetStatusWidths([100, 100, 120, 150, -1, 110])
        self.bar.SetStatusText("位置: ", ID_POS)
        self.bar.SetStatusText("大小: ", ID_RECT)
        self.bar.SetStatusText("画布: -1 x -1", ID_CANVAS)
        self.bar.SetStatusText("导出后: -1 x -1", ID_OUTPUT)
        self.bar.SetStatusText("", ID_NONE)
        self.bar.SetStatusText("缩放: 100%", ID_SCALE)

        self._cursor_pos: tuple[int, int] | None = None
        self._rect_size: tuple[int, int] | None = None
        self._canvas_size: tuple[int, int] | None = None
        self._output_size: tuple[int, int] | None = None
        self._scale: float | None = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        hor_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hor_sizer.AddMany([
            (self.elements_lc, 0, wx.EXPAND),
            (self.canvas, 2, wx.EXPAND),
            (self.info_editor, 0, wx.EXPAND)
        ])
        sizer.AddMany([
            (hor_sizer, 1, wx.EXPAND),
            (self.bar, 0, wx.EXPAND)
        ])
        self.SetSizer(sizer)

    @property
    def b_cursor_pos(self):
        return self._cursor_pos

    @b_cursor_pos.setter
    def b_cursor_pos(self, value: tuple[int, int] | None):
        self._cursor_pos = value
        if value is None:
            self.bar.SetStatusText("位置: ", ID_POS)
        else:
            self.bar.SetStatusText(f"位置: {value[0]}, {value[1]}", ID_POS)

    @property
    def b_rect_size(self):
        return self._rect_size

    @b_rect_size.setter
    def b_rect_size(self, value: tuple[int, int] | None):
        self._rect_size = value
        if value is None:
            self.bar.SetStatusText("大小: ", ID_RECT)
        else:
            self.bar.SetStatusText(f"大小: {value[0]} x {value[1]}", ID_RECT)

    @property
    def b_canvas_size(self):
        return self._canvas_size

    @b_canvas_size.setter
    def b_canvas_size(self, value: tuple[int, int]):
        self._canvas_size = value
        self.bar.SetStatusText(f"画布: {value[0]} x {value[1]}", ID_CANVAS)

    @property
    def b_output_size(self):
        return self._output_size

    @b_output_size.setter
    def b_output_size(self, value: tuple[int, int]):
        self._output_size = value
        self.bar.SetStatusText(f"导出后: {value[0]} x {value[1]}", ID_OUTPUT)

    @property
    def b_scale(self):
        return self._scale

    @b_scale.setter
    def b_scale(self, value: float):
        if int(value * 100) == value * 100:
            self.bar.SetStatusText(f"缩放: {int(value * 100)}%", ID_SCALE)
        else:
            self.bar.SetStatusText(f"缩放: {value * 100:.1f}%", ID_SCALE)
        self._scale = value


class ElementListCtrlUI(wx.ListCtrl):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, style=wx.LC_REPORT)
        self.project = project
        self.image_list = wx.ImageList(16, 16)
        self.AppendColumn("", wx.LIST_FORMAT_CENTER, width=28)
        self.AppendColumn("名称", width=200)
        self.AssignImageList(self.image_list, wx.IMAGE_LIST_SMALL)


class ElementCanvasUI(wx.Window):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent)
        self.project = project


class InfoEditorUI(NoTabNotebook):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent)
        self.SetMinSize((300, -1))
        self.proj_editor = ui_class(ProjectInfoEditorUI)(self, project)
        self.element_editor = ui_class(ElementInfoEditorUI)(self)
        self.add_page(self.proj_editor)
        self.add_page(self.element_editor)
        self.switch_page(0)


GroupData = tuple[tuple[str, bool], tuple[tuple, ...]]
EntryType = DataEntry | IntEntry | FloatEntry | StringEntry | BoolEntry | EnumEntry
RESAMPLE_MAP = {
    Resampling.NEAREST: "最近邻",
    Resampling.BILINEAR: "BiLinear",
    Resampling.HAMMING: "汉明",
    Resampling.BICUBIC: "双三次",
    Resampling.LANCZOS: "Lanczos"
}


#  加载定义数据, 并返回组件列表
def load_group_raw(defines: GroupData, sizer: wx.Sizer, parent: wx.Window) -> list[EntryType]:
    label, is_collapse = defines[0]
    panel = wx.CollapsiblePane(parent, label=label, style=wx.CP_NO_TLW_RESIZE | wx.CP_DEFAULT_STYLE)
    panel.SetDoubleBuffered(True)
    panel.Collapse(is_collapse)
    sizer_out = wx.BoxSizer(wx.HORIZONTAL)
    collapse_sizer = wx.FlexGridSizer(len(defines[1]), 2, 5, 5)
    collapse_sizer.AddGrowableCol(1, 1)
    entries = []
    for index in range(len(defines[1])):
        entry_type = defines[1][index][0]
        args = defines[1][index][1:]
        entry: DataEntry = entry_type(panel.GetPane(), *args)
        entries.append(entry)
        collapse_sizer.Add(entry.label, 0, wx.EXPAND)
        collapse_sizer.Add(entry.entry, 1, wx.EXPAND)
    sizer_out.AddSpacer(15)
    sizer_out.Add(collapse_sizer, 1, wx.EXPAND | wx.BOTTOM, 5)
    sizer_out.AddSpacer(5)
    panel.GetPane().SetSizer(sizer_out)
    sizer.Add(panel, 0, wx.EXPAND)
    return entries


class ElementInfoEditorUI(wx.ScrolledWindow):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, size=(200, -1))
        widget_groups: list[GroupData] = [
            (("位置", False), ((IntEntry, "X"), (IntEntry, "Y"))),
            (("缩放", False), ((FloatEntry, "X"), (FloatEntry, "Y"))),
            (("裁剪", True), ((IntEntry, "上"), (IntEntry, "下"), (IntEntry, "左"), (IntEntry, "右"))),
            (("翻转", True), ((BoolEntry, "左右翻转"), (BoolEntry, "上下翻转"), (EnumEntry, "翻转顺序", {
                ReverseWay.X_FIRST: "先翻转X轴",
                ReverseWay.Y_FIRST: "先翻转Y轴",
                ReverseWay.BOTH: "同时翻转"
            }))),
            (("动画", True),
             ((BoolEntry, "启用关键字动画编辑"), (IntEntry, "动画开始"), (IntEntry, "帧间隔"), (IntEntry, "动画帧数"),
              (StringEntry, "总帧数-只读")))
        ]
        sizer = wx.BoxSizer(wx.VERTICAL)

        def load_group(defines: GroupData) -> list[EntryType]:
            return load_group_raw(defines, sizer, self)

        title = CenteredText(self, label="元素信息")
        title.SetFont(ft(16))
        sizer.Add(title, 0, wx.EXPAND | wx.ALL, 5)

        self.name: StringEntry = StringEntry(self, "名称", use_sizer=True)
        sizer.Add(self.name, 0, wx.EXPAND | wx.ALL, 5)

        ret = load_group(widget_groups[0])
        self.pos_x: IntEntry = ret[0]
        self.pos_y: IntEntry = ret[1]

        self.rotation = FloatEntry(self, "旋转角度", use_sizer=True)
        sizer.Add(self.rotation, 0, wx.EXPAND | wx.ALL, 5)

        ret = load_group(widget_groups[1])
        self.scale_x: FloatEntry = ret[0]
        self.scale_y: FloatEntry = ret[1]

        ret = load_group(widget_groups[2])
        self.crop_up: IntEntry = ret[0]
        self.crop_down: IntEntry = ret[1]
        self.crop_left: IntEntry = ret[2]
        self.crop_right: IntEntry = ret[3]

        ret = load_group(widget_groups[3])
        self.reverse_x: BoolEntry = ret[0]
        self.reverse_y: BoolEntry = ret[1]
        self.reverse_way: EnumEntry = ret[2]

        ret = load_group(widget_groups[4])
        self.animation_panel: wx.CollapsiblePane = cast(wx.CollapsiblePane, sizer.GetChildren()[-1].Window)
        self.enable_key_ani: BoolEntry = ret[0]
        self.frame_start: IntEntry = ret[1]
        self.frame_inv: IntEntry = ret[2]
        self.frame_length: IntEntry = ret[3]
        self.animation_frames_count: StringEntry = ret[4]

        self.resample_map = RESAMPLE_MAP
        self.res_panel = wx.BoxSizer(wx.HORIZONTAL)
        self.resample_type = wx.Choice(self, choices=list(self.resample_map.values()))
        self.resample_type.SetSelection(0)
        self.res_panel.Add(CenteredText(self, label="缩放方法: "), 0, wx.EXPAND)
        self.res_panel.AddSpacer(5)
        self.res_panel.Add(self.resample_type, 1, wx.EXPAND)
        sizer.Add(self.res_panel, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)
        self.SetScrollRate(0, 30)

        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.on_collapse)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def on_collapse(self, event: wx.CollapsiblePaneEvent):
        self.on_size(None)
        self.Sizer.Layout()
        self.on_size(None)
        event.Skip()

    def on_size(self, _):
        size = self.Sizer.ComputeFittingWindowSize(self)
        self.SetVirtualSize((cast(tuple, self.GetSize())[0] - 17, size[1]))


class ProjectInfoEditorUI(wx.Panel):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent)
        self.project = project
        sizer = wx.BoxSizer(wx.VERTICAL)
        widget_groups: list[tuple[tuple[str, bool], tuple[tuple[type, str], ...]]] = [
            (("中心", False), ((IntEntry, "X"), (IntEntry, "Y"))),
        ]

        self.title = CenteredText(self, label="项目信息")
        self.title.SetFont(ft(16))
        sizer.Add(self.title, 0, wx.EXPAND | wx.ALL, 5)

        def load_group(defines: GroupData):
            return load_group_raw(defines, sizer, self)

        self.name: StringEntry = StringEntry(self, "名称")
        self.name.set_value(str(project.name))
        self.external_name: StringEntry = StringEntry(self, "外部名称")
        self.external_name.set_value(str(project.external_name))
        self.kind: EnumEntry = EnumEntry(self, "指针类型", CURSOR_KIND_NAME_OFFICIAL)
        self.kind.set_value(project.kind)

        ret = load_group(widget_groups[0])
        self.center_x: IntEntry = ret[0]
        self.center_y: IntEntry = ret[1]
        self.center_x.set_value(project.center_pos.x)
        self.center_y.set_value(project.center_pos.y)

        self.scale: FloatEntry = FloatEntry(self, "缩放")
        self.scale.set_value(project.scale)

        self.is_ani_cursor: BoolEntry = BoolEntry(self, "动画光标")
        self.is_ani_cursor.set_value(project.is_ani_cursor)

        self.frame_count: IntEntry = IntEntry(self, "帧数")
        self.frame_count.set_value(project.frame_count)

        self.ani_rate: IntEntry = IntEntry(self, "帧间隔")
        self.ani_rate.label.SetToolTip("实际帧间隔为 [n * (1/60)] ms")
        self.ani_rate.set_value(project.ani_rate)

        self.resample_map = RESAMPLE_MAP
        self.resample_type = wx.Choice(self, choices=list(self.resample_map.values()))
        self.resample_type.SetSelection(0)

        grid_sizer = wx.FlexGridSizer(8, 2, 5, 5)
        grid_sizer.AddGrowableCol(1, 1)
        grid_sizer.Add(self.name.label, 0, wx.EXPAND)
        grid_sizer.Add(self.name.entry, 1, wx.EXPAND)
        grid_sizer.Add(self.external_name.label, 0, wx.EXPAND)
        grid_sizer.Add(self.external_name.entry, 1, wx.EXPAND)
        grid_sizer.Add(self.kind.label, 0, wx.EXPAND)
        grid_sizer.Add(self.kind.entry, 1, wx.EXPAND)
        grid_sizer.Add(self.scale.label, 0, wx.EXPAND)
        grid_sizer.Add(self.scale.entry, 1, wx.EXPAND)
        grid_sizer.Add(self.is_ani_cursor.label, 0, wx.EXPAND)
        grid_sizer.Add(self.is_ani_cursor.entry, 1, wx.EXPAND)

        grid_sizer.Add(self.frame_count.label, 0, wx.EXPAND)
        grid_sizer.Add(self.frame_count.entry, 1, wx.EXPAND)
        grid_sizer.Add(self.ani_rate.label, 0, wx.EXPAND)
        grid_sizer.Add(self.ani_rate.entry, 1, wx.EXPAND)

        grid_sizer.Add(CenteredText(self, label="缩放方法: "), 0, wx.EXPAND)
        grid_sizer.Add(self.resample_type, 0, wx.EXPAND)
        sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.on_collapse)

        if not project.is_ani_cursor:
            self.ani_rate.disable()
            self.frame_count.disable()

    def on_collapse(self, event: wx.CollapsiblePaneEvent):
        self.Layout()
        event.Skip()
