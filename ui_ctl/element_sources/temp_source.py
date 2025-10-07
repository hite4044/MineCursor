import wx
from PIL.Image import Resampling

from lib.data import ThemeType, CursorProject
from lib.dpi import BL_SIZE
from lib.image_pil2wx import PilImg2WxImg
from lib.render import render_project_frame
from lib.resources import theme_manager


class TemplateSource(wx.ListCtrl):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, style=wx.LC_ICON | wx.NO_BORDER)
        self.index2project_map: dict[int, CursorProject] = {}
        self.image_list = wx.ImageList(BL_SIZE, BL_SIZE)
        self.AssignImageList(self.image_list, wx.IMAGE_LIST_NORMAL)

        # 填充数据
        for theme in theme_manager.themes:
            if theme.type != ThemeType.TEMPLATE:  # 筛除不是模板的主题
                continue
            for project in theme.projects:
                project_frame = render_project_frame(project, 0)\
                    .resize((BL_SIZE, BL_SIZE), Resampling.BOX)
                preview_index = self.image_list.Add(PilImg2WxImg(project_frame).ConvertToBitmap())
                index = self.InsertItem(self.GetItemCount(),
                                        project.name if project.name else project.kind.kind_name,
                                        preview_index)
                self.index2project_map[index] = project

    def get_project(self):
        if self.GetFirstSelected() == -1:
            return None

        index = self.GetFirstSelected()
        return self.index2project_map[index].copy()
