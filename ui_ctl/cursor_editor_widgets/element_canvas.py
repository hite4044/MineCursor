import threading
import time
from typing import cast
from typing import cast as type_cast

import wx
from PIL import Image
from PIL.Image import Resampling

from lib.data import CursorProject, CursorElement, Position
from lib.image_pil2wx import PilImg2WxImg
from lib.log import logger
from lib.render import render_project_frame
from ui.cursor_editor import ElementCanvasUI
from ui_ctl.cursor_editor_widgets.events import ElementSelectedEvent, ScaleUpdatedEvent, ProjectUpdatedEvent

EC_HOTSPOT_LEN = 5
EC_SCALE_LEVEL = [
    0.06125,
    0.125,
    0.25,
    0.5,
    1.0,
    2.0,
    3.0,
    4.0,
    5.0,
    6.0,
    8.0,
    10.0,
    16.0,
    20.0,
    32.0
]


class ElementCanvas(ElementCanvasUI):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)
        self.active_element: CursorElement | None = None
        self.scale = 10.0
        self.scale_index: int = EC_SCALE_LEVEL.index(self.scale)
        self.x_offset: float = 0.5
        self.y_offset: float = 0.5
        self.frame_index = -1
        self.frames: dict[int, Image.Image] = {}
        self.scaled_frame_cache: dict[int, wx.Bitmap] = {}  # 在不同缩放值下的DC内容缓存
        self.last_point = None
        self.last_index = 0
        self.drag_offset: tuple[int, int] | None = None
        self.cvs_drag_offset: tuple[int, int] | None = None
        self.animation_thread = threading.Thread(target=self.frame_thread)
        self.animation_stop_flag = threading.Event()

        self.SetDoubleBuffered(True)

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.on_dragging)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_scroll)

        if project.is_ani_cursor:
            self.animation_thread.start()

    def set_element(self, element: CursorElement | None):
        self.active_element = element
        self.Refresh()

    def project_updated(self):
        self.clear_frame_cache()
        if self.active_element not in self.project.elements:
            self.active_element = None
        self.Refresh()
        if self.project.is_ani_cursor:
            if not self.animation_thread.is_alive():
                self.animation_thread = threading.Thread(target=self.frame_thread)
                self.animation_stop_flag.clear()
                self.animation_thread.start()
        else:
            if self.animation_thread.is_alive():
                self.animation_stop_flag.set()
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
                self.drag_offset = None
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
            elif self.active_element: # 启动元素的拖动
                ele_pos = self.active_element.position
                self.drag_offset = (pos[0] - ele_pos.x, pos[1] - ele_pos.y)
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

    def frame_thread(self):
        while not self.animation_stop_flag.is_set():
            timer = time.perf_counter()
            self.update_frame()
            if self.project.ani_rates:
                try:
                    wait_time = self.project.ani_rates[self.frame_index] / 60
                except IndexError:
                    wait_time = self.project.ani_rate / 60
            else:
                wait_time = self.project.ani_rate / 60
            self.animation_stop_flag.wait(timeout=max(0.0, wait_time - (time.perf_counter() - timer)))

    def update_frame(self):
        if self.frame_index >= self.project.frame_count:
            self.frame_index = 0
        try:
            self.Refresh()
        except RuntimeError:
            return
        self.frame_index += 1
        if self.frame_index >= self.project.frame_count:
            self.frame_index = 0

    def on_paint(self, _):
        size = self.GetClientSize()
        dc = wx.PaintDC(self)

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
            bitmap = image.ConvertToBitmap()
            self.scaled_frame_cache[self.frame_index] = bitmap
        else:
            bitmap = wx.Bitmap(self.scaled_frame_cache[self.frame_index])

        # 计算画布绘制坐标 + 绘制 + 绘制画布边框
        cvs_x = int(size.width * self.x_offset - bitmap.GetWidth() / 2)
        cvs_y = int(size.height * self.y_offset - bitmap.GetHeight() / 2)
        dc.DrawBitmap(bitmap, cvs_x, cvs_y)
        dc.DrawLineList([
            (cvs_x, cvs_y, cvs_x, cvs_y + bitmap.GetHeight()),
            (cvs_x, cvs_y + bitmap.GetHeight(), cvs_x + bitmap.GetWidth(), cvs_y + bitmap.GetHeight()),
            (cvs_x + bitmap.GetWidth(), cvs_y + bitmap.GetHeight(), cvs_x + bitmap.GetWidth(), cvs_y),
            (cvs_x + bitmap.GetWidth(), cvs_y, cvs_x, cvs_y),
        ])

        # 绘制热点 (十字)
        center = Position(*self.translate_canvas_position(*self.project.center_pos))
        line_hor = (center.x - EC_HOTSPOT_LEN, center.y, center.x + EC_HOTSPOT_LEN + 1, center.y)
        line_ver = (center.x, center.y - EC_HOTSPOT_LEN, center.x, center.y + EC_HOTSPOT_LEN + 1)
        dc.SetPen(wx.Pen(wx.RED))
        dc.DrawLine(*line_hor)
        dc.DrawLine(*line_ver)

        # 绘制元素外框
        if self.active_element:
            dc.SetPen(wx.Pen(wx.RED))
            raw_rect = self.active_element.final_rect
            corner1 = self.translate_canvas_position(raw_rect[0], raw_rect[1])
            corner2 = self.translate_canvas_position(raw_rect[0] + raw_rect[2], raw_rect[1] + raw_rect[3])
            dc.DrawLine(corner1.x, corner1.y, corner2.x, corner1.y)
            dc.DrawLine(corner2.x, corner1.y, corner2.x, corner2.y)
            dc.DrawLine(corner2.x, corner2.y, corner1.x, corner2.y)
            dc.DrawLine(corner1.x, corner2.y, corner1.x, corner1.y)

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
        bitmap: wx.Bitmap = next(iter(self.scaled_frame_cache.values()))
        cvs_x, cvs_y = self.get_canvas_position()
        canvas_rect = wx.Rect(cvs_x, cvs_y, bitmap.GetWidth(), bitmap.GetHeight())
        if not canvas_rect.Contains(position[0], position[1]) and check_border:
            return None
        return (int((position[0] - cvs_x) / bitmap.GetWidth() * self.project.raw_canvas_size[0]),
                int((position[1] - cvs_y) / bitmap.GetHeight() * self.project.raw_canvas_size[1]))

    def get_canvas_size(self) -> tuple[int, int]:
        if self.frames:
            frame = next(iter(self.frames.values()))
        else:
            frame = render_project_frame(self.project, 0)
            self.frames[0] = frame
        scaled_size = (int(frame.width * self.scale), int(frame.height * self.scale))
        return scaled_size

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
