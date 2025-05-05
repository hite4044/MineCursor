from typing import Type, Callable

import wx
from PIL import Image

from lib.data import CursorProject, CursorElement, Position
from lib.image_pil2wx import PilImg2WxImg
from lib.render import render_project_frame
from ui.cursor_editor import CursorEditorUI, InfoEditorUI, ElementInfoEditorUI, ElementCanvasUI, ProjectInfoEditorUI, \
    ElementListCtrlUI
from ui.widget.data_entry import DataEntryEvent, DataEntry, EVT_DATA_UPDATE

mcEVT_ELEMENT_SELECTED = wx.NewEventType()
EVT_ELEMENT_SELECTED = wx.PyEventBinder(mcEVT_ELEMENT_SELECTED, 1)
mcEVT_PROJECT_UPDATED = wx.NewEventType()
EVT_PROJECT_UPDATED = wx.PyEventBinder(mcEVT_PROJECT_UPDATED, 1)
mcEVT_SCALE_UPDATED = wx.NewEventType()
EVT_SCALE_UPDATED = wx.PyEventBinder(mcEVT_SCALE_UPDATED, 1)


class ElementSelectedEvent(wx.PyCommandEvent):
    def __init__(self, element: CursorElement | None):
        super().__init__(mcEVT_ELEMENT_SELECTED)
        self.element = element


class ProjectUpdatedEvent(wx.PyCommandEvent):
    def __init__(self):
        super().__init__(mcEVT_PROJECT_UPDATED)



class ScaleUpdatedEvent(wx.PyCommandEvent):
    def __init__(self, scale: float):
        super().__init__(mcEVT_SCALE_UPDATED)
        self.scale = scale


class CursorEditor(CursorEditorUI):
    elements_lc: 'ElementListCtrl'
    canvas: 'ElementCanvas'
    info_editor: 'InfoEditor'

    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)
        self.project = project
        self.b_canvas_size = self.project.canvas_size

        self.canvas.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.canvas.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
        self.Bind(EVT_ELEMENT_SELECTED, self.on_element_selected)
        self.Bind(EVT_PROJECT_UPDATED, self.on_project_updated)
        self.Bind(EVT_SCALE_UPDATED, self.on_scale_updated)

    def on_mouse_move(self, event: wx.MouseEvent):
        event.Skip()
        self.b_cursor_pos = self.canvas.translate_mouse_position(event.GetPosition().IM)

    def on_mouse_leave(self, event: wx.MouseEvent):
        event.Skip()
        self.b_cursor_pos = None

    def on_element_selected(self, event: ElementSelectedEvent):
        self.info_editor.set_element(event.element)
        self.canvas.set_element(event.element)
        if not self.elements_lc.select_processing:
            self.elements_lc.set_element(event.element)

    def on_project_updated(self, _):
        self.canvas.project_updated()
        if self.canvas.active_element is None:
            self.info_editor.set_element(None)

    def on_scale_updated(self, event: ScaleUpdatedEvent):
        self.b_scale = event.scale


