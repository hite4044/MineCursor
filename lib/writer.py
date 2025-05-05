from os import makedirs
from os.path import expandvars, join
from random import randbytes

from PIL import Image
from ani_file import ani_file
from win_cur import Cursor


def create_project_cache():
    temp_dir = expandvars("%TEMP%/MineCursorCache")
    makedirs(temp_dir, exist_ok=True)
    project_dir = join(temp_dir, hex(int.from_bytes(randbytes(4), "big"))[2:])
    makedirs(project_dir, exist_ok=True)
    return project_dir


def write_ani(path: str, frames: list[Image.Image], hotspot: tuple[int, int], rate: int):
    project_dir = create_project_cache()

    files = []
    for i, frame in enumerate(frames):
        frame.save(join(project_dir, f"{i}.png"))
    ani = ani_file.open(path, "w")
    ani.setframespath(files, xy=hotspot)
    ani.setrate(rate)
    ani.close()


def write_cur(frame: Image.Image, hotspot: tuple[int, int], path: str):
    cur = Cursor()
    cur.add_cursor(frame.width, frame.height, hotspot[0], hotspot[1], frame.tobytes())
    cur.save_file(path)
