from enum import Enum
from typing import cast as type_cast

import wx
from PIL import Image, ImageOps
from PIL import ImageDraw
from PIL.Image import Resampling, Transpose

from lib.clipboard import PUBLIC_MASK_CLIPBOARD
from lib.dpi import TS
from lib.image_pil2wx import PilImg2WxImg
from widget.center_text import CenteredText
from widget.data_dialog import DataDialog, DataLineParam, DataLineType
from widget.win_icon import set_multi_size_icon

mcEVT_SCALE_UPDATED = wx.NewEventType()
EVT_SCALE_UPDATED = wx.PyEventBinder(mcEVT_SCALE_UPDATED, 1)
mc_EVT_POSITION_UPDATED = wx.NewEventType()
EVT_POSITION_UPDATED = wx.PyEventBinder(mc_EVT_POSITION_UPDATED, 1)


class ScaleUpdatedEvent(wx.PyCommandEvent):
    def __init__(self, scale: float):
        super().__init__(mcEVT_SCALE_UPDATED, -1)
        self.scale = scale


class PositionUpdatedEvent(wx.PyCommandEvent):
    def __init__(self, position: tuple[int, int] | None):
        super().__init__(mc_EVT_POSITION_UPDATED, -1)
        self.position = position


class ScaleAction(Enum):
    SCALE_NEAREST = 0
    SCALE_BILINEAR = 1
    SCALE_BICUBIC = 2


class MaskAction(Enum):
    ROTATE_RIGHT = 0
    ROTATE_LEFT = 1
    SCALE_FLIP_X = 2
    SCALE_FLIP_Y = 3


class MaskScaleDialog(DataDialog):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, "复制操作",
                         DataLineParam("type", "选择操作", DataLineType.CHOICE, Resampling.NEAREST, enum_names={
                             Resampling.NEAREST: "最近邻",
                             Resampling.BILINEAR: "双线性",
                             Resampling.BICUBIC: "三次插值"
                         }))

    def get_result(self, mask: Image.Image, target_size: tuple[int, int]):
        return mask.resize(target_size, resample=self.datas["type"])


class MaskActionDialog(wx.Dialog):
    ACTION_MAP = {
        MaskAction.ROTATE_LEFT: "左转",
        MaskAction.ROTATE_RIGHT: "右转",
        MaskAction.SCALE_FLIP_X: "左右翻转",
        MaskAction.SCALE_FLIP_Y: "上下翻转"
    }

    def __init__(self, editor: 'MaskEditor'):
        super().__init__(editor, title="遮罩操作")
        self.SetFont(editor.GetFont())

        self.editor = editor
        self.mask = self.editor.mask
        self.saved_mask = self.editor.mask.copy()
        self.end_btn = wx.Button(self, label="完成")
        self.cancel_btn = wx.Button(self, label="取消")
        self.fill_color_entry = wx.TextCtrl(self)
        self.fill_color_btn = wx.Button(self, label="填充")
        self.fill_color_entry.SetValue("128")

        sizer = wx.BoxSizer(wx.VERTICAL)
        for action, name in self.ACTION_MAP.items():
            btn = wx.Button(self, label=name, id=action.value)
            btn.Bind(wx.EVT_BUTTON, self.on_btn, btn)
            sizer.Add(btn, 0, wx.EXPAND | wx.ALL, 5)

        fill_sizer = wx.BoxSizer(wx.HORIZONTAL)
        fill_sizer.Add(CenteredText(self, label="填充颜色:"), 0, wx.EXPAND | wx.RIGHT, 5)
        fill_sizer.Add(self.fill_color_entry, 1, wx.EXPAND | wx.RIGHT, 5)
        fill_sizer.Add(self.fill_color_btn, 0, wx.EXPAND)
        sizer.Add(fill_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.end_btn, 0, wx.EXPAND | wx.ALL, 5)
        btn_sizer.Add(self.cancel_btn, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)
        self.Fit()

        self.fill_color_btn.Bind(wx.EVT_BUTTON, self.on_fill)
        self.end_btn.Bind(wx.EVT_BUTTON, self.on_finish)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)

    def on_finish(self, _):
        self.EndModal(wx.ID_OK)

    def on_cancel(self, _):
        self.editor.set_mask(self.saved_mask)
        self.EndModal(wx.ID_CANCEL)

    def on_btn(self, event: wx.Event):
        self.on_action(MaskAction(event.GetId()))

    def on_action(self, action: MaskAction):
        if action == MaskAction.ROTATE_RIGHT:
            self.mask = self.mask.rotate(90)
        elif action == MaskAction.ROTATE_LEFT:
            self.mask = self.mask.rotate(-90)
        elif action == MaskAction.SCALE_FLIP_X:
            self.mask = self.mask.transpose(Transpose.FLIP_LEFT_RIGHT)
        elif action == MaskAction.SCALE_FLIP_Y:
            self.mask = self.mask.transpose(Transpose.FLIP_TOP_BOTTOM)
        self.editor.set_mask(self.mask)

    def on_fill(self, _):
        try:
            alpha = int(self.fill_color_entry.GetValue())
            assert 0 <= alpha <= 255
        except (ValueError, AssertionError):
            wx.MessageBox("你这数值有问题啊, (指), 呐, 有杂物\n(数值需为0~255的整数)", "数值错误")
            return
        ret = wx.MessageBox(f"确定要填充遮罩颜色为[{alpha}]吗?", "提示", wx.YES_NO | wx.ICON_QUESTION)
        if ret != wx.YES:
            return
        self.mask = Image.new("L", self.mask.size, (255 - alpha))
        self.editor.set_mask(self.mask)