class ElementListCtrl(ElementListCtrlUI):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)

        self.line_mapping = {}
        self.select_processing = False
        self.set_processing = False
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_menu)
        for element in project.elements:
            self.add_element(element)

    def on_menu(self, event: wx.ListEvent):
        line = event.GetIndex()
        menu = wx.Menu()
        def ect_binder(name: str, func: Callable, *args):
            item = menu.Append(wx.ID_ANY, name)
            menu.Bind(wx.EVT_MENU, lambda _: func(*args), id=item.GetId())
        ect_binder("添加", lambda: None)
        menu.AppendSeparator()
        ect_binder("上移一层", self.move_element, line, -1)
        ect_binder("下移一层", self.move_element, line, 1)
        menu.AppendSeparator()
        ect_binder("删除", self.remove_element, line)

        self.PopupMenu(menu)

    def send_project_updated(self):
        event = ProjectUpdatedEvent()
        wx.PostEvent(self, event)

    def rebuild_control(self):
        self.line_mapping.clear()
        self.image_list.RemoveAll()
        self.DeleteAllItems()
        for element in self.project.elements:
            self.add_element(element)

    def get_element_by_index(self, index: int):
        element_id = self.line_mapping.pop(index)
        for element in self.project.elements:
            if element.id == element_id:
                break
        else:
            wx.MessageBox("无法找到对应元素")
            return None
        return element

    def remove_element(self, line: int):
        element = self.get_element_by_index(line)
        self.project.elements.remove(element)
        self.rebuild_control()
        self.send_project_updated()

    def move_element(self, line: int, delta: int):
        if not 0 <= line+delta < len(self.project.elements):
            return
        old_element = self.project.elements[line+delta]
        self.project.elements[line+delta] = self.project.elements[line]
        self.project.elements[line] = old_element
        self.rebuild_control()
        self.send_project_updated()

    def add_element(self, element: CursorElement):
        index = self.image_list.Add(PilImg2WxImg(element.frames[0].resize((16, 16))).ConvertToBitmap())
        line = self.GetItemCount()
        self.InsertItem(line, index)
        self.SetItem(line, 1, element.name)
        self.line_mapping[line] = element.id

    def set_element(self, element: CursorElement | None):
        if self.select_processing:
            return

        self.set_processing = True
        # 取消选择所有项
        for i in range(self.GetItemCount()):
            self.Select(i, False)
        if element is not None:
            res_map = {v: k for k, v in self.line_mapping.items()}
            line = res_map[element.id]
            self.Select(line)
        self.set_processing = False

    def on_select(self, event: wx.ListEvent):
        if self.set_processing:
            return
        select_id = self.line_mapping[event.GetIndex()]
        for element in self.project.elements:
            if element.id == select_id:
                break
        else:
            return

        self.select_processing = True
        event = ElementSelectedEvent(element)
        wx.PostEvent(self, event)
        self.select_processing = False


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
    8.0,
    10.0,
    16.0,
    20.0,
    32.0
]


