from typing import Callable, cast as type_cast

import wx
from PIL import Image

from lib.cursor.writer import write_cur, write_ani
from lib.data import CursorProject, CursorElement
from lib.image_pil2wx import PilImg2WxImg
from lib.render import render_project_gen
from ui.cursor_editor import ElementListCtrlUI
from ui_ctl.cursor_editor_widgets.events import ProjectUpdatedEvent, ElementSelectedEvent
from ui_ctl.cursor_editor_widgets.mask_editor import MaskEditor
from ui_ctl.cursor_editor_widgets.source_info_edit_dialog import SourceInfoEditDialog
from ui_ctl.element_add_dialog import ElementAddDialog
from widget.ect_menu import EtcMenu


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
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_menu)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down, self)
        for element in project.elements:
            self.add_element(element)

    def on_key_down(self, event: wx.KeyEvent):
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.remove_elements(self.get_select_elements())
        elif event.GetKeyCode() == ord("Z") and event.GetModifiers() == wx.MOD_CONTROL:
            if len(self.elements_has_deleted) == 0:
                return
            stacks = self.elements_has_deleted.pop(-1)
            for index, project in stacks[::-1]:
                self.project.elements.insert(index, project)
            self.rebuild_control()
            self.send_project_updated()
        else:
            event.Skip()

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

    def on_item_menu(self, event: wx.ListEvent):
        index = event.GetIndex()
        elements = self.get_select_elements()
        menu = EtcMenu()

        menu.Append("添加", self.on_add_element)
        if len(elements) == 1:
            menu.AppendSeparator()
            menu.Append("复制", self.copy_element, index)
            menu.Append("上移一层", self.move_element, index, -1)
            menu.Append("下移一层", self.move_element, index, 1)
            menu.Append("编辑遮罩", self.on_edit_mask, index)
            menu.Append("编辑源信息", self.on_edit_source, index)
        menu.AppendSeparator()
        menu.Append("删除" + mk_end(elements), self.remove_elements, elements)

        self.PopupMenu(menu)

    def copy_element(self, index: int):
        element = self.get_element_by_index(index)
        self.project.add_element(element.copy())
        self.rebuild_control()
        self.send_project_updated()

    def on_menu(self, event: wx.MouseEvent):
        if type_cast(tuple[int, int], self.HitTest(event.GetPosition()))[0] != -1:
            event.Skip()
            return
        menu = wx.Menu()

        def ect_binder(name: str, func: Callable, *args):
            item = menu.Append(wx.ID_ANY, name)
            menu.Bind(wx.EVT_MENU, lambda _: func(*args), id=item.GetId())

        ect_binder("添加", self.on_add_element)
        menu.AppendSeparator()
        ect_binder("清空", self.on_remove_all_elements)
        menu.AppendSeparator()
        ect_binder("导出", self.output_file)
        self.PopupMenu(menu)

    def on_add_element(self):
        dialog = ElementAddDialog(self)
        if dialog.ShowModal() != wx.ID_OK:
            return
        if not dialog.element:
            return
        self.project.add_element(dialog.element)
        self.rebuild_control()
        self.send_project_updated()

    def on_edit_source(self, index: int):
        element = self.get_element_by_index(index)
        dialog = SourceInfoEditDialog(self, element)
        dialog.ShowModal()
        self.rebuild_control()
        self.send_project_updated()

    def on_edit_mask(self, index: int):
        element = self.get_element_by_index(index)
        background = element.final_image
        if element.mask:
            mask = element.mask.resize(background.size, Image.Resampling.NEAREST)
        else:
            mask = background.getchannel("A")
        dialog = MaskEditor(self, mask, background)
        if dialog.ShowModal() == wx.ID_OK:
            element.mask = dialog.get_mask()
            self.rebuild_control()
            self.send_project_updated()

    def output_file(self):
        wildcard = "动态光标 (*.ani)|*.ani" if self.project.is_ani_cursor else "静态光标 (*.cur)|*.cur"
        end_fix = ".ani" if self.project.is_ani_cursor else ".cur"
        dialog = wx.FileDialog(self, "选择保存路径", defaultFile=self.project.name + end_fix, wildcard=wildcard,
                               style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dialog.ShowModal() != wx.ID_OK:
            return

        path = dialog.GetPath()

        def get_text(action: str, use_num: bool = True):
            if use_num:
                return action + " ({}/" + str(self.project.frame_count) + ")..."
            return action + "..."

        render_text = get_text("渲染中")
        progress_dialog = wx.ProgressDialog("导出进度", render_text.format(0))
        frames = []
        generator = render_project_gen(self.project)
        progress_dialog.SetRange(self.project.frame_count)
        for i, frame in enumerate(generator):
            progress_dialog.Update(i, render_text.format(i))
            frames.append(frame)

        if not self.project.is_ani_cursor:
            progress_dialog.SetRange(1)
            progress_dialog.Update(0, "写入cur文件...")
            write_cur(frames[0], self.project.center_pos, path)
            progress_dialog.Update(1)
        else:
            gen = write_ani(path, frames, self.project)
            while True:
                try:
                    msg, index = next(gen)
                except StopIteration:
                    break
                if index != -1:
                    new_msg = f"{msg} ({index}/{self.project.frame_count})..."
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
