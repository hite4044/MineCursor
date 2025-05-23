from typing import Callable

import wx

from lib.data import CursorProject, CursorElement
from lib.log import logger
from ui.cursor_editor import InfoEditorUI, ElementInfoEditorUI, ProjectInfoEditorUI
from widget.data_entry import DataEntryEvent, DataEntry, EVT_DATA_UPDATE, BoolEntry
from ui_ctl.cursor_editor_widgets.events import ProjectUpdatedEvent


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


def create_cfg_bind(widget: DataEntry,
                    obj,
                    cfg_path: str,
                    cbk: Callable[[DataEntryEvent], None] = lambda _: None,
                    checking_widget: BoolEntry = None,
                    checking_none: bool = False):
    def warp(event: DataEntryEvent):
        if checking_widget is not None and checking_widget.entry.GetValue() == False:
            ret = wx.MessageBox("是否启用关键字动画编辑?\n会导致先前绘制的帧动画丢失", "警告",
                                wx.ICON_WARNING | wx.YES_NO)
            if ret == wx.YES:
                checking_widget.set_value(True)
                obj.enable_key_ani = True
                warp(event)
            return
        if cfg_path.count(".") == 1:
            attr_name, attr_name2 = cfg_path.split('.')
            next_attr = getattr(obj, attr_name)
            setattr(next_attr, attr_name2, event.data)
            setattr(obj, attr_name, next_attr)
        else:
            if checking_none and event.data == "None":
                setattr(obj, cfg_path, None)
            else:
                setattr(obj, cfg_path, event.data)
        cbk(event)
        logger.info(f"更新对象 {obj} 的 {cfg_path} 属性")
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
            print("choice")
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
        create_cfg_bind(self.enable_key_ani, element, "enable_key_ani")
        if len(element.frames) > 1:
            def update_ani_data(_):
                element.update_ani_data_by_key_data()

            create_cfg_bind(self.frame_start, element, "animation_key_data.frame_start",
                            update_ani_data, self.enable_key_ani)
            create_cfg_bind(self.frame_inv, element, "animation_key_data.frame_inv",
                            update_ani_data, self.enable_key_ani)
            create_cfg_bind(self.frame_length, element, "animation_key_data.frame_length",
                            update_ani_data, self.enable_key_ani)
        else:
            self.frame_start.entry.Unbind(EVT_DATA_UPDATE)
            self.frame_inv.entry.Unbind(EVT_DATA_UPDATE)
            self.frame_length.entry.Unbind(EVT_DATA_UPDATE)
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
        self.enable_key_ani.set_value(element.enable_key_ani)
        if len(element.frames) > 1:
            self.frame_start.set_value(element.animation_key_data.frame_start)
            self.frame_inv.set_value(element.animation_key_data.frame_inv)
            self.frame_length.set_value(element.animation_key_data.frame_length)
            self.animation_frames_count.set_value(str(len(element.frames)))
            self.animation_panel.Show()
        else:
            self.animation_panel.Hide()
        self.resample_type.SetSelection(list(self.resample_map.values()).index(self.resample_map[element.resample]))
        self.active_element = element
        self.Layout()

    def update_animation_key_data(self):
        if self.active_element is None:
            return


class ProjectInfoEditor(ProjectInfoEditorUI):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)
        create_cfg_bind(self.name, project, "name")
        create_cfg_bind(self.external_name, project, "external_name", checking_none=True)
        create_cfg_bind(self.kind, project, "kind")
        create_cfg_bind(self.center_x, project, "center_pos.x")
        create_cfg_bind(self.center_y, project, "center_pos.y")
        create_cfg_bind(self.scale, project, "scale")
        create_cfg_bind(self.is_ani_cursor, project, "is_ani_cursor")
        create_cfg_bind(self.frame_count, project, "frame_count")
        create_cfg_bind(self.ani_rate, project, "ani_rate")
        self.is_ani_cursor.entry.Bind(EVT_DATA_UPDATE, self.on_is_ani_cursor_switch)

        def on_choice(event: wx.CommandEvent):
            event.Skip()
            project.resample = list(self.resample_map.keys())[self.resample_type.GetSelection()]
            event = ProjectUpdatedEvent()
            wx.PostEvent(self.resample_type, event)

        self.resample_type.Bind(wx.EVT_CHOICE, on_choice)

    def on_is_ani_cursor_switch(self, event: DataEntryEvent):
        event.Skip()

        if event.data:
            self.ani_rate.enable()
            self.frame_count.enable()
        else:
            self.ani_rate.disable()
            self.frame_count.disable()