ID_POS = 0
ID_CANVAS = 1
ID_NONE = 2
ID_SCALE = 3


class MaskEditor(wx.Dialog):
    def __init__(self, parent: wx.Window, mask: Image.Image, background: Image.Image | None = None):
        super().__init__(parent, title="编辑遮罩", size=TS(870, 720), style=wx.DEFAULT_FRAME_STYLE)
        if parent:
            self.SetFont(parent.GetFont())
        set_multi_size_icon(self, "assets/icons/element/edit_mask.png")
        mask = ImageOps.invert(mask)
        self.raw_mask = mask.copy()
        self.mask = mask
        self.background = background
        self._position = (0, 0)
        self._canvas = (-1, -1)
        self._scale = 8.0

        self.editor = MaskEditorPanel(self, mask, background)
        self.bar = wx.StatusBar(self)
        self.bar.SetFieldsCount(4)
        self.bar.SetStatusWidths([100, 120, -1, 110])
        self.bar.SetStatusText("位置: ", ID_POS)
        self.bar.SetStatusText("画布: -1 x -1", ID_CANVAS)
        self.bar.SetStatusText("", ID_NONE)
        self.bar.SetStatusText("缩放: 800%", ID_SCALE)
        self.reset = wx.Button(self.editor, label="重置")
        self.clear_btn = wx.Button(self.editor, label="清空")
        self.action_btn = wx.Button(self.editor, label="操作")
        self.show_grid = wx.CheckBox(self.editor, label="显示网格",
                                     style=wx.CHK_3STATE | wx.CHK_ALLOW_3RD_STATE_FOR_USER)
        self.color_value_label = CenteredText(self.editor, label="255")
        self.color_slider = wx.Slider(self.editor, value=0xFF, maxValue=0xFF)
        self.ok = wx.Button(self.editor, label="确定")
        self.cancel = wx.Button(self.editor, label="取消")
        self.show_grid.Set3StateValue(wx.CHK_UNDETERMINED)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.reset, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.clear_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.action_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.color_value_label, 0, wx.EXPAND)
        btn_sizer.Add(self.color_slider, 1, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.show_grid, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.ok, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.cancel, 0, wx.EXPAND)
        btn_sizer_ver = wx.BoxSizer(wx.VERTICAL)
        btn_sizer_ver.AddStretchSpacer()
        btn_sizer_ver.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.editor.SetSizer(btn_sizer_ver)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.editor, 1, wx.EXPAND)
        sizer.Add(self.bar, 0, wx.EXPAND)
        self.SetSizer(sizer)

        self.reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.action_btn.Bind(wx.EVT_BUTTON, self.on_action)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        self.show_grid.Bind(wx.EVT_CHECKBOX, self.on_switch_show_grid)
        self.ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.color_slider.Bind(wx.EVT_SLIDER, self.on_set_draw_color)
        self.Bind(EVT_POSITION_UPDATED, self.on_position_updated)
        self.Bind(EVT_SCALE_UPDATED, self.on_scale_updated)

        self.b_canvas = mask.size
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.clip = PUBLIC_MASK_CLIPBOARD(self.editor, self.get_mask_func, self.set_mask_func)

    def on_action(self, _):
        dialog = MaskActionDialog(self)
        dialog.ShowModal()

    def get_mask_func(self):
        wx.Bell()
        return self.mask.copy()

    def set_mask_func(self, mask: Image.Image):
        mask = mask.copy()
        if mask.size != self.mask.size:
            ret = wx.MessageBox("遮罩大小不一致, 是否直接缩放并继续?", "错误", wx.YES_NO | wx.ICON_WARNING)
            if ret != wx.YES:
                return
            dialog = MaskScaleDialog(self)
            if not dialog.ShowModal():
                return
            mask = dialog.get_result(mask, self.mask.size)
        self.set_mask(mask)

    def set_mask(self, mask: Image.Image):
        self.mask = self.editor.mask = mask
        self.editor.mask_draw = ImageDraw.ImageDraw(self.editor.mask)
        self.editor.clear_cache()
        self.editor.Refresh()

    def on_clear(self, _):
        ret = wx.MessageBox("确定要清空吗？", "清空", wx.YES_NO)
        if ret == wx.YES:
            self.set_mask(Image.new("L", self.editor.mask.size, 255))

    def on_set_draw_color(self, _):
        value = self.color_slider.GetValue()
        self.editor.draw_color = 255 - value
        self.color_value_label.SetLabel("255")
        self.Layout()
        self.color_value_label.SetLabel(str(value))

    def on_switch_show_grid(self, _):
        state = self.show_grid.Get3StateValue()
        self.editor.GRID_STATE = state
        self.editor.Refresh()

    def on_close(self, event: wx.CloseEvent):
        if self.mask != self.raw_mask:
            ret = wx.MessageBox("确定要放弃没有保存的遮罩吗？", "确认关闭", wx.YES_NO | wx.ICON_QUESTION)
            if ret != wx.YES:
                return
        self.EndModal(wx.ID_CANCEL)
        self.Destroy()
        event.Skip()

    def on_position_updated(self, event: PositionUpdatedEvent):
        self.b_position = event.position

    def on_scale_updated(self, event: ScaleUpdatedEvent):
        self.b_scale = event.scale

    def on_reset(self, _):
        ret = wx.MessageBox("确定要重置吗？", "重置", wx.YES_NO)
        if ret == wx.YES:
            self.set_mask(ImageOps.invert(self.background.getchannel("A")))

    def on_ok(self, _):
        self.EndModal(wx.ID_OK)
        self.Destroy()

    def on_cancel(self, _):
        self.EndModal(wx.ID_CANCEL)
        self.Destroy()

    def get_mask(self):
        mask = ImageOps.invert(self.mask)
        return mask if mask != self.background.getchannel("A") else None

    @property
    def b_position(self):
        return self._position

    @b_position.setter
    def b_position(self, position: tuple[int, int]):
        self._position = position
        if position is None:
            self.bar.SetStatusText("位置: ", ID_POS)
        else:
            self.bar.SetStatusText(f"位置: {position[0]}, {position[1]}", ID_POS)

    @property
    def b_canvas(self):
        return self._canvas

    @b_canvas.setter
    def b_canvas(self, size: tuple[int, int]):
        self._canvas = size
        self.bar.SetStatusText(f"画布: {size[0]} x {size[1]}", ID_CANVAS)

    @property
    def b_scale(self):
        return self._scale

    @b_scale.setter
    def b_scale(self, scale: float):
        self._scale = scale
        self.bar.SetStatusText(f"缩放: {int(self._scale * 100)}%", ID_SCALE)


