from typing import Callable

import wx

from lib.data import CursorProject, CursorElement
from lib.log import logger
from ui.cursor_editor import InfoEditorUI, ElementInfoEditorUI, ProjectInfoEditorUI
from ui_ctl.cursor_editor_widgets.rate_editor import RateEditor
from ui_ctl.cursor_editor_widgets.step_editor import StepEditor
from widget.data_entry import DataEntryEvent, DataEntry, EVT_DATA_UPDATE, BoolEntry
from ui_ctl.cursor_editor_widgets.events import ProjectUpdatedEvent, FrameCounterChangeEvent, AnimationModeChangeEvent, \
    AnimationMode


class InfoEditor(InfoEditorUI):
    element_editor: 'ElementInfoEditor'
    proj_editor: 'ProjectInfoEditor'

    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)

    def set_element(self, element: CursorElement | None):
        if element is None:
            self.switch_page(0)
        else:
            self.switch_page(1)
            self.element_editor.set_element(element)


def create_cfg_bind(widget: DataEntry,
                    obj,
                    cfg_path: str,
                    cbk: Callable[[DataEntryEvent], None] = lambda _: None,
                    enable_keyframe_anim_widget: bool = False,
                    process_none_string: bool = False):
    def warp(event: DataEntryEvent):
        if enable_keyframe_anim_widget and widget.entry.GetValue() == True:
            ret = wx.MessageBox("是否启用关键字动画编辑?\n会导致先前绘制的帧动画丢失", "警告",
                                wx.ICON_WARNING | wx.YES_NO)
            enable = ret == wx.YES
            obj.enable_key_ani = enable
            widget.set_value(False)
            widget.entry.ProcessEvent(DataEntryEvent(enable))
            widget.set_value(enable)
            return
        event.Skip()
        if cfg_path.count(".") == 1:
            attr_name, attr_name2 = cfg_path.split('.')
            next_attr = getattr(obj, attr_name)
            setattr(next_attr, attr_name2, event.data)
            setattr(obj, attr_name, next_attr)
        else:
            if process_none_string and event.data == "":
                setattr(obj, cfg_path, None)
            else:
                setattr(obj, cfg_path, event.data)
        cbk(event)
        logger.debug(f"更新对象 {obj} 的 {cfg_path} 属性")
        event = ProjectUpdatedEvent()
        wx.PostEvent(widget.entry, event)

    widget.entry.Unbind(EVT_DATA_UPDATE)
    widget.entry.Bind(EVT_DATA_UPDATE, warp)


class ElementInfoEditor(ElementInfoEditorUI):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.active_element: CursorElement | None = None
        self.open_step_editor_btn.Bind(wx.EVT_BUTTON, self.open_step_editor)

        self.mask_color.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_pick_mask_color)
        self.mask_color_reset_btn.Bind(wx.EVT_BUTTON, self.on_reset_mask_color)

    def send_update(self):
        event = ProjectUpdatedEvent()
        wx.PostEvent(self, event)

    def open_step_editor(self, _):
        if self.active_element:
            StepEditor(self, self.active_element).Show()

    def on_pick_mask_color(self, event: wx.ColourPickerEvent):
        event.Skip()
        if self.active_element:
            clr = event.GetColour()
            self.active_element.mask_color = clr.GetRed(), clr.GetGreen(), clr.GetBlue()
            self.send_update()

    def on_reset_mask_color(self, _):
        if self.active_element:
            self.active_element.mask_color = None
            self.set_element(self.active_element)
            self.send_update()

    def set_element(self, element: CursorElement):
        create_cfg_bind(self.name, element, "name")
        create_cfg_bind(self.pos_x, element, "position.x")
        create_cfg_bind(self.pos_y, element, "position.y")
        create_cfg_bind(self.rotation, element, "rotation")
        create_cfg_bind(self.scale_x, element, "scale.x")
        create_cfg_bind(self.scale_y, element, "scale.y")
        create_cfg_bind(self.rotate_resample, element, "resample")
        create_cfg_bind(self.scale_resample, element, "scale_resample")
        create_cfg_bind(self.crop_up, element, "crop_margins.up")
        create_cfg_bind(self.crop_down, element, "crop_margins.down")
        create_cfg_bind(self.crop_left, element, "crop_margins.left")
        create_cfg_bind(self.crop_right, element, "crop_margins.right")
        create_cfg_bind(self.reverse_x, element, "reverse_x")
        create_cfg_bind(self.reverse_y, element, "reverse_y")
        create_cfg_bind(self.reverse_way, element, "reverse_way")

        create_cfg_bind(self.animation_start_offset, element, "animation_start_offset")
        create_cfg_bind(self.loop_animation, element, "loop_animation")
        create_cfg_bind(self.reverse_animation, element, "reverse_animation")
        create_cfg_bind(self.enable_key_ani, element, "enable_key_ani", enable_keyframe_anim_widget=True)
        if len(element.frames) > 1 or True:
            def update_ani_data(event: DataEntryEvent):
                event.Skip()
                element.update_ani_data_by_key_data()
            create_cfg_bind(self.frame_start, element, "animation_key_data.frame_start", cbk=update_ani_data)
            create_cfg_bind(self.frame_inv, element, "animation_key_data.frame_inv", cbk=update_ani_data)
            create_cfg_bind(self.frame_length, element, "animation_key_data.frame_length", cbk=update_ani_data)

            self.frame_start.set_depend(self.enable_key_ani)
            self.frame_inv.set_depend(self.enable_key_ani)
            self.frame_length.set_depend(self.enable_key_ani)
        else:
            self.frame_start.entry.Unbind(EVT_DATA_UPDATE)
            self.frame_inv.entry.Unbind(EVT_DATA_UPDATE)
            self.frame_length.entry.Unbind(EVT_DATA_UPDATE)

        self.name.set_value(element.name)
        self.pos_x.set_value(element.position.x)
        self.pos_y.set_value(element.position.y)
        self.rotation.set_value(element.rotation)
        self.rotate_resample.set_value(element.resample)
        self.scale_x.set_value(element.scale.x)
        self.scale_y.set_value(element.scale.y)
        self.scale_resample.set_value(element.scale_resample)
        self.crop_up.set_value(element.crop_margins.up)
        self.crop_down.set_value(element.crop_margins.down)
        self.crop_left.set_value(element.crop_margins.left)
        self.crop_right.set_value(element.crop_margins.right)
        self.reverse_x.set_value(element.reverse_x)
        self.reverse_y.set_value(element.reverse_y)
        self.reverse_way.set_value(element.reverse_way)
        self.enable_key_ani.set_value(element.enable_key_ani)
        if len(element.frames) > 1 or True:
            self.animation_start_offset.set_value(element.animation_start_offset)
            self.loop_animation.set_value(element.loop_animation)
            self.reverse_animation.set_value(element.reverse_animation)
            self.frame_start.set_value(element.animation_key_data.frame_start)
            self.frame_inv.set_value(element.animation_key_data.frame_inv)
            self.frame_length.set_value(element.animation_key_data.frame_length)
            self.animation_frames_count.set_value(str(len(element.frames)))
            self.animation_panel.Show()
        else:
            self.animation_panel.Hide()

        create_cfg_bind(self.allow_mask_scale, element, "allow_alpha_scale")
        self.allow_mask_scale.set_value(element.allow_mask_scale)
        if element.mask_color is None:
            pick_btn: wx.BitmapButton = self.mask_color.GetPickerCtrl()
            pick_btn.SetBitmap(wx.BitmapBundle(wx.Bitmap("assets/NULL.png")))
        else:
            self.mask_color.SetColour(wx.Colour(*element.mask_color))
        self.active_element = element
        self.Layout()

    def update_animation_key_data(self):
        if self.active_element is None:
            return


