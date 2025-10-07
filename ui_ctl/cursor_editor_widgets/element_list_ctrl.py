from typing import cast as type_cast

import wx
from PIL import Image

from lib.clipboard import PUBLIC_ELEMENT_CLIPBOARD
from lib.cursor.writer import write_cur, write_ani
from lib.data import CursorProject, CursorElement
from lib.image_pil2wx import PilImg2WxImg
from lib.render import render_project_gen
from ui.cursor_editor import ElementListCtrlUI
from ui.select import select_all
from ui_ctl.cursor_editor_widgets.events import ProjectUpdatedEvent, ElementSelectedEvent
from ui_ctl.cursor_editor_widgets.mask_editor import MaskEditor
from ui_ctl.cursor_editor_widgets.source_info_editor import SourceInfoEditDialog
from ui_ctl.element_add_dialog import ElementAddDialog
from widget.data_dialog import DataDialog, DataLineParam, DataLineType
from widget.ect_menu import EtcMenu


class ProjectSizeDialog(DataDialog):
    def __init__(self, parent: wx.Window, size: int | tuple[int, int]):
        super().__init__(parent, "修改项目尺寸",
                         DataLineParam("width", "画布宽", DataLineType.INT, size[0]),
                         DataLineParam("height", "画布高", DataLineType.INT, size[1]))

    def get_size(self):
        return self.datas["width"], self.datas["height"]


def mk_end(li: list):
    if len(li) > 1:
        return f" ({len(li)})"
    return ""


