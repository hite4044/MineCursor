import hashlib
import json
import re
from copy import deepcopy
from io import BytesIO
from os.path import join, split
from shutil import copy as copy_file
from typing import Any
from zipfile import ZipFile, ZIP_DEFLATED

import toml
from PIL import Image

from lib.data import AssetSource
from lib.datas.base_struct import generate_id


def check_names(file: ZipFile, names: list[str]) -> bytes | None:
    for name in names:
        if name in file.NameToInfo:
            return file.read(name)
    return None


def append_basic_info(file: ZipFile, note: str) -> str:
    """添加README、MCMETA、License文件的内容进入描述"""
    if info := check_names(file, ["pack.mcmeta"]):
        note += "\n资源包信息 (Mcmeta): \n"
        note += info.decode("utf-8", errors="ignore")
        note += "\n"
    if info := check_names(file, ["README.txt", "README", "readme.txt", "ReadMe.txt", "README.TXT", "README.md"]):
        note += "\n说明文件 (Readme): \n"
        note += info.decode("utf-8", errors="ignore")
        note += "\n"
    if info := check_names(file, ["LICENSE.txt", "LICENSE", "License.txt", "License", "license.txt", "license"]):
        note += "\n\n协议文件 (License): \n"
        note += info.decode("utf-8", errors="ignore")
        note += "\n"
    return note


class ModInfo:
    def __init__(self):
        self.name: str = ""
        self.mod_id: str = ""
        self.version: str = ""
        self.authors: str = ""
        self.description: str = ""
        self.icon: str | None = None
        self.license: str | None = None
        self.uri: str | None = None

        self.source_id: str = ""

    def load_as_forge(self, info: dict[str, Any], jar_version: str = None):
        mod = info["mods"][0]
        self.name = mod.get("displayName", "新素材源")
        self.mod_id = mod.get("modId", "what, this mod has no modId")
        self.version = mod.get("version", "未知")
        if "${file.jarVersion}" in self.version and jar_version:
            self.version = self.version.replace("${file.jarVersion}", jar_version)
        self.authors = mod.get("authors", "未知")
        self.description = mod.get("description", "未知")
        self.icon = mod.get("logoFile")
        self.source_id = f"{self.name}-{self.version}-{hex(hash(str(info)))[3:3 + 8]}"
        self.license = info.get('license')
        self.uri = mod.get('displayURL')

    def load_as_fabric(self, info: dict[str, Any]):
        self.name = info.get("name", "新素材源")
        self.mod_id = info.get("id", "fabric-mod")
        self.version = info.get("version", "未知")
        self.authors = ", ".join(info.get("authors", ["未知"]))
        self.description = info.get("description", "未知")
        self.icon = info.get("icon")
        self.source_id = f"{self.name}-{self.version}-{hex(hash(str(info)))[3:3 + 8]}"
        if license_list := info.get('license'):
            self.license = ", ".join(license_list)
        self.uri = info.get('contact', {}).get('homepage')