ME_SCALE_LEVEL = [
    0.05,
    0.10,
    0.15,
    0.2,
    0.4,
    0.5,
    0.7,
    0.8,
    1.0,
    1.25,
    1.50,
    1.75,
    2.0,
    2.5,
    3.0,
    3.5,
    4.0,
    5.0,
    6.0,
    7.0,
    8.0,
    10.0,
    12.0,
    15.0,
    18.0,
    20.0,
    25.0,
    30.0,
    35.0,
    40.0,
    45.0,
    60.0,
    80.0,
    100.0,
]


def get_alpha_back(size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGBA", size, (109, 189, 79, 255))
    draw = ImageDraw.ImageDraw(image)
    RT = 4
    for y in range(0, size[1], RT):
        for x in range(0, size[0], RT):
            if int((x + y) / RT) % 2 == 0:
                draw.rectangle(((x, y), (x + RT - 1, y + RT - 1)), (155, 106, 73, 255), outline=None)
    return image


class MaskEditorPanel(wx.Window):
    GRID_STATE = wx.CHK_UNDETERMINED

    def __init__(self, parent: wx.Window, mask: Image.Image, background: Image.Image | None = None):
        super().__init__(parent)
        if background is None:
            background = Image.new("RGBA", mask.size, (255, 255, 255, 0))
        assert mask.size == background.size
        background = background.copy()
        background.putalpha(128)
        self.mask = mask
        self.mask_draw = ImageDraw.ImageDraw(mask)
        self.background = background
        self.alpha_back = get_alpha_back(mask.size)
        self.is_drawing: bool = False
        self.draw_or_clear = True
        self.last_draw_position: tuple[int, int] | None = None
        self.draw_color: int = 0x00
        self.current_color: int = 0xFF
        self.drag_offset: tuple[int, int] | None = None
        self.scale = 8.0
        self.scale_index = 21
        self.x_offset = 0.5
        self.y_offset = 0.5
        self.scaled_bitmap_cache: dict[float, wx.Bitmap] = {}
        self.last_bitmap: wx.Bitmap | None = None
        self.draw_grid_line: bool = False

        self.alpha_back.putalpha(100)

        self.SetDoubleBuffered(True)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_scroll)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse_drag)

    def on_size(self, event: wx.SizeEvent):
        event.Skip()
        self.Refresh()

    def on_mouse_move(self, event: wx.MouseEvent):
        event.Skip()
        event = PositionUpdatedEvent(self.translate_local_position(event.GetX(), event.GetY()))
        wx.PostEvent(self, event)

    def translate_local_position(self, x: int, y: int) -> tuple[int, int] | None:
        """本窗口相对坐标转化为画布上的坐标"""
        cvs_x, cvs_y = self.get_canvas_position()
        cvs_local_x = x - cvs_x
        cvs_local_y = y - cvs_y
        canvas_size = self.get_canvas_size()
        if cvs_local_x < 0 or cvs_local_y < 0 or cvs_local_x > canvas_size[0] or cvs_local_y > canvas_size[1]:
            return None
        final_x, final_y = int(cvs_local_x / self.scale), int(cvs_local_y / self.scale)
        return max(0, min(self.background.width - 1, final_x)), max(0, min(self.background.height - 1, final_y))

    def on_mouse_drag(self, event: wx.MouseEvent):
        event.Skip()
        if event.LeftDown():
            if self.translate_local_position(event.GetX(), event.GetY()) is None:
                cvs_x, cvs_y = self.get_canvas_position()
                canvas_size = self.get_canvas_size()
                x_offset = event.GetX() - cvs_x - canvas_size[0] // 2
                y_offset = event.GetY() - cvs_y - canvas_size[1] // 2
                self.drag_offset = x_offset, y_offset
                return
            else:
                self.is_drawing = True
                self.draw_or_clear = True
                self.current_color = self.draw_color
                event.Dragging = lambda: True
        elif event.RightDown() and self.translate_local_position(event.GetX(), event.GetY()):
            self.is_drawing = True
            self.draw_or_clear = False
            self.current_color = 0xFF
            event.Dragging = lambda: True
        if event.Dragging():
            if self.drag_offset:
                canvas_size = self.get_canvas_size()
                win_size = type_cast(tuple[int, int], self.GetClientSize())
                self.x_offset = (event.GetX() - self.drag_offset[0]) / win_size[0]
                self.y_offset = (event.GetY() - self.drag_offset[1]) / win_size[1]
                canvas_pad_x = max(0, canvas_size[0] - 40) / 2 / win_size[0]
                canvas_pad_y = max(0, canvas_size[1] - 40) / 2 / win_size[1]
                self.x_offset = max(0 - canvas_pad_x, min(1 + canvas_pad_x, self.x_offset))
                self.y_offset = max(0 - canvas_pad_y, min(1 + canvas_pad_y, self.y_offset))
            elif self.is_drawing:
                cvs_pos = self.translate_local_position(event.GetX(), event.GetY())
                if cvs_pos and cvs_pos != self.last_draw_position:
                    if self.last_draw_position is None:
                        self.last_draw_position = cvs_pos
                    self.mask_draw.line((self.last_draw_position, cvs_pos), fill=self.current_color)
                    self.last_draw_position = cvs_pos
                    self.clear_cache()
        elif event.LeftUp() or event.RightUp():
            self.drag_offset = None
            self.is_drawing = False
            self.last_draw_position = None
            return
        else:
            return
        self.Refresh()

    def clear_cache(self):
        self.scaled_bitmap_cache.clear()

    def on_scroll(self, event: wx.MouseEvent):
        event.Skip()
        if event.GetWheelRotation() > 0 and self.scale_index != len(ME_SCALE_LEVEL) - 1:
            self.scale_index += 1
        elif event.GetWheelRotation() < 0 and self.scale_index != 0:
            self.scale_index -= 1
        self.scale = ME_SCALE_LEVEL[self.scale_index]
        self.draw_grid_line = self.scale >= 20.0
        event = ScaleUpdatedEvent(self.scale)
        wx.PostEvent(self, event)
        self.Refresh()

    def get_canvas_size(self) -> tuple[int, int]:
        return int(self.background.width * self.scale), int(self.background.height * self.scale)

    def get_canvas_position(self) -> tuple[int, int]:
        canvas_size = self.get_canvas_size()
        win_size = type_cast(tuple[int, int], self.GetClientSize())
        return int((win_size[0] * self.x_offset) - canvas_size[0] // 2), int(
            (win_size[1] * self.y_offset) - canvas_size[1] // 2)

    def on_paint(self, _):
        dc = wx.PaintDC(self)
        if self.scale in self.scaled_bitmap_cache:
            bitmap = wx.Bitmap(self.scaled_bitmap_cache[self.scale])
        else:
            bitmap = self.render_bitmap(self.scale)
            self.scaled_bitmap_cache[self.scale] = bitmap
        cvs_x, cvs_y = self.get_canvas_position()
        dc.DrawBitmap(bitmap, cvs_x, cvs_y)
        if (self.draw_grid_line and self.GRID_STATE != wx.CHK_UNCHECKED) or self.GRID_STATE == wx.CHK_CHECKED:
            dc.SetPen(wx.Pen(wx.Colour(128, 128, 128)))
            scale = self.scale
            for i in range(0, self.background.width + 1):
                dc.DrawLine(int(cvs_x + i * scale), cvs_y,
                            int(cvs_x + i * scale), int(cvs_y + self.background.height * scale))
            for i in range(0, self.background.height + 1):
                dc.DrawLine(cvs_x, int(cvs_y + i * scale),
                            int(cvs_x + self.background.width * scale), int(cvs_y + i * scale))

    def render_bitmap(self, scale: float) -> wx.Bitmap:
        image = self.background.copy()
        image.putalpha(int(255 * 0.7))
        image.paste(self.alpha_back, (0, 0), self.mask)
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.NEAREST)
        return PilImg2WxImg(image).ConvertToBitmap()


def test_main():
    app = wx.App()
    mask = Image.new("L", (32, 32), 0)
    draw = ImageDraw.ImageDraw(mask)
    draw.line((0, 0, 100, 100), fill=255)
    dlg = MaskEditor(wx.Frame(None), mask, Image.new("RGBA", (32, 32), (255, 128, 56, 255)))
    dlg.ShowModal()


if __name__ == "__main__":
    test_main()
