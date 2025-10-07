import json
import os
import re
import time
import typing
import zlib
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from os import rename
from os.path import join, basename, isfile, dirname, split, isdir, expandvars
from shutil import copytree, rmtree
from threading import Event, Thread
from typing import Callable, Any
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

from lib.config import config
from lib.data import CursorTheme, path_theme_data, CursorElement, \
    AssetSourceInfo, AssetType, path_deleted_theme_data
from lib.datas.base_struct import generate_id
from lib.datas.data_dir import path_user_sources
from lib.datas.source import SourceNotFoundError, AssetSource, source_manager
from lib.log import logger
from lib.perf import Counter
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


def full_dir_into_zip(file: ZipFile, source_dir: str, source_arc_path: str):
    file.write(source_dir, source_arc_path + "/")

    root, dirs, files = next(os.walk(source_dir))
    for dir_name in dirs:
        dir_path = join(root, dir_name)
        arc_dir_path = join(source_arc_path, dir_name)
        full_dir_into_zip(file, dir_path, arc_dir_path)

    for file_name in files:
        file_path = join(root, file_name)
        arc_file_path = join(source_arc_path, split(file_path)[1])
        file.write(file_path, arc_file_path)
def import_theme_sources(zip_io: BytesIO) -> list[AssetSource]:
    work_dir = join(expandvars("%TEMP%"), f"MineCursor Source Extract {generate_id()}")
    os.makedirs(work_dir, exist_ok=True)
    with ZipFile(zip_io) as zip_file:
        zip_file.extractall(work_dir)

    sources_dir = join(work_dir, "sources")
    if not isdir(sources_dir):
        return []

    _, dirs, files = next(os.walk(sources_dir))
    sources = []
    for dir_name in dirs:
        logger.debug(f"导入主题包内置的素材源: {dir_name}")
        dir_path = join(sources_dir, dir_name)
        source_json = join(dir_path, "source.json")
        if isfile(source_json):
            sources.append(AssetSource.from_file(source_json))

    for source in sources:
        if source_manager.get_source_by_id(source.id, False) is None:
            new_dir = join(str(path_user_sources), split(source.source_dir)[1])
            copytree(source.source_dir, new_dir)
            rmtree(source.source_dir)
            source.source_dir = new_dir
            sources.append(source)
            source_manager.user_sources.append(source)
    source_manager.save_source()

    rmtree(work_dir)

    return sources

class ThemeFileType(Enum):
    RAW_JSON = 0
    ZIP_COMPRESS = "zip_compress"
    ZIP_FILE = "zip_file"


@dataclass
class ThemeLoadInfo:
    file_type: ThemeFileType = None
    theme_data: str = None
    zip_io: BytesIO = None
    extra_sources: list[AssetSource] = None
    theme: CursorTheme = None