class ProjectInfoEditor(ProjectInfoEditorUI):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)
        self.updating_slider = False
        create_cfg_bind(self.name, project, "name", process_none_string=True)
        create_cfg_bind(self.external_name, project, "external_name", process_none_string=True)
        create_cfg_bind(self.kind, project, "kind")
        create_cfg_bind(self.center_x, project, "center_pos.x")
        create_cfg_bind(self.center_y, project, "center_pos.y")
        create_cfg_bind(self.scale, project, "scale")
        create_cfg_bind(self.is_ani_cursor, project, "is_ani_cursor")
        create_cfg_bind(self.frame_count, project, "frame_count")
        create_cfg_bind(self.ani_rate, project, "ani_rate", cbk=self.update_ani_rate_tooltip)
        self.update_ani_rate_tooltip(None)
        self.ani_rate.set_depend(self.is_ani_cursor)
        self.frame_count.set_depend(self.is_ani_cursor)

        def on_choice(event: wx.CommandEvent):
            event.Skip()
            project.resample = list(self.resample_map.keys())[self.resample_type.GetSelection()]
            event = ProjectUpdatedEvent()
            wx.PostEvent(self.resample_type, event)

        self.resample_type.Bind(wx.EVT_CHOICE, on_choice)

        self.frame_count.Bind(EVT_DATA_UPDATE, self.on_frame_count_change)
        self.ani_mode_reset_btn.Bind(wx.EVT_BUTTON, self.on_reset_ani_mode)
        self.frame_counter_slider.SetMax(self.project.frame_count - 1)
        self.frame_counter_slider.Bind(wx.EVT_SLIDER, self.on_slider_slide)

        self.open_rate_editor_btn.Bind(wx.EVT_BUTTON, self.open_rate_editor)

    def on_reset_ani_mode(self, _):
        event = AnimationModeChangeEvent(AnimationMode.NORMAL)
        wx.PostEvent(self, event)

    def on_slider_slide(self, _):
        if self.updating_slider:
            return
        frame_index = self.frame_counter_slider.GetValue()
        event = AnimationModeChangeEvent(AnimationMode.MANUAL, frame_index)
        wx.PostEvent(self, event)
        self.frame_counter_text.SetLabel(str(frame_index))

    def on_frame_counter_change(self, event: FrameCounterChangeEvent):
        self.frame_counter_text.SetLabel(str(event.frame_counter))
        self.updating_slider = True
        self.frame_counter_slider.SetValue(event.frame_counter)
        self.updating_slider = False

    def on_frame_count_change(self, event: DataEntryEvent):
        event.Skip()
        self.frame_counter_slider.SetMax(event.data - 1)

    def open_rate_editor(self, _):
        if not self.project.is_ani_cursor:
            return
        editor = RateEditor(self, self.project)
        editor.Show()

    def update_ani_rate_tooltip(self, event: DataEntryEvent | None):
        if event:
            data = event.data
        else:
            data = self.ani_rate.data
        self.ani_rate.label.SetToolTip("实际帧间隔为 [n * (1/60)] ms\n"
                                       f"实际间隔: {data / 60 * 1000:.2f}ms  "
                                       f"{1 / data * 60:.2f} FPS")
