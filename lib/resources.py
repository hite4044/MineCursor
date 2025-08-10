import os
import re
from enum import Enum
from os import rename
from os.path import join, basename, isfile
from typing import Callable

from lib.data import CursorTheme, data_file_manager, WorkFileManager, backup_themes_manager
from lib.log import logger

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
    def __init__(self):
        self.themes: list[CursorTheme] = []
        self.deleted_themes: list[CursorTheme] = []
        self.theme_file_mapping: dict[CursorTheme, str] = {}
        self.callbacks: dict[ThemeAction, list[Callable[[CursorTheme], None]]] = {}
        self.load()

    def load(self):
        logger.info(f"加载主题... (From: {data_file_manager.work_dir})")
        _, _, file_names = next(os.walk(data_file_manager.work_dir))
        for file_name in file_names:
            file_path = str(join(data_file_manager.work_dir, file_name))
            self.load_theme(file_path)

        _, _, file_names = next(os.walk(backup_themes_manager.work_dir))
        for file_name in file_names:
            file_path = str(join(backup_themes_manager.work_dir, file_name))
            theme = self.load_theme_file(file_path)
            self.theme_file_mapping[theme] = file_path
            self.deleted_themes.append(theme)

    def save(self):
        logger.info("正在保存主题")
        self.save_themes(data_file_manager, self.themes)
        self.save_themes(backup_themes_manager, self.deleted_themes)

    def save_themes(self, parent_dir: WorkFileManager, themes: list[CursorTheme]):
        themes_id_mapping = get_dir_all_themes(parent_dir.work_dir)
        for theme in themes:
            if theme.id in themes_id_mapping:
                os.remove(themes_id_mapping[theme.id])
            file_path = str(join(parent_dir.work_dir, f"MineCursor Theme_{theme.id}_{theme.name}.mctheme"))
            self.theme_file_mapping[theme] = file_path
            self.save_theme_file(file_path, theme)

    def load_theme(self, file_path: str):
        theme = self.load_theme_file(file_path)
        logger.info(f"已加载主题: {theme}")
        self.add_theme(theme)
        self.theme_file_mapping[theme] = file_path

    @staticmethod
    def load_theme_file(file_path: str) -> CursorTheme:
        with open(file_path, "r", encoding="utf-8") as f:
            data = eval(f.read())
        return CursorTheme.from_dict(data)

    @staticmethod
    def save_theme_file(file_path: str, theme: CursorTheme):
        logger.debug(f"保存主题至: {basename(file_path)}")
        data_string = str(theme.to_dict())
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(data_string)

    def add_theme(self, theme: CursorTheme):
        self.themes.append(theme)
        self.call_callback(ThemeAction.ADD, theme)

    def remove_theme(self, theme: CursorTheme):
        self.call_callback(ThemeAction.DELETE, theme)
        self.themes.remove(theme)
        if theme in self.theme_file_mapping:
            if isfile(self.theme_file_mapping[theme]):
                os.remove(self.theme_file_mapping[theme])
            del self.theme_file_mapping[theme]

    def renew_theme(self, theme: CursorTheme):
        if theme not in self.theme_file_mapping:
            return
        raw_path = self.theme_file_mapping.pop(theme)
        self.theme_file_mapping[theme] = join(data_file_manager.work_dir,
                                              f"MineCursor Theme_{theme.id}_{theme.name}.mctheme")
        if isfile(raw_path):
            rename(raw_path, self.theme_file_mapping[theme])

    def clear_all_theme(self):
        self.themes.clear()
        for theme in self.theme_file_mapping.keys():
            if isfile(self.theme_file_mapping[theme]):
                os.remove(self.theme_file_mapping[theme])
        self.theme_file_mapping.clear()

    def register_theme_change_callback(self, action: ThemeAction, callback: Callable[[CursorTheme], None]):
        if action not in self.callbacks:
            self.callbacks[action] = []
        self.callbacks[action].append(callback)

    def call_callback(self, action: ThemeAction, theme: CursorTheme):
        if action in self.callbacks:
            for callback in self.callbacks[action]:
                callback(theme)

    def find_project(self, project_id: str):
        for theme in self.themes:
            for project in theme.projects:
                if project.id == project_id:
                    return project
        return None

    def find_theme(self, theme_id: str):
        for theme in self.themes:
            if theme.id == theme_id:
                return theme
        return None


theme_manager = ThemeManager()