class ElementCanvas(ElementCanvasUI):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)
        self.active_element = None
        self.scale = 4.0
        self.scale_index: int = 7
        self.x_offset: float = 0.5
        self.y_offset: float = 0.5
        self.frame_index = -1
        self.frames: dict[int, Image.Image] = {}
        self.dc_frame_cache: dict[int, wx.Bitmap] = {}  # 在不同缩放值下的DC内容缓存
        self.last_point = None
        self.last_index = 0

        self.SetDoubleBuffered(True)

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_scroll)

        if project.frame_count != -1:
            self.animation_call()

    def set_element(self, element: CursorElement | None):
        self.active_element = element
        self.Refresh()

    def project_updated(self):
        self.frames.clear()
        self.dc_frame_cache.clear()
        if self.active_element not in self.project.elements:
            self.active_element = None
        self.Refresh()

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
            element = elements[0]
            self.last_index = 1 if len(elements) > 1 else 0
            self.last_point = raw_pos
        self.post_element_selected(element)

    def post_element_selected(self, element: CursorElement | None):
        event = ElementSelectedEvent(element)
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
        self.dc_frame_cache.clear()
        wx.PostEvent(self, ScaleUpdatedEvent(self.scale))

    # 绘制类函数

    def on_size(self, _):
        self.Refresh()

    def animation_call(self):
        wx.CallLater(self.project.ani_rate, self.animation_call)
        try:
            self.Refresh()
        except RuntimeError:
            return
        self.frame_index += 1
        if self.frame_index >= self.project.frame_count:
            self.frame_index = 0

    def on_paint(self, _):
        size = self.GetClientSize()
        p_dc = wx.PaintDC(self)

        # 获取缩放后的帧
        if self.frame_index not in self.frames or self.frame_index not in self.dc_frame_cache:
            if self.frame_index not in self.frames:
                self.render_frame()
            current_frame = self.frames[self.frame_index]
            current_frame = current_frame.resize(
                (int(current_frame.width * self.scale), int(current_frame.height * self.scale)),
                resample=self.project.resample
            )
            image = PilImg2WxImg(current_frame)
            bitmap = image.ConvertToBitmap()
            self.dc_frame_cache[self.frame_index] = bitmap
        else:
            bitmap = wx.Bitmap(self.dc_frame_cache[self.frame_index])

        # 计算画布绘制坐标 + 绘制
        cvs_x = int(size.width * self.x_offset - bitmap.GetWidth() / 2)
        cvs_y = int(size.height * self.y_offset - bitmap.GetHeight() / 2)
        p_dc.DrawBitmap(bitmap, cvs_x, cvs_y)

        # 绘制热点 (十字)
        center = Position(*self.translate_canvas_position(*self.project.center_pos))
        line_hor = (center.x - EC_HOTSPOT_LEN, center.y, center.x + EC_HOTSPOT_LEN + 1, center.y)
        line_ver = (center.x, center.y - EC_HOTSPOT_LEN, center.x, center.y + EC_HOTSPOT_LEN + 1)
        p_dc.SetPen(wx.Pen(wx.RED))
        p_dc.DrawLine(*line_hor)
        p_dc.DrawLine(*line_ver)

        # 绘制元素外框
        if self.active_element:
            p_dc.SetPen(wx.Pen(wx.RED))
            raw_rect = self.active_element.final_rect
            corner1 = self.translate_canvas_position(raw_rect[0], raw_rect[1])
            corner2 = self.translate_canvas_position(raw_rect[0] + raw_rect[2], raw_rect[1] + raw_rect[3])
            p_dc.DrawLine(corner1.x, corner1.y, corner2.x, corner1.y)
            p_dc.DrawLine(corner2.x, corner1.y, corner2.x, corner2.y)
            p_dc.DrawLine(corner2.x, corner2.y, corner1.x, corner2.y)
            p_dc.DrawLine(corner1.x, corner2.y, corner1.x, corner1.y)

    def render_frame(self):
        if self.frame_index == -1:  # 无动画
            frame = render_project_frame(self.project, 0)
            self.frames[-1] = frame
        else:
            frame = render_project_frame(self.project, self.frame_index)
            self.frames[self.frame_index] = frame

    # 工具类函数

    def translate_mouse_position(self, position: tuple[int, int]) -> tuple[int, int] | None:
        """将窗口里一个点的坐标转化为画布上鼠标的坐标, 超出绘制的画布范围则返回None"""
        if not self.dc_frame_cache:
            return None
        bitmap: wx.Bitmap = next(iter(self.dc_frame_cache.values()))
        cvs_x, cvs_y = self.get_canvas_draw_position()
        canvas_rect = wx.Rect(cvs_x, cvs_y, bitmap.GetWidth(), bitmap.GetHeight())
        if not canvas_rect.Contains(position[0], position[1]):
            return None
        return (int((position[0] - cvs_x) / bitmap.GetWidth() * self.project.raw_canvas_size[0]),
                int((position[1] - cvs_y) / bitmap.GetHeight() * self.project.raw_canvas_size[1]))

    def get_canvas_draw_position(self) -> tuple[int, int]:
        if not self.dc_frame_cache:
            return 0, 0
        size = self.GetClientSize()
        bitmap: wx.Bitmap = next(iter(self.dc_frame_cache.values()))
        cvs_x = int(size.width * self.x_offset - bitmap.GetWidth() / 2)
        cvs_y = int(size.height * self.y_offset - bitmap.GetHeight() / 2)
        return cvs_x, cvs_y

    def translate_canvas_position(self, x: int, y: int):
        cvs_x, cvs_y = self.get_canvas_draw_position()
        x *= self.scale * self.project.scale
        y *= self.scale * self.project.scale
        x += cvs_x
        y += cvs_y
        return Position(int(x), int(y))


class InfoEditor(InfoEditorUI):
    element_editor: 'ElementInfoEditor'

    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)

    def set_element(self, element: CursorElement | None):
        if element is None:
            self.switch_page(0)
        else:
            self.switch_page(1)
            self.element_editor.set_element(element)


