import wx

from lib.data import CursorElement, ProcessStep

STEP_NAME_MAP = {
    ProcessStep.CROP: "裁剪",
    ProcessStep.ROTATE: "旋转",
    ProcessStep.SCALE: "缩放",
    ProcessStep.TRANSPOSE: "翻转"
}


class StepEditor(wx.Dialog):
    def __init__(self, parent: wx.Window, element: CursorElement):
        super().__init__(parent, title="步骤编辑")
        self.SetFont(parent.GetFont())
        self.element = element
        self.element.proc_step = list(element.proc_step)

        self.list = wx.ListBox(self)
        for step in element.proc_step:
            self.list.Append(STEP_NAME_MAP[step])

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key)

    def exchange_item(self, index1: int, index2: int):
        self.element.proc_step[index1], self.element.proc_step[index2] = self.element.proc_step[index2], \
        self.element.proc_step[index1]
        self.list.SetString(index1, STEP_NAME_MAP[self.element.proc_step[index1]])
        self.list.SetString(index2, STEP_NAME_MAP[self.element.proc_step[index2]])

    def on_key(self, event: wx.KeyEvent):
        item_selected = self.list.GetSelection() if self.list.GetSelection() != wx.NOT_FOUND else None
        if event.GetKeyCode() == wx.WXK_UP and item_selected is not None and item_selected > 0:
            self.exchange_item(item_selected, item_selected - 1)
            self.list.Select(item_selected - 1)
        elif event.GetKeyCode() == wx.WXK_DOWN and item_selected is not None and item_selected < self.list.GetCount() - 1:
            self.exchange_item(item_selected, item_selected + 1)
            self.list.Select(item_selected + 1)
        else:
            event.Skip()
