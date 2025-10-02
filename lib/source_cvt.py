import hashlib
import json
import re
from copy import deepcopy
from io import BytesIO
from os.path import join, split
from shutil import copy as copy_file
from zipfile import ZipFile, ZIP_DEFLATED

import toml
from PIL import Image

from lib.data import AssetSource
from lib.datas.base_struct import generate_id

NOTE_TEMP = """模组协议: {}"""


def check_names(file: ZipFile, names: list[str]) -> bytes | None:
    for name in names:
        if name in file.NameToInfo:
            return file.read(name)
    return None


def append_basic_info(file: ZipFile, note: str) -> str:
    if info := check_names(file, ["README.txt", "README", "readme.txt", "ReadMe.txt", "README.TXT", "README.md"]):
        note += "说明文件 (Readme): \n"
        note += info.decode("utf-8", errors="ignore")
        note += "\n"
    if info := check_names(file, ["LICENSE.txt", "LICENSE", "License.txt", "License", "license.txt", "license"]):
        note += "协议文件 (License): \n"
        note += info.decode("utf-8", errors="ignore")
        note += "\n"
    return note


def load_jar2source(fp: str, extract_dir: str = None):
    jar = ZipFile(fp)
    info_bytes = jar.read("META-INF/mods.toml")
    info = toml.loads(info_bytes.decode("utf-8"))

    # 提取模组信息
    mods = info["mods"][0]
    mod_id = mods["modId"]
    name = mods.get("displayName", "新素材源")
    version = mods.get("version", "未知")
    authors = mods.get("authors", "未知")
    description = mods.get("description", "未知")
    note = NOTE_TEMP.format(info["license"]) if info.get("license") else "未知"
    source_id = f"{name}-{version}-{hex(hash(info_bytes))[2:2 + 8]}"
    note = append_basic_info(jar, note)

    # 保存图标
    if icon := mods.get("logoFile"):
        image = Image.open(BytesIO(jar.read(icon)))
        image = image.convert("RGBA")
        image.save(join(extract_dir, "icon.png"), "PNG")

    # 提取贴图
    texture_zip = ZipFile(join(extract_dir, "textures.zip"), "x", ZIP_DEFLATED, compresslevel=1)
    textures_root = f"assets/{mod_id}/textures/"
    for path, info in jar.NameToInfo.items():
        if path.startswith(textures_root) and path != textures_root:
            new_info = deepcopy(info)
            new_info.filename = info.filename.replace(textures_root, "", 1)
            new_info.orig_filename = info.orig_filename.replace(textures_root, "", 1)
            if info.is_dir():
                texture_zip.filelist.append(new_info)
            else:
                texture_zip.writestr(new_info, jar.read(path))

    texture_zip.close()

    # 保留完整Jar文件
    copy_file(fp, join(extract_dir, "full.zip"))
    with open(join(extract_dir, "orig_filename"), "w", encoding="utf-8") as f:
        f.write(split(fp)[1])

    source = AssetSource(name, source_id, version, authors, description, note, extract_dir)
    return source


def load_zip2source(fp: str, extract_dir: str = None):
    with open(fp, "rb") as f:
        file_context = f.read()
    pack = ZipFile(BytesIO(file_context))
    info_bytes = pack.read("pack.mcmeta")
    info = json.loads(info_bytes.decode("utf-8"))

    # 选择大小较大的资源文件夹
    assets_dirs: dict[str, int] = {}
    for path, info in pack.NameToInfo.items():
        if path.startswith("assets/"):
            parts = path.split("/")
            if path.endswith("textures/") and len(parts) == 3:
                if path in assets_dirs:
                    continue
                dir_path = parts[1]
                assets_dirs[dir_path] = 0
            elif len(parts) >= 3 and path[2] == "textures" and path[-1] != "/":
                dir_path = parts[1]
                try:
                    assets_dirs[dir_path] += info.file_size
                except KeyError:
                    assets_dirs[dir_path] = info.file_size

    # 筛选资源文件夹
    if len(assets_dirs) == 0:
        raise RuntimeError("未找到资源文件夹")
    max_dir = None
    max_size = -1
    for dir_path, size in assets_dirs.items():
        if size > max_size:
            max_dir = dir_path
            max_size = size

    # 提取贴图
    textures_zip = ZipFile(join(extract_dir, "textures.zip"), "x", ZIP_DEFLATED, compresslevel=1)
    textures_root = max_dir + "textures/"
    for path, info in pack.NameToInfo.items():
        if path.startswith(textures_root) and not path.endswith("/"):
            new_info = deepcopy(info)
            new_info.filename = info.filename.replace(max_dir, "", 1)
            new_info.orig_filename = info.orig_filename.replace(max_dir, "", 1)
            textures_zip.writestr(new_info, pack.read(path))
    textures_zip.close()

    # 提取资源包信息
    name = split(fp)[1].replace(".zip", "")
    fp_name = re.sub("§[0123456789abcdef]", "", split(fp)[1])
    source_id = f"{fp_name}-{generate_id()}"
    description = info["pack"].get("description", "未知")
    description = re.sub("§[0123456789abcdef]", "", description).replace("\n", " ")
    note = f"来源于Zip资源包: {split(fp)[1]}\n" \
           f"文件sha256: {hashlib.sha256(file_context).hexdigest()}\n" \
           f"资源包标题: {description}\n"
    note = append_basic_info(pack, note)

    # 保存图标
    try:
        image = Image.open(BytesIO(pack.read("pack.png")))
        image = image.convert("RGBA")
        image.save(join(extract_dir, "icon.png"), "PNG")
    except KeyError:
        pass

    source = AssetSource(name, source_id, f"未知", f"未知", description, note, extract_dir)
    return source
