import os
import subprocess
from itertools import cycle
from os import makedirs
from os.path import join

from PIL import Image
from PIL.Image import Resampling

os.chdir(os.path.split(os.path.split(os.path.split(__file__)[0])[0])[0])
from lib.data import CursorProject, CursorTheme
from lib.render import render_project_frame
from lib.resources import theme_manager

PROJECT_SIZE = 128  # 单个项目的图片大小
PROJECT_PAD = 64
FRAME_DIV = 2
FPS = 64 // FRAME_DIV

VER_CNT = 3
HOR_CNT = 5


def main():
    # 开头输出
    print()
    print("主题动态预览图生成工具 - By hite404")
    print()
    print("以下为可用主题")

    # 输出备选主题
    for i, theme in enumerate(theme_manager.themes):
        print(f"{i} -> 主题 [{theme.name}] ({len(theme.projects)}-curs) ({theme.id})")
    print()

    # 输入主题信息
    index = int(input("请输入主题编号: "))
    frames_count = int(input("请输入生成帧数: "))
    current_theme = theme_manager.themes[index]

    # 生成动画帧
    image = Image.new("RGBA", (HOR_CNT * (PROJECT_SIZE + PROJECT_PAD) - PROJECT_PAD,
                               VER_CNT * (PROJECT_SIZE + PROJECT_PAD) - PROJECT_PAD))
    frames: list[Image.Image] = []
    for current_frame in range(frames_count):
        print(f"\r正在生成第{current_frame}帧...", end="")
        frames.append(draw_frame(image, current_frame, current_theme))
    print()

    # 确定保存参数
    print("0 -> 输出多个静态PNG帧")
    print("1 -> 输出一个动态APNG")
    print("2 -> 输出一个动态WEBP")
    print("3 -> 输出一个透明MOV (需安装ffmpeg)")
    print()
    way = input("请输入保存方式: ")
    dir_path = input("输入保存文件夹的地址 (可自动创建): ")

    # 保存帧
    makedirs(dir_path, exist_ok=True)
    print("正在保存文件...")
    if way == "0":
        for i, frame in enumerate(frames):
            print(f"\r正在保存第{i}帧...", end="")
            frame_path = join(dir_path, f"{current_theme.name}_{i}.png")
            frame.save(frame_path, format="PNG")
        print()
    elif way == "1":
        apng_path = join(dir_path, f"{current_theme.name}.apng")
        first_frame = frames.pop(0)
        first_frame.save(apng_path, format="PNG", append_images=frames, duration=int(1 / FPS * 1000))
    elif way == "2":
        apng_path = join(dir_path, f"{current_theme.name}.webp")
        first_frame = frames.pop(0)
        first_frame.save(apng_path, format="WEBP", append_images=frames, duration=int(1 / FPS * 1000))
    elif way == "3":
        paths = []
        for i, frame in enumerate(frames):
            print(f"\r正在保存第{i}帧...", end="")
            frame_path = join(dir_path, f"{current_theme.name}_{i}.png")
            frame.save(frame_path, format="PNG")
            paths.append(frame_path)
        print()
        default_path = join(dir_path, f"{current_theme.name}_%d.png")
        cmd = f"ffmpeg -framerate {FPS} -i {default_path}" \
              f" -r {FPS} -c:v qtrle -y {join(dir_path, current_theme.name)}.mov"
        print(f"即将执行: {cmd}")
        print("执行ffmpeg转码指令中...")
        print("=====================================")
        subprocess.run(cmd, shell=True)
        for path in paths:
            os.remove(path)

    print("=====================================")
    print("图片已全部生成完毕")
    print("感谢使用!")
    print("Tool by hite404")


def draw_frame(base_image: Image.Image, frame_count: int, theme: CursorTheme):
    frame = base_image.copy()
    for y in range(VER_CNT):
        for x in range(HOR_CNT):
            try:
                project = theme.projects[y * HOR_CNT + x]
            except IndexError:
                return frame
            draw_project_frame(project, frame,
                               (x * (PROJECT_SIZE + PROJECT_PAD), y * (PROJECT_SIZE + PROJECT_PAD)),
                               frame_count)
    return frame


def draw_project_frame(project: CursorProject, image: Image.Image, position: tuple[int, int], frame_count: int):
    if not project.is_ani_cursor:
        frame = render_project_frame(project, 0)
        frame = frame.resize((PROJECT_SIZE, PROJECT_SIZE), resample=Resampling.NEAREST)
        image.alpha_composite(frame, position)
        return

    if project.ani_rates:
        project_frame_count = 0
        rates = project.ani_rates.copy()
        if len(rates) > project.frame_count:
            [rates.pop(-1) for _ in range(project.frame_count - len(rates))]
        elif len(rates) < project.frame_count:
            rates.extend(([project.ani_rate for _ in range(len(rates) - project.frame_count)]))
        assert len(rates) == project.frame_count
        for i, frame_time in enumerate(cycle(project.ani_rates)):
            if project_frame_count / 60 >= frame_count / FPS:
                break
            project_frame_count += frame_time
    else:
        project_frame_count = int(frame_count / project.ani_rate * FRAME_DIV) % project.frame_count

    frame = render_project_frame(project, project_frame_count)
    frame = frame.resize((PROJECT_SIZE, PROJECT_SIZE), resample=Resampling.NEAREST)
    image.alpha_composite(frame, position)


if __name__ == "__main__":
    main()
