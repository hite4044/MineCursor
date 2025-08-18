from time import perf_counter
from typing import cast
from typing import cast as type_cast

import wx
from PIL import Image
from PIL.Image import Resampling

from lib.data import CursorProject, CursorElement, Position
from lib.image_pil2wx import PilImg2WxImg
from lib.log import logger
from lib.perf import FPSMonitor
from lib.render import render_project_frame
from ui.cursor_editor import ElementCanvasUI
from ui_ctl.cursor_editor_widgets.events import ElementSelectedEvent, ScaleUpdatedEvent, ProjectUpdatedEvent, \
    AnimationModeChangeEvent, AnimationMode, FrameCounterChangeEvent


class AnimationManager:
    def __init__(self, parent: wx.Window):
        self.timer = wx.Timer(parent)
        self.frame_time_cbk = lambda: 0.0
        self.frame_call_cbk = lambda: None
        self.last_frame_time = 1 / 60
        self.last_update = perf_counter()

        self.offsets_sum = 0
        self.offsets_count = 0

        parent.Bind(wx.EVT_TIMER, self.on_evt_timer, self.timer)

    def is_alive(self):
        return self.timer.IsRunning()

    def on_evt_timer(self, _):
        self.frame_call_cbk()
        frame_time = self.frame_time_cbk()
        self.timer.StartOnce(int(max(0.0, frame_time - self.get_offset()) * 1000))
        self.last_frame_time = frame_time

    def get_offset(self):
        crt_time = perf_counter()
        if self.offsets_count > 4:
            self.offsets_sum /= 2
            self.offsets_count /= 2

        self.offsets_sum += (crt_time - self.last_update) - self.last_frame_time
        self.offsets_count += 1
        self.last_update = crt_time
        return self.offsets_sum / self.offsets_count


    def start(self):
        self.on_evt_timer(None)

    def stop(self):
        if self.timer.IsRunning():
            self.timer.Stop()


EC_HOTSPOT_LEN = 5
EC_SCALE_LEVEL = [
    0.05,
    0.1,
    0.15,
    0.2,
    0.25,
    0.3,
    0.5,
    0.6,
    0.8,
    1.0,
    1.25,
    1.5,
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
    16.0,
    18.0,
    21.0,
    25.0,
    30.0,
    35.0,
    40.0
]