class ElementListCtrl(ElementListCtrlUI):
    def __init__(self, parent: wx.Window, project: CursorProject):
        super().__init__(parent, project)

        self.line_mapping = {}
        self.elements_has_deleted: list[list[tuple[int, CursorElement]]] = []
        self.set_processing = False
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select, self)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_menu, self)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_active, self)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu, self)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down, self)
        for element in project.elements:
            self.add_element(element)

        self.clip = PUBLIC_ELEMENT_CLIPBOARD(self, self.clip_on_get_data, self.clip_on_set_data)

    def clip_on_get_data(self):
        item = self.GetFirstSelected()
        return None if item == -1 else [element.to_dict() for element in self.get_select_elements()]

    def clip_on_set_data(self, element_datas: list[dict]):
        for element_data in element_datas:
            element = CursorElement.from_dict(element_data)
            self.project.elements.append(element.copy())
        self.rebuild_control()
        self.send_project_updated()

    def on_key_down(self, event: wx.KeyEvent):
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.remove_elements(self.get_select_elements())
        elif event.GetKeyCode() == ord("Z") and event.GetModifiers() == wx.MOD_CONTROL:
            self.undo()
        elif event.GetKeyCode() == ord("A") and event.GetModifiers() == wx.MOD_CONTROL:
            select_all(self)
        elif event.GetKeyCode() == wx.WXK_UP and event.GetModifiers() == wx.MOD_SHIFT:
            index = self.GetFirstSelected()
            self.move_element(index, -1)
        elif event.GetKeyCode() == wx.WXK_DOWN and event.GetModifiers() == wx.MOD_SHIFT:
            index = self.GetFirstSelected()
            self.move_element(index, 1)
        else:
            event.Skip()

    def undo(self):
        if len(self.elements_has_deleted) == 0:
            return
        stacks = self.elements_has_deleted.pop(-1)
        for index, project in stacks[::-1]:
            self.project.elements.insert(index, project)
        self.rebuild_control()
        self.send_project_updated()

    def project_updated(self):
        for i, element in enumerate(self.project.elements):
            if element.name != self.GetItemText(i, 1):
                self.SetItem(i, 1, element.name)

    def get_select_elements(self) -> list[CursorElement]:
        first = self.GetFirstSelected()
        selections = []
        while first != -1:
            selections.append(self.get_element_by_index(first))
            first = self.GetNextSelected(first)
        return selections

    def on_item_active(self, event: wx.ListEvent):
        element = self.get_element_by_index(event.GetIndex())
        if element.sub_project:
            from ui_ctl.cursor_editor import CursorEditor
            element.sub_project.name = element.name
            editor = CursorEditor(self, element.sub_project)
            editor.is_sub_project = True
            editor.Show()

    def on_item_menu(self, event: wx.ListEvent):
        index = event.GetIndex()
        elements = self.get_select_elements()
        menu = EtcMenu()

        menu.Append("添加 (&A)", self.on_add_element, icon="element/add.png")
        if len(elements) == 1:
            menu.AppendSeparator()
            menu.Append("编辑遮罩 (&M)", self.on_edit_mask, index, icon="element/edit_mask.png")
            if not elements[0].sub_project:
                menu.Append("编辑源信息 (&I)", self.on_edit_source, index, icon="element/edit_info.png")
            menu.AppendSeparator()
            menu.Append("上移一层 (&W)", self.move_element, index, -1, icon="action/up.png")
            menu.Append("下移一层 (&S)", self.move_element, index, 1, icon="action/down.png")
        menu.AppendSeparator()
        if len(elements) > 1:
            menu.Append("创建子项目 (&G)", self.create_sub_project, elements, icon="element/package.png")
        elif elements[0].sub_project:
            menu.Append("编辑子项目信息 (&P)", self.edit_sub_project_info,
                        elements[0].sub_project, icon="project/edit_info.png")
            menu.Append("解散子项目 (&G)", self.extract_sub_project, elements[0], icon="element/unpackage.png")
        menu.Append("复制 (&C)" + mk_end(elements), self.copy_elements, elements, icon="element/copy.png")
        if len(self.elements_has_deleted) == -1:
            menu.Append("撤销 (&Z)", self.undo, icon="action/undo.png")
        menu.AppendSeparator()
        menu.Append("删除 (&D)" + mk_end(elements), self.remove_elements, elements, icon="action/delete.png")

        self.PopupMenu(menu)

    def edit_sub_project_info(self, sub_project: CursorProject):
        dialog = ProjectSizeDialog(self, sub_project.raw_canvas_size)
        if dialog.ShowModal() == wx.ID_OK:
            sub_project.raw_canvas_size = dialog.get_size()
            self.send_project_updated()

    def create_sub_project(self, elements: list[CursorElement]):
        # 创建新元素并添加
        new_element = CursorElement("新子项目", [])
        new_element.create_sub_project(size=self.project.raw_canvas_size, elements=elements)
        self.project.elements.append(new_element)

        # 删除旧元素
        for element in elements:
            self.project.elements.remove(element)

        self.rebuild_control()
        self.send_project_updated()

    def extract_sub_project(self, org_element: CursorElement):
        frame_offset_delta = org_element.animation_start_offset
        org_index = self.project.elements.index(org_element)
        for element in org_element.sub_project.elements[::-1]:
            element.animation_start_offset += frame_offset_delta
            self.project.elements.insert(org_index, element)
        self.project.elements.remove(org_element)

        self.rebuild_control()
        self.send_project_updated()

    def copy_elements(self, elements: list[CursorElement]):
        for element in elements[::-1]:
            self.project.elements.append(element.copy())
        self.rebuild_control()
        self.send_project_updated()

    def on_menu(self, event: wx.MouseEvent):
        if type_cast(tuple[int, int], self.HitTest(event.GetPosition()))[0] != -1:
            event.Skip()
            return
        menu = EtcMenu()

        menu.Append("添加 (&A)", self.on_add_element, icon="element/add.png")
        menu.AppendSeparator()
        menu.Append("清空 (&D)", self.on_remove_all_elements, icon="action/delete.png")
        menu.AppendSeparator()
        menu.Append("导出 (&O)", self.output_file, self.project, icon="project/export.png")

        self.PopupMenu(menu)

    def on_add_element(self):
        dialog = ElementAddDialog(self, self.project.kind)
        if dialog.ShowModal() != wx.ID_OK:
            return
        if not dialog.element:
            return
        self.project.make_time += dialog.work_timer
        self.project.add_element(dialog.element)
        self.rebuild_control()
        self.send_project_updated()

    def on_edit_source(self, index: int):
        element = self.get_element_by_index(index)
        dialog = SourceInfoEditDialog(self, element, self.project.kind)
        dialog.ShowModal()
        self.rebuild_control()
        self.send_project_updated()

    def on_edit_mask(self, index: int):
        element = self.get_element_by_index(index)
        background = element.final_image
        if element.mask:
            if element.allow_mask_scale:
                background = background.resize(element.mask.size, element.scale_resample)
                mask = element.mask.copy()
            else:
                mask = element.mask.resize(background.size, element.scale_resample)
        else:
            mask = background.getchannel("A")
        dialog = MaskEditor(self, mask, background)
        if dialog.ShowModal() == wx.ID_OK:
            element.mask = dialog.get_mask()
            self.rebuild_control()
            self.send_project_updated()

    @staticmethod
    def output_file(project: CursorProject):
        wildcard = "动态光标 (*.ani)|*.ani" if project.is_ani_cursor else "静态光标 (*.cur)|*.cur"
        end_fix = ".ani" if project.is_ani_cursor else ".cur"
        default_name = project.name if project.name else (project.external_name if project.external_name else project.kind.kind_name)
        dialog = wx.FileDialog(wx.GetActiveWindow(), "选择保存路径", defaultFile=default_name + end_fix,
                               wildcard=wildcard,
                               style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dialog.ShowModal() != wx.ID_OK:
            return

        path = dialog.GetPath()

        def get_text(action: str, use_num: bool = True):
            if use_num:
                return action + " ({}/" + str(project.frame_count) + ")..."
            return action + "..."

        render_text = get_text("渲染中")
        progress_dialog = wx.ProgressDialog("导出进度", render_text.format(0))
        frames = []
        generator = render_project_gen(project, for_export=True)
        progress_dialog.SetRange(project.frame_count)
        for i, frame in enumerate(generator):
            progress_dialog.Update(i, render_text.format(i))
            frames.append(frame)

        if not project.is_ani_cursor:
            progress_dialog.SetRange(1)
            progress_dialog.Update(0, "写入cur文件...")
            write_cur(frames[0], project.center_pos, path)
            progress_dialog.Update(1)
        else:
            gen = write_ani(path, frames, project)
            while True:
                try:
                    msg, index = next(gen)
                except StopIteration:
                    break
                if index != -1:
                    new_msg = f"{msg} ({index}/{project.frame_count})..."
                else:
                    new_msg = f"{msg}..."
                    progress_dialog.SetRange(1)
                progress_dialog.Update(index, new_msg)
        dialog.Destroy()
        wx.MessageBox("保存成功")

    def on_remove_all_elements(self):
        if wx.MessageBox("确定要清空所有元素吗？", "提示", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            self.elements_has_deleted.append([(i, element) for i, element in enumerate(self.project.elements)])
            self.project.elements.clear()
            self.rebuild_control()
            self.send_project_updated()

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
        element_id = self.line_mapping[index]
        for element in self.project.elements:
            if element.id == element_id:
                break
        else:
            wx.MessageBox("无法找到对应元素")
            return None
        return element

    def remove_elements(self, elements: list[CursorElement]):
        indexes: list[int] = [{v: k for k, v in self.line_mapping.items()}[element.id] for element in elements]
        self.elements_has_deleted.append([(line, element) for line, element in zip(indexes[::-1], elements[::-1])])
        for element in elements:
            self.project.elements.remove(element)
        self.rebuild_control()
        self.send_project_updated()

    def move_element(self, line: int, delta: int):
        if not 0 <= line + delta < len(self.project.elements):
            return
        old_element = self.project.elements[line + delta]
        self.project.elements[line + delta] = self.project.elements[line]
        self.project.elements[line] = old_element
        self.rebuild_control()
        self.Select(line + delta)
        self.send_project_updated()

    def add_element(self, element: CursorElement):
        index = self.image_list.Add(PilImg2WxImg(element.frames[0].resize((16, 16))).ConvertToBitmap())
        line = self.GetItemCount()
        self.InsertItem(line, index)
        self.SetItem(line, 1, element.name)
        self.line_mapping[line] = element.id

    def set_element(self, element: CursorElement | None):
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
        event.Skip()
        if self.set_processing:
            return
        select_id = self.line_mapping[event.GetIndex()]
        for element in self.project.elements:
            if element.id == select_id:
                break
        else:
            return

        event = ElementSelectedEvent(element)
        event.SetEventObject(self)
        wx.PostEvent(self, event)
