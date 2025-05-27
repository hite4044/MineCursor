from typing import cast as type_cast

import wx
from PIL import Image, ImageOps
from PIL import ImageDraw

from lib.image_pil2wx import PilImg2WxImg

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


ID_POS = 0
ID_CANVAS = 1
ID_NONE = 2
ID_SCALE = 3


class MaskEditor(wx.Dialog):
    def __init__(self, parent: wx.Window, mask: Image.Image, background: Image.Image | None = None):
        super().__init__(parent, title="编辑遮罩", size=(870, 720), style=wx.DEFAULT_FRAME_STYLE)
        if parent:
            self.SetFont(parent.GetFont())
        mask = ImageOps.invert(mask)
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
        self.ok = wx.Button(self.editor, label="确定")
        self.cancel = wx.Button(self.editor, label="取消")

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.ok, 0)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.cancel, 0)
        btn_sizer_ver = wx.BoxSizer(wx.VERTICAL)
        btn_sizer_ver.AddStretchSpacer()
        btn_sizer_ver.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.editor.SetSizer(btn_sizer_ver)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.editor, 1, wx.EXPAND)
        sizer.Add(self.bar, 0, wx.EXPAND)
        self.SetSizer(sizer)

        self.ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.Bind(EVT_POSITION_UPDATED, self.on_position_updated)
        self.Bind(EVT_SCALE_UPDATED, self.on_scale_updated)

        self.b_canvas = mask.size

    def on_position_updated(self, event: PositionUpdatedEvent):
        self.b_position = event.position

    def on_scale_updated(self, event: ScaleUpdatedEvent):
        self.b_scale = event.scale

    def on_ok(self, _):
        self.EndModal(wx.ID_OK)

    def on_cancel(self, _):
        self.EndModal(wx.ID_CANCEL)

    def get_mask(self):
        return ImageOps.invert(self.mask)

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
    35.0,
    40.0,
    45.0,
    60.0,
    80.0,
    100.0,
]


def get_alpha_back(size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.ImageDraw(image)
    RT = 4
    for y in range(0, size[1], RT):
        for x in range(0, size[0], RT):
            if int((x + y) / RT) % 2 == 0:
                draw.rectangle(((x, y), (x + RT - 1, y + RT - 1)), (200, 200, 200, 255), outline=None)
    return image


class MaskEditorPanel(wx.Window):
    def __init__(self, parent: wx.Window, mask: Image.Image, background: Image.Image | None = None):
        super().__init__(parent)
        if background is None:
            background = Image.new("RGBA", mask.size, (255, 255, 255, 0))
        assert mask.size == background.size
        self.mask = mask
        self.mask_draw = ImageDraw.ImageDraw(mask)
        self.background = background
        self.alpha_back = get_alpha_back(mask.size)
        self.is_drawing: bool = False
        self.draw_or_clear = True
        self.last_draw_position: tuple[int, int] | None = None
        self.draw_color: int = 0xFF
        self.drag_offset: tuple[int, int] | None = None
        self.scale = 8.0
        self.scale_index = 21
        self.x_offset = 0.5
        self.y_offset = 0.5
        self.scaled_bitmap_cache: dict[float, wx.Bitmap] = {}
        self.last_bitmap: wx.Bitmap | None = None
        self.draw_grid_line: bool = False

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
                self.draw_color = 0xFF
                event.Dragging = lambda: True
        elif event.RightDown() and self.translate_local_position(event.GetX(), event.GetY()):
            self.is_drawing = True
            self.draw_or_clear = False
            self.draw_color = 0x00
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
                    self.mask_draw.line((self.last_draw_position, cvs_pos), fill=self.draw_color)
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
        if self.draw_grid_line:
            dc.SetPen(wx.Pen(wx.Colour(128, 128, 128)))
            scale = self.scale
            for i in range(0, self.background.width + 1):
                dc.DrawLine(int(cvs_x + i * scale), cvs_y,
                            int(cvs_x + i * scale), int(cvs_y + self.background.height * scale))
            for i in range(0, self.background.height + 1):
                dc.DrawLine(cvs_x, int(cvs_y + i * scale),
                            int(cvs_x + self.background.width * scale), int(cvs_y + i * scale))

    def render_bitmap(self, scale: float) -> wx.Bitmap:
        image = self.alpha_back.copy()
        image.putalpha(int(255 * 0.35))
        image.paste(self.background, (0, 0), self.background)
        image.paste(ImageOps.invert(self.mask), (0, 0), self.mask)
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
