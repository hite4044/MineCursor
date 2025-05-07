from os import makedirs
from os.path import expandvars, join
from random import randbytes
from shutil import copy as copy_file, rmtree

from PIL import Image
from PIL.Image import Resampling

Image.ANTIALIAS = Resampling.LANCZOS
from ani_file import ani_file
from win_cur import Cursor


def create_project_cache():
    temp_dir = expandvars("%TEMP%\\MineCursorCache")
    makedirs(temp_dir, exist_ok=True)
    project_dir = join(temp_dir, hex(int.from_bytes(randbytes(4), "big"))[2:])
    makedirs(project_dir, exist_ok=True)
    return project_dir


def write_ani(path: str, frames: list[Image.Image], hotspot: tuple[int, int], rate: int):
    project_dir = create_project_cache()

    files = []
    for i, frame in enumerate(frames):
        file_path = join(project_dir, f"{i}.png")
        print(file_path, project_dir, f"{i}.png")
        frame.save(file_path)
        files.append(file_path)
    ani_path = join(project_dir, "ani_file.ani")
    ani = ani_file.open(ani_path, "w")
    ani.setframespath(files, xy=hotspot)
    ani.setrate([rate for _ in range(len(frames))])
    ani.close()
    copy_file(ani_path, path)
    rmtree(project_dir)


def write_cur(frame: Image.Image, hotspot: tuple[int, int], path: str):
    cur = Cursor()
    cur.add_cursor(frame.width, frame.height, hotspot[0], hotspot[1], frame.tobytes())
    cur.save_file(path)


def write_cursor(path: str, frames: list[Image.Image], hotspot: tuple[int, int], rate: int):
    if path.endswith(".cur"):
        write_cur(frames[0], hotspot, path)
    else:
        write_ani(path, frames, hotspot, rate)