import json
import os
import re
import zlib
from enum import Enum
from io import BytesIO
from os import rename
from os.path import join, basename, isfile
from typing import Callable, Any

from lib.data import CursorTheme, path_theme_data, CursorElement, \
    AssetSourceInfo, AssetType, path_deleted_theme_data
from lib.log import logger
from lib.render import render_project_frame

HEX_PATTERN = re.compile("^#([A-Fa-f0-9]+)$")


class ThemeAction(Enum):
    ADD = 0
    DELETE = 2


def get_dir_all_themes(dir_path: str):
    _, _, files = next(os.walk(dir_path))
    themes: dict[str, str] = {}
    for file_name in files:
        if not file_name.startswith("MineCursor Theme_"):
            continue
        parts = file_name.split("_")
        theme_id = parts[1]
        if not re.match(HEX_PATTERN, theme_id):
            continue
        file_path = str(join(dir_path, file_name))
        themes[theme_id] = file_path
    return themes


class ThemeManager:
    def __init__(self, dir_path: str):
        self.root_dir = dir_path
        self.themes: list[CursorTheme] = []
        self.theme_file_mapping: dict[CursorTheme, str] = {}
        self.callbacks: dict[ThemeAction, list[Callable[[CursorTheme], None]]] = {}
        self.load()

    def load(self):
        logger.info(f"加载主题... (From: {self.root_dir})")
        _, _, file_names = next(os.walk(self.root_dir))
        for file_name in file_names:
            file_path = str(join(self.root_dir, file_name))
            self.load_theme(file_path)

    def save(self):
        logger.info("正在保存主题")
        self.save_themes(self.themes)

    def save_themes(self, themes: list[CursorTheme]):
        themes_id_mapping = get_dir_all_themes(self.root_dir)
        for theme in themes:
            if theme.id in themes_id_mapping:
                os.remove(themes_id_mapping[theme.id])
            file_path = str(join(self.root_dir, f"MineCursor Theme_{theme.id}_{theme.name}.mctheme"))
            self.theme_file_mapping[theme] = file_path
            self.save_theme_file(file_path, theme)

    def load_theme(self, file_path: str):
        theme = self.load_theme_file(file_path)
        logger.info(f"已加载主题: {theme}")
        self.add_theme(theme)
        self.theme_file_mapping[theme] = file_path

    @staticmethod
    def load_theme_file(file_path: str) -> CursorTheme:
        with open(file_path, "rb") as f:
            data = f.read()
        if data.startswith(b"\x8CMineCursor Theme".zfill(32)):
            data_io = BytesIO(data)
            data_io.read(32)
            header_length = int.from_bytes(data_io.read(8), "big")
            header: dict[str, Any] = json.loads(data_io.read(header_length))

            if header["type"] == "zip_content":
                theme_data = zlib.decompress(data_io.read()).decode("utf-8")
                return CursorTheme.from_dict(json.loads(theme_data))
            else:
                raise RuntimeError("未知的主题类型")
        else:
            return CursorTheme.from_dict(json.loads(data.decode("utf-8")))

    @staticmethod
    def save_theme_file(file_path: str, theme: CursorTheme):
        logger.debug(f"保存主题至: {basename(file_path)}")
        data_string = json.dumps(theme.to_dict(), ensure_ascii=False)
        header = json.dumps({"type": "zip_content"}).encode("utf-8")
        with open(file_path, "wb") as f:
            result = zlib.compress(data_string.encode("utf-8"), 1)
            f.write(b"\x8CMineCursor Theme".zfill(32))
            f.write(len(header).to_bytes(8, "big"))
            f.write(header)
            f.write(result)

    @staticmethod
    def save_rendered_theme_file(file_path: str, theme: CursorTheme):
        new_theme = theme.copy()
        for i, project in enumerate(new_theme.projects):
            new_project = project.copy()
            saved_scale = new_project.scale
            new_project.scale = 1.0

            frame_count = project.frame_count if project.is_ani_cursor else 1
            frame_element = CursorElement(str("已渲染项目"), [])
            for f_index in range(frame_count):
                frame = render_project_frame(new_project, f_index)
                frame_element.frames.append(frame)
                frame_element.source_infos.append(AssetSourceInfo(AssetType.IMAGE, image=frame, size=frame.size))
            frame_element.animation_key_data.frame_length = frame_count
            frame_element.update_ani_data_by_key_data()

            new_project.elements.clear()
            new_project.elements.append(frame_element)
            new_project.scale = saved_scale
            new_theme.projects[i] = new_project
        ThemeManager.save_theme_file(file_path, new_theme)

    def add_theme(self, theme: CursorTheme):  # 添加主题
        self.themes.append(theme)
        self.call_callback(ThemeAction.ADD, theme)

    def remove_theme(self, theme: CursorTheme):  # 移除主题
        self.call_callback(ThemeAction.DELETE, theme)
        self.themes.remove(theme)
        if theme in self.theme_file_mapping:
            if isfile(self.theme_file_mapping[theme]):
                os.remove(self.theme_file_mapping[theme])
            del self.theme_file_mapping[theme]

    def renew_theme(self, theme: CursorTheme):  # 刷新主题名称
        if theme not in self.theme_file_mapping:
            return
        raw_path = self.theme_file_mapping.pop(theme)[:]
        self.theme_file_mapping[theme] = join(self.root_dir,
                                              f"MineCursor Theme_{theme.id}_{theme.name}.mctheme")
        if isfile(raw_path):
            rename(raw_path, self.theme_file_mapping[theme])

    def register_theme_change_callback(self, action: ThemeAction, callback: Callable[[CursorTheme], None]):  # 注册回调
        if action not in self.callbacks:
            self.callbacks[action] = []
        self.callbacks[action].append(callback)

    def call_callback(self, action: ThemeAction, theme: CursorTheme):  # 调用回调
        if action in self.callbacks:
            for callback in self.callbacks[action]:
                callback(theme)

    def find_project(self, project_id: str):  # 查找项目
        for theme in self.themes:
            for project in theme.projects:
                if project.id == project_id:
                    return project
        return None

    def find_theme(self, theme_id: str):  # 查找主题
        for theme in self.themes:
            if theme.id == theme_id:
                return theme
        return None


theme_manager = ThemeManager(path_theme_data)
deleted_theme_manager = ThemeManager(path_deleted_theme_data)