class ElementCanvas(ElementCanvasUI):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)
        self.active_element: CursorElement | None = None
        self.animation_mode = AnimationMode.NORMAL
        self.scale = {1.0: 16.0, 2.0: 8.0}.get(project.scale, 10.0)
        self.scale_index: int = EC_SCALE_LEVEL.index(self.scale)
        self.x_offset: float = 0.5
        self.y_offset: float = 0.5
        self.frame_index = -1
        self.frames: dict[int, Image.Image] = {}
        self.scaled_frame_cache: dict[int, wx.GraphicsBitmap] = {}  # 在不同缩放值下的DC内容缓存
        self.last_point = None
        self.last_index = 0
        self.drag_offset: tuple[int, int] | None = None
        self.cvs_drag_offset: tuple[int, int] | None = None
        self.animation_manager = AnimationManager(self)
        self.fps_monitor = FPSMonitor()

        self.SetDoubleBuffered(True)

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.on_dragging)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_scroll)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy)

        self.animation_manager.frame_call_cbk = self.frame_call
        self.animation_manager.frame_time_cbk = self.get_frame_time
        if project.is_ani_cursor:
            self.animation_manager.start()

    def on_animation_mode_change(self, event: AnimationModeChangeEvent):
        self.animation_mode = event.mode
        if event.mode == AnimationMode.NORMAL:
            if not self.animation_manager.is_alive():
                self.animation_manager.start()
        elif event.mode == AnimationMode.MANUAL:
            if self.animation_manager.is_alive():
                self.animation_manager.stop()
            self.frame_index = event.frame_index
            self.Refresh()

    def on_destroy(self, event: wx.WindowDestroyEvent):
        event.Skip()
        if self.animation_manager.is_alive():
            self.animation_manager.stop()

    def set_element(self, element: CursorElement | None):
        self.active_element = element
        self.Refresh()

    def project_updated(self):
        self.clear_frame_cache()
        if self.active_element not in self.project.elements:
            self.active_element = None
        self.Refresh()
        if self.project.is_ani_cursor:
            if not self.animation_manager.is_alive() and self.animation_mode == AnimationMode.NORMAL:
                self.animation_manager.start()
        else:
            if self.animation_manager.is_alive():
                self.animation_manager.stop()
            self.frame_index = 0

    def clear_frame_cache(self):
        self.frames.clear()
        self.scaled_frame_cache.clear()

    # 鼠标响应函数

    def get_point_elements(self, position: tuple[int, int]):
        elements = []
        for element in self.project.elements:
            if wx.Rect(*element.final_rect).Contains(position):
                elements.append(element)
        return elements

    def on_click(self, event: wx.MouseEvent):
        event.Skip()
        raw_pos = (event.GetX(), event.GetY())
        pos = self.translate_mouse_position(raw_pos)
        if pos is None:
            self.post_element_selected(None)
            return
        elements = self.get_point_elements(pos)
        if len(elements) < 1:
            self.post_element_selected(None)
            return
        if raw_pos == self.last_point:
            element = elements[self.last_index]
            self.last_index += 1
            if self.last_index >= len(elements):
                self.last_index = 0
        else:
            if self.active_element in elements:
                element = self.active_element
            else:
                element = elements[0]
            self.last_index = 1 if len(elements) > 1 else 0
            self.last_point = raw_pos
        self.post_element_selected(element)

    def on_dragging(self, event: wx.MouseEvent):
        event.Skip()
        if event.LeftUp():
            if self.drag_offset:
                logger.debug("拖动结束")
                self.drag_offset: tuple[int, int] | None = None
                wx.PostEvent(self.GetParent(), ProjectUpdatedEvent())
                self.post_element_selected(self.active_element)
            if self.cvs_drag_offset:
                logger.debug("画布拖动结束")
                self.cvs_drag_offset = None
        if event.LeftDown():
            pos = self.translate_mouse_position(cast(tuple[int, int], event.GetPosition()))
            if pos is None:  # 启动画布的拖动
                cvs_x, cvs_y = self.get_canvas_position()
                canvas_size = self.get_canvas_size()
                x_offset = event.GetX() - cvs_x - canvas_size[0] // 2
                y_offset = event.GetY() - cvs_y - canvas_size[1] // 2
                self.cvs_drag_offset = x_offset, y_offset
                logger.debug(f"画布拖动开始")
        if event.Dragging():
            pos = self.translate_mouse_position(cast(tuple[int, int], event.GetPosition()), check_border=False)
            if self.drag_offset:  # 元素的拖动
                if not pos:
                    return
                new_pos = Position(pos[0] - self.drag_offset[0], pos[1] - self.drag_offset[1])
                if self.active_element.position == new_pos:
                    return
                self.active_element.position = new_pos
                logger.debug(f"元素位置更新 -> {self.active_element}")
                self.clear_frame_cache()
            elif self.cvs_drag_offset:  # 画布的拖动
                canvas_size = self.get_canvas_size()
                win_size = type_cast(tuple[int, int], self.GetClientSize())
                self.x_offset = (event.GetX() - self.cvs_drag_offset[0]) / win_size[0]
                self.y_offset = (event.GetY() - self.cvs_drag_offset[1]) / win_size[1]
                canvas_pad_x = max(0, canvas_size[0] - 40) / 2 / win_size[0]
                canvas_pad_y = max(0, canvas_size[1] - 40) / 2 / win_size[1]
                self.x_offset = max(0 - canvas_pad_x, min(1 + canvas_pad_x, self.x_offset))
                self.y_offset = max(0 - canvas_pad_y, min(1 + canvas_pad_y, self.y_offset))
                logger.debug(f"画布偏移更新 -> {self.x_offset}, {self.y_offset}")
            elif self.active_element:  # 启动元素的拖动
                ele_pos = self.active_element.position
                self.drag_offset: tuple[int, int] | None = (pos[0] - ele_pos.x, pos[1] - ele_pos.y)
                logger.debug(f"元素拖动开始 -> {self.active_element}")
            else:
                return
            self.Refresh()

    def post_element_selected(self, element: CursorElement | None):
        event = ElementSelectedEvent(element)
        event.SetEventObject(self)
        wx.CallAfter(wx.PostEvent, self, event)

    def on_scroll(self, event: wx.MouseEvent):
        event.Skip()
        direction = event.GetWheelRotation() / abs(event.GetWheelRotation())
        if direction > 0:  # 放大
            if not self.scale_index < len(EC_SCALE_LEVEL) - 1:
                return
            self.scale_index += 1
            self.scale = EC_SCALE_LEVEL[self.scale_index]
        else:  # 缩小
            if not self.scale_index > 0:
                return
            self.scale_index -= 1
            self.scale = EC_SCALE_LEVEL[self.scale_index]
        self.Refresh()
        logger.debug(f"缩放比例更新 -> {self.scale}")
        self.scaled_frame_cache.clear()
        wx.PostEvent(self, ScaleUpdatedEvent(self.scale))

    # 绘制类函数

    def on_size(self, _):
        self.Refresh()

    def frame_call(self):
        self.update_frame()
        self.frame_add()
        self.fps_monitor.count()

    def update_frame(self):
        try:
            wx.CallAfter(self.Refresh)
        except RuntimeError:
            return

    def get_frame_time(self):
        if self.project.ani_rates:
            try:
                return self.project.ani_rates[self.frame_index] / 60
            except IndexError:
                return self.project.ani_rate / 60
        else:
            return self.project.ani_rate / 60

    def frame_add(self, frame_delta: int = 1):
        if self.frame_index + frame_delta >= self.project.frame_count:
            self.frame_index = frame_delta - ((self.project.frame_count - 1) - self.frame_index)
        else:
            self.frame_index += frame_delta
        event = FrameCounterChangeEvent(self.frame_index)
        wx.PostEvent(self, event)

    def on_paint(self, _):
        size = self.GetClientSize()
        dc = wx.PaintDC(self)
        gc = wx.GraphicsContext.Create(dc)

        # 获取缩放后的帧
        if self.frame_index not in self.frames or self.frame_index not in self.scaled_frame_cache:
            if self.frame_index not in self.frames:
                self.render_frame()
            current_frame = self.frames[self.frame_index]
            current_frame = current_frame.resize(
                (int(current_frame.width * self.scale), int(current_frame.height * self.scale)),
                resample=Resampling.BOX
            )
            image = PilImg2WxImg(current_frame)
            bitmap = gc.CreateBitmap(image.ConvertToBitmap())
            self.scaled_frame_cache[self.frame_index] = bitmap
        else:
            bitmap = self.scaled_frame_cache[self.frame_index]

        # 计算画布绘制坐标 + 绘制 + 绘制画布边框
        width, height = self.get_canvas_size()
        cvs_x = int(size.width * self.x_offset - width / 2)
        cvs_y = int(size.height * self.y_offset - height / 2)
        gc.DrawBitmap(bitmap, cvs_x, cvs_y, width, height)
        gc.DrawLines([
            wx.Point2D(cvs_x, cvs_y),
            wx.Point2D(cvs_x, cvs_y + height),
            wx.Point2D(cvs_x + width, cvs_y + height),
            wx.Point2D(cvs_x + width, cvs_y),
        ])

        # 绘制热点 (十字)
        center = Position(*self.translate_canvas_position(*self.project.center_pos))
        line_hor = [wx.Point2D(center.x - EC_HOTSPOT_LEN, center.y),
                    wx.Point2D(center.x + EC_HOTSPOT_LEN + 1, center.y)]
        line_ver = [wx.Point2D(center.x, center.y - EC_HOTSPOT_LEN),
                    wx.Point2D(center.x, center.y + EC_HOTSPOT_LEN + 1)]
        gc.SetPen(gc.CreatePen(wx.Pen(wx.RED)))
        gc.DrawLines(line_hor)
        gc.DrawLines(line_ver)

        # 绘制元素外框
        if self.active_element:
            raw_rect = self.active_element.final_rect
            corner1 = self.translate_canvas_position(raw_rect[0], raw_rect[1])
            corner2 = self.translate_canvas_position(raw_rect[0] + raw_rect[2], raw_rect[1] + raw_rect[3])
            gc.DrawLines([
                wx.Point2D(corner1.x, corner1.y),
                wx.Point2D(corner2.x, corner1.y),
                wx.Point2D(corner2.x, corner2.y),
                wx.Point2D(corner1.x, corner2.y)
            ])

    def render_frame(self):
        if self.frame_index == -1:  # 无动画
            frame = render_project_frame(self.project, 0)
            self.frames[-1] = frame
        else:
            frame = render_project_frame(self.project, self.frame_index)
            self.frames[self.frame_index] = frame

    # 工具类函数

    def translate_mouse_position(self, position: tuple[int, int], check_border: bool = True) -> tuple[int, int] | None:
        """将窗口里一个点的坐标转化为画布上鼠标的坐标, 超出绘制的画布范围则返回None"""
        if not self.scaled_frame_cache:
            return None
        width, height = self.get_canvas_size()
        cvs_x, cvs_y = self.get_canvas_position()
        canvas_rect = wx.Rect(cvs_x, cvs_y, width, height)
        if not canvas_rect.Contains(position[0], position[1]) and check_border:
            return None
        return (int((position[0] - cvs_x) / width * self.project.raw_canvas_size[0]),
                int((position[1] - cvs_y) / height * self.project.raw_canvas_size[1]))

    def get_canvas_size(self) -> tuple[int, int]:
        size = self.project.canvas_size
        return int(size[0] * self.scale), int(size[1] * self.scale)

    def get_canvas_position(self) -> tuple[int, int]:
        if not self.scaled_frame_cache:
            return 0, 0
        size = self.GetClientSize()
        canvas_size = self.get_canvas_size()
        cvs_x = int(size.width * self.x_offset - canvas_size[0] / 2)
        cvs_y = int(size.height * self.y_offset - canvas_size[1] / 2)
        return cvs_x, cvs_y

    def translate_canvas_position(self, x: int, y: int):
        cvs_x, cvs_y = self.get_canvas_position()
        x *= self.scale * self.project.scale
        y *= self.scale * self.project.scale
        x += cvs_x
        y += cvs_y
        return Position(int(x), int(y))