class ThemeManager:
    """主题管理器, 管理主题, 请避免直接操作themes列表"""

    MCTF = b"MCTF"
    HEADER_TEXT = b" Hite404 - MineCursor@github Cursor Theme File "
    NORMAL_THEME_HEADER = bytes().join([
        MCTF,
        len(HEADER_TEXT).to_bytes(4, "little"),
        HEADER_TEXT
    ])

    def __init__(self, dir_path: str):
        self.root_dir = dir_path
        self.themes: list[CursorTheme] = []
        self.theme_file_mapping: dict[CursorTheme, str] = {}
        self.callbacks: dict[ThemeAction, list[Callable[[CursorTheme], None]]] = {}
        self.load()

        self.live_save_thread: Thread | None = None
        self.live_save_flag = Event()

    def load(self):
        logger.info(f"加载主题... (From: {self.root_dir})")
        timer = Counter()
        _, _, file_names = next(os.walk(self.root_dir))
        for file_name in file_names:
            file_path = str(join(self.root_dir, file_name))
            self.load_theme(file_path)
        logger.info(f"主题加载完毕, 用时: {timer.endT()}")

    def live_save(self):
        """间隔设置的时间后再进行保存"""

        def live_save_thread(wait_time: float):
            self.live_save_flag.wait(timeout=wait_time)
            if self.live_save_flag.is_set():
                return
            self.save()

        if self.live_save_thread and self.live_save_thread.is_alive():
            self.live_save_flag.set()
            self.live_save_thread.join()
            self.live_save_flag.clear()
        self.live_save_thread = Thread(target=live_save_thread, args=(config.live_save_time,), daemon=True)
        self.live_save_thread.start()

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

    def load_theme(self, file_path: str, refresh_id: bool = False, file_mapping: bool = True) -> ThemeLoadInfo | None:
        try:
            theme, info = self.load_theme_file(file_path)
        except SourceNotFoundError as e:
            logger.warning(f"主题 [{file_path}] 中ID为 [{e.source_id}] 的源不存在")
            return None
        logger.info(f"已加载主题: {theme}")
        if refresh_id:
            theme.refresh_id()

        self.add_theme(theme)
        if file_mapping:
            self.theme_file_mapping[theme] = file_path
        info.theme = theme
        return info

    @staticmethod
    def load_theme_file(file_path: str) -> tuple[CursorTheme | dict, ThemeLoadInfo]:
        """从一个MineCursor主题文件加载主题"""
        info = ThemeLoadInfo()
        with open(file_path, "rb") as data_io:
            if data_io.read(4) == ThemeManager.MCTF:
                data_io.read(int.from_bytes(data_io.read(4), "little"))  # 读取并丢弃头文本

                header_length = int.from_bytes(data_io.read(8), "little")
                header: dict[str, Any] = json.loads(data_io.read(header_length))

                data_length = int.from_bytes(data_io.read(8), "little")
                file_type = ThemeFileType(header["type"])
                info.file_type = file_type
                if file_type == ThemeFileType.ZIP_COMPRESS:
                    theme_data = zlib.decompress(data_io.read(data_length)).decode("utf-8")
                elif file_type == ThemeFileType.ZIP_FILE:
                    zip_io = BytesIO(data_io.read(data_length))
                    with ZipFile(zip_io, "r") as zip_file:
                        theme_data = zip_file.read("theme.json").decode("utf-8")
                    zip_io.seek(0)
                    info.zip_io = zip_io
                    info.extra_sources = import_theme_sources(zip_io)
                else:
                    raise RuntimeError(f"无法加载主题: {file_path}, 未知的主题类型")
            else:
                info.file_type = ThemeFileType.RAW_JSON
                data_io.seek(0)
                theme_data = data_io.read().decode("utf-8")
        return CursorTheme.from_dict(json.loads(theme_data)), info

    @staticmethod
    def save_theme_file(file_path: str, theme: CursorTheme, file_type: ThemeFileType = ThemeFileType.ZIP_COMPRESS,
                        extra_sources: list[AssetSource] | None = None):
        """保存主题到一个MineCursor主题文件"""
        logger.debug(f"保存主题至: {basename(file_path)}")

        data_string = json.dumps(theme.to_dict(), ensure_ascii=False)
        if file_type == ThemeFileType.RAW_JSON:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(data_string)
            return

        header = json.dumps({"type": file_type.value}).encode("utf-8")
        with open(file_path, "wb") as f:
            f.write(ThemeManager.NORMAL_THEME_HEADER)
            f.write(len(header).to_bytes(8, "little"))
            f.write(header)
            if file_type == ThemeFileType.ZIP_COMPRESS:
                compressed_theme = zlib.compress(data_string.encode("utf-8"), 1)
                f.write(len(compressed_theme).to_bytes(8, "little"))
                f.write(compressed_theme)
            elif file_type == ThemeFileType.ZIP_FILE:
                zip_io = BytesIO()
                zip_file = ZipFile(zip_io, "x", ZIP_DEFLATED, compresslevel=1)
                zip_file.writestr("theme.json", data_string)
                if extra_sources:
                    dir_info = ZipInfo("sources/", typing.cast(tuple[int, int, int, int, int, int], time.localtime()))
                    zip_file.writestr(dir_info, b"")
                    for source in extra_sources:
                        if source.internal_source:
                            continue
                        full_dir_into_zip(zip_file, source.source_dir, f"sources/{split(source.source_dir)[1]}")
                zip_file.close()
                f.write(len(zip_io.getbuffer()).to_bytes(8, "little"))
                f.write(zip_io.getbuffer())

    @staticmethod
    def save_rendered_theme_file(file_path: str, theme: CursorTheme,
                                 file_type: ThemeFileType = ThemeFileType.ZIP_COMPRESS):
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
        ThemeManager.save_theme_file(file_path, new_theme, file_type)

    def add_theme(self, theme: CursorTheme):  # 添加主题
        self.themes.append(theme)
        self.call_callback(ThemeAction.ADD, theme)

    def remove_theme(self, theme: CursorTheme):  # 移除主题
        if theme in self.theme_file_mapping:
            if isfile(self.theme_file_mapping[theme]):
                os.remove(self.theme_file_mapping[theme])
            del self.theme_file_mapping[theme]
        self.themes.remove(theme)
        self.call_callback(ThemeAction.DELETE, theme)

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