def create_cfg_bind(widget: DataEntry, element, cfg_path: str):
    def warp(event: DataEntryEvent):
        if cfg_path.count(".") == 1:
            attr_name, t_field_name = cfg_path.split('.')
            attr = getattr(element, attr_name)
            field_names: tuple[str] = getattr(attr, "_fields")
            new_datas = []
            for field_name in field_names:
                if field_name == t_field_name:
                    new_datas.append(event.data)
                else:
                    new_datas.append(getattr(attr, field_name))
            tuple_class: Type[tuple] = attr.__class__
            new_tuple = tuple_class(*new_datas)
            setattr(element, attr_name, new_tuple)
        else:
            setattr(element, cfg_path, event.data)
        event = ProjectUpdatedEvent()
        wx.PostEvent(widget.entry, event)

    widget.entry.Unbind(EVT_DATA_UPDATE)
    widget.entry.Bind(EVT_DATA_UPDATE, warp)


class ElementInfoEditor(ElementInfoEditorUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.active_element: CursorElement | None = None

    def set_element(self, element: CursorElement):

        def on_choice(event: wx.CommandEvent):
            event.Skip()
            element.resample = list(self.resample_map.keys())[self.resample_type.GetSelection()]
            event = ProjectUpdatedEvent()
            wx.PostEvent(self.resample_type, event)

        create_cfg_bind(self.name, element, "name")
        create_cfg_bind(self.pos_x, element, "position.x")
        create_cfg_bind(self.pos_y, element, "position.y")
        create_cfg_bind(self.rotation, element, "rotation")
        create_cfg_bind(self.scale_x, element, "scale.x")
        create_cfg_bind(self.scale_y, element, "scale.y")
        create_cfg_bind(self.crop_up, element, "crop_margins.up")
        create_cfg_bind(self.crop_down, element, "crop_margins.down")
        create_cfg_bind(self.crop_left, element, "crop_margins.left")
        create_cfg_bind(self.crop_right, element, "crop_margins.right")
        create_cfg_bind(self.reverse_x, element, "reverse_x")
        create_cfg_bind(self.reverse_y, element, "reverse_y")
        if len(element.frames) > 1:
            create_cfg_bind(self.animation_start, element, "animation_start")
            create_cfg_bind(self.animation_length, element, "animation_length")
        else:
            self.animation_start.entry.Unbind(EVT_DATA_UPDATE)
            self.animation_length.entry.Unbind(EVT_DATA_UPDATE)
        self.resample_type.Unbind(wx.EVT_CHOICE)
        self.resample_type.Bind(wx.EVT_CHOICE, on_choice)

        self.name.set_value(element.name)
        self.pos_x.set_value(element.position.x)
        self.pos_y.set_value(element.position.y)
        self.rotation.set_value(element.rotation)
        self.scale_x.set_value(element.scale.x)
        self.scale_y.set_value(element.scale.y)
        self.crop_up.set_value(element.crop_margins.up)
        self.crop_down.set_value(element.crop_margins.down)
        self.crop_left.set_value(element.crop_margins.left)
        self.crop_right.set_value(element.crop_margins.right)
        self.reverse_x.set_value(element.reverse_x)
        self.reverse_y.set_value(element.reverse_y)
        if len(element.frames) > 1:
            self.animation_start.set_value(element.animation_start)
            self.animation_length.set_value(element.animation_length)
            self.animation_panel.Enable()
        else:
            self.animation_panel.Disable()
            self.animation_panel.Collapse()
        self.resample_type.SetSelection(list(self.resample_map.values()).index(self.resample_map[element.resample]))
        self.active_element = element
        self.Layout()


class ProjectInfoEditor(ProjectInfoEditorUI):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)
        create_cfg_bind(self.name, project, "name")
        create_cfg_bind(self.center_x, project, "center_pos.x")
        create_cfg_bind(self.center_y, project, "center_pos.y")
        create_cfg_bind(self.scale, project, "scale")
        if project.frame_count != -1:
            create_cfg_bind(self.frame_count, project, "frame_count")
            create_cfg_bind(self.ani_rate, project, "ani_rate")
        self.resample_type.Unbind(wx.EVT_CHOICE)

        def on_choice(event: wx.CommandEvent):
            event.Skip()
            project.resample = list(self.resample_map.keys())[self.resample_type.GetSelection()]
            event = ProjectUpdatedEvent()
            wx.PostEvent(self.resample_type, event)

        self.resample_type.Bind(wx.EVT_CHOICE, on_choice)