def load_jar2source(fp: str, extract_dir: str = None) -> AssetSource:
    jar = ZipFile(fp)
    if "META-INF/mods.toml" in jar.NameToInfo:  # Forge
        info_bytes = jar.read("META-INF/mods.toml")
        forge_or_fabric = True
    elif "META-INF/neoforge.mods.toml" in jar.NameToInfo:  # NeoForge
        info_bytes = jar.read("META-INF/neoforge.mods.toml")
        forge_or_fabric = True
    elif "fabric.mod.json" in jar.NameToInfo:  # Fabric
        info_bytes = jar.read("fabric.mod.json")
        forge_or_fabric = False
    else:
        raise NotImplementedError("不支持的模组格式")

    # 提取模组信息
    info = ModInfo()
    if forge_or_fabric:  # Forge & Neoforge
        jar_version = None
        if "META-INF/MANIFEST.MF" in jar.NameToInfo:  # 如果有jar信息文件, 就提取
            mf = jar.read("META-INF/MANIFEST.MF").decode("utf-8")
            result_list = re.findall(r"Implementation-Version: .+\n", mf)
            if result_list:
                data_line: str = result_list[0]
                jar_version = data_line.rstrip("\n").rstrip("\r").replace("Implementation-Version: ", "")
        info_dict = toml.loads(info_bytes.decode("utf-8"))
        info.load_as_forge(info_dict, jar_version)
    else:  # Fabric!
        info_dict = json.loads(info_bytes.decode("utf-8"))
        info.load_as_fabric(info_dict)
    note = ""  # 添加额外信息进入描述
    if info.license:
        note += f"模组协议: {info.license}\n"
    if info.uri:
        note += f"模组主页: {info.uri}\n"
    note = append_basic_info(jar, note)

    # 保存图标
    if icon := info.icon:
        image = Image.open(BytesIO(jar.read(icon)))
        image = image.convert("RGBA")
        image.save(join(extract_dir, "icon.png"), "PNG")

    # 提取贴图
    texture_zip = ZipFile(join(extract_dir, "textures.zip"), "x", ZIP_DEFLATED, compresslevel=1)
    textures_root = f"assets/{info.mod_id}/textures/"
    for path, zip_info in jar.NameToInfo.items():
        if path.startswith(textures_root) and path != textures_root:
            new_info = deepcopy(zip_info)
            new_info.filename = zip_info.filename.replace(textures_root, "", 1)
            new_info.orig_filename = zip_info.orig_filename.replace(textures_root, "", 1)
            if zip_info.is_dir():
                texture_zip.filelist.append(new_info)
            else:
                texture_zip.writestr(new_info, jar.read(path))

    texture_zip.close()

    # 保留完整Jar文件
    copy_file(fp, join(extract_dir, "full.zip"))
    with open(join(extract_dir, "orig_filename"), "w", encoding="utf-8") as f:
        f.write(split(fp)[1])

    source = AssetSource(info.name, info.source_id, info.version, info.authors, info.description, note, extract_dir)
    return source


def load_zip2source(fp: str, extract_dir: str = None):
    with open(fp, "rb") as f:
        file_context = f.read()
    pack = ZipFile(BytesIO(file_context))

    # 选择大小较大的资源文件夹
    assets_dirs: dict[str, int] = {}
    for path, zip_info in pack.NameToInfo.items():
        print(path)
        if path.startswith("assets/"):
            parts = path.split("/")
            if path.endswith("textures/") and len(parts) == 4:
                if path in assets_dirs:
                    continue
                dir_path = parts[1]
                assets_dirs[dir_path] = 0
            elif len(parts) >= 4 and path[2] == "textures" and path[-1] != "/":
                dir_path = parts[1]
                try:
                    assets_dirs[dir_path] += zip_info.file_size
                except KeyError:
                    assets_dirs[dir_path] = zip_info.file_size

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
    for path, zip_info in pack.NameToInfo.items():
        if path.startswith(textures_root) and not path.endswith("/"):
            new_info = deepcopy(zip_info)
            new_info.filename = zip_info.filename.replace(max_dir, "", 1)
            new_info.orig_filename = zip_info.orig_filename.replace(max_dir, "", 1)
            textures_zip.writestr(new_info, pack.read(path))
    textures_zip.close()

    # 提取资源包信息
    info_bytes = pack.read("pack.mcmeta")
    info = json.loads(info_bytes.decode("utf-8"))
    name = split(fp)[1].replace(".zip", "")
    fp_name = re.sub("§[0123456789abcdef]", "", split(fp)[1])
    source_id = f"{fp_name}-{generate_id()}"
    description = info["pack"].get("description", "未知")
    description = re.sub("§[0123456789abcdef]", "", description).replace("\n", " ")
    note = f"来源于Zip资源包: {split(fp)[1]}\n" \
           f"文件md5: {hashlib.md5(file_context).hexdigest()}\n" \
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
