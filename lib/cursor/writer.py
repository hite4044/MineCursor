from os import makedirs
from os.path import expandvars, join
from random import randbytes
from shutil import copy as copy_file, rmtree

from PIL import Image
from PIL.Image import Resampling

from lib.data import CursorProject

Image.ANTIALIAS = Resampling.LANCZOS
from ani_file import ani_file
from win_cur import Cursor


def create_project_cache():
    temp_dir = expandvars("%TEMP%\\MineCursorCache")
    makedirs(temp_dir, exist_ok=True)
    project_dir = join(temp_dir, hex(int.from_bytes(randbytes(4), "big"))[2:])
    makedirs(project_dir, exist_ok=True)
    return project_dir


def write_ani(path: str, frames: list[Image.Image], project: CursorProject):
    project_dir = create_project_cache()
    hotspot = (int(project.center_pos[0] * project.scale), int(project.center_pos[1] * project.scale))
    if project.ani_rates:
        rates = project.ani_rates + [project.ani_rate] * (project.frame_count - len(project.ani_rates))
    else:
        rates = [project.ani_rate] * project.frame_count

    files = []
    for i, frame in enumerate(frames):
        file_path = join(project_dir, f"{i}.png")
        frame.save(file_path)
        files.append(file_path)
        yield "写入帧", i
    ani_path = join(project_dir, "ani_file.ani")
    ani = ani_file.open(ani_path, "w")
    yield "合并帧", -1
    ani.setframespath(files, xy=hotspot)
    ani.setrate(rates)
    ani.close()
    yield "复制文件至保存路径", -1
    copy_file(ani_path, path)
    yield "删除临时文件", -1
    rmtree(project_dir)


def write_cur(frame: Image.Image, hotspot: tuple[int, int], path: str):
    cur = Cursor()
    cur.add_cursor(frame.width, frame.height, hotspot[0], hotspot[1], frame.tobytes())
    cur.save_file(path)


def write_cursor_progress(path: str, frames: list[Image.Image], project: CursorProject):
    hotspot = (int(project.center_pos[0] * project.scale), int(project.center_pos[1] * project.scale))
    if path.endswith(".cur"):
        yield "保存至cur文件", -1
        write_cur(frames[0], hotspot, path)
    else:
        gen = write_ani(path, frames, project)
        while True:
            try:
                yield next(gen)
            except StopIteration:
                break
