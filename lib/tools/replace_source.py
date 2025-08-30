# 这个脚本将所有主题的[MC 1.21.5]素材源强制切换为[25w32a]
import os
from os.path import expandvars, split, join

theme_dir = join(split(expandvars("%APPDATA%"))[0], "Mine Cursor\\Theme Data")

for file_name in os.listdir(theme_dir):
    print("Replace:", file_name)
    full_path = join(theme_dir, file_name)
    with open(full_path, "r", encoding="utf-8") as f:
        theme_string = f.read()
    theme_string = theme_string.replace("minecraft-textures-1.21.5", "minecraft-textures-25w32a")
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(theme_string)
