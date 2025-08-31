from time import perf_counter

import wx
from PIL import Image

from lib.data import CursorProject, CursorElement, Position, Scale2D
from lib.log import logger
from lib.perf import Counter
from lib.resources import theme_manager
from ui.cursor_editor import CursorEditorUI
from widget.win_icon import set_multi_size_icon
from ui_ctl.cursor_editor_widgets.element_canvas import ElementCanvas
from ui_ctl.cursor_editor_widgets.element_list_ctrl import ElementListCtrl
from ui_ctl.cursor_editor_widgets.events import EVT_PROJECT_UPDATED, EVT_ELEMENT_SELECTED, EVT_SCALE_UPDATED, \
    ElementSelectedEvent, ScaleUpdatedEvent, EVT_FRAME_COUNTER_CHANGE, EVT_ANIMATION_MODE_CHANGE, ProjectUpdatedEvent
from ui_ctl.cursor_editor_widgets.info_editor import InfoEditor


class CursorEditor(CursorEditorUI):
    elements_lc: 'ElementListCtrl'
    canvas: 'ElementCanvas'
    info_editor: 'InfoEditor'
    is_sub_project: bool = False

    def __init__(self, parent: wx.Window | None, project: CursorProject):
        timer = Counter(create_start=True)
        super().__init__(parent, project)
        set_multi_size_icon(self, "assets\icons\project\edit.png")
        self.project = project
        self.b_canvas_size = self.project.raw_canvas_size
        self.b_output_size = self.project.canvas_size
        self.b_scale = self.canvas.scale

        self.canvas.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.canvas.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
        self.canvas.Bind(EVT_FRAME_COUNTER_CHANGE, self.on_frame_counter_change)
        self.Bind(EVT_ANIMATION_MODE_CHANGE, self.on_animation_mode_change)
        self.Bind(EVT_ELEMENT_SELECTED, self.on_element_selected)
        self.Bind(EVT_PROJECT_UPDATED, self.on_project_updated)
        self.Bind(EVT_SCALE_UPDATED, self.on_scale_updated)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        logger.info(f"项目编辑器初始化用时: {timer.endT()}, 项目: {project}")

        self.last_edit = perf_counter()

    def on_close(self, event: wx.CloseEvent):
        if not self.is_sub_project:
            theme_manager.save()
        event.Skip()

    def on_frame_counter_change(self, event):
        if self.project.is_ani_cursor:
            self.info_editor.proj_editor.on_frame_counter_change(event)

    def on_animation_mode_change(self, event):
        if self.project.is_ani_cursor:
            self.canvas.on_animation_mode_change(event)

    def on_mouse_move(self, event: wx.MouseEvent):
        event.Skip()
        self.b_cursor_pos = self.canvas.translate_mouse_position(event.GetPosition().IM)

    def on_mouse_leave(self, event: wx.MouseEvent):
        event.Skip()
        self.b_cursor_pos = None

    def on_element_selected(self, event: ElementSelectedEvent):
        logger.info(f"元素被选择 -> {event.element}")
        self.info_editor.set_element(event.element)
        self.canvas.set_element(event.element)
        if event.GetEventObject() is not self.elements_lc:
            self.elements_lc.set_element(event.element)
        if event.element:
            self.b_rect_size = event.element.final_rect[2:]
        else:
            self.b_rect_size = None

    def on_project_updated(self, event: ProjectUpdatedEvent):
        if perf_counter() - self.last_edit < 60:
            self.project.make_time += perf_counter() - self.last_edit
        self.last_edit = perf_counter()

        event.Skip()
        logger.debug("项目数据已更新")
        self.elements_lc.project_updated()
        self.canvas.project_updated()
        if self.canvas.active_element is None:
            self.info_editor.set_element(None)
        self.SetTitle(f"光标项目编辑器 - {self.project.name if self.project.name else self.project.kind.kind_name}")
        self.b_output_size = self.project.canvas_size

    def on_scale_updated(self, event: ScaleUpdatedEvent):
        self.b_scale = event.scale


def test_editor():
    t_project = CursorProject("Sword Loading", (32, 32))
    t_project.scale = 2.0
    t_project.is_ani_cursor = True
    t_project.frame_count = 64
    t_project.ani_rate = 50
    t_project.add_element(
        CursorElement("Diamond Sword", [Image.open("diamond_sword.png").convert("RGBA")], scale=Scale2D(2.0, 2.0),
                      reverse_x=True))

    element = CursorElement("Clock", [])
    element.position = Position(17, 0)
    for f_index in range(64):
        fp = rf"assets_test\clock_{str(f_index).zfill(2)}.png"
        element.frames.append(Image.open(fp).convert("RGBA"))
    element.animation_key_data.frame_length = 64
    element.update_ani_data_by_key_data()
    t_project.add_element(element)

    app = wx.App()
    frame = CursorEditor(None, t_project)
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    test_editor()
