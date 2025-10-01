from dataclasses import field, dataclass
from datetime import datetime

from lib.datas.base_struct import *
from lib.datas.project import CursorProject
from lib.struct import ThemeType

DEFAULT_NOTE = """这个人或许不想写备注"""

DEFAULT_LICENSE_INFO = """\
主题提供协议 - CC BY-NC-SA 4.0:
https://creativecommons.org/licenses/by-nc-sa/4.0/

此主题使用的部分游戏资源, 遵循此条款:
https://www.minecraft.net/usage-guidelines
"""


@dataclass
class CursorTheme:
    name: str
    base_size: int = 32
    author: str = "Unknow"
    description: str = "None"
    type: ThemeType = ThemeType.NORMAL
    projects: list[CursorProject] = field(default_factory=list)

    id: str = field(default_factory=generate_id)

    note: str = DEFAULT_NOTE
    license_info: str = DEFAULT_LICENSE_INFO
    create_time: str = datetime.now().strftime("%Y-%m-%d %H:%M")

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return f"<Theme:[{self.name}],{self.base_size}px,{len(self.projects)}-curs>"

    def to_dict(self):
        data = {
            "name": self.name,
            "type": self.type.value,
            "id": self.id,
            "base_size": self.base_size,
            "author": self.author,
            "description": self.description,
            "projects": [project.to_dict() for project in self.projects],
            "create_time": self.create_time,
        }
        if self.note:
            data["note"] = self.note
        if self.license_info:
            data["license_info"] = self.license_info
        return data

    @staticmethod
    def from_dict(data: dict) -> 'CursorTheme':
        return CursorTheme(
            name=data["name"],
            type=ThemeType(data.get("type", ThemeType.NORMAL)),
            id=data["id"],
            base_size=data["base_size"],
            author=data["author"],
            description=data["description"],
            projects=[CursorProject.from_dict(project) for project in data["projects"]],
            note=data.get("note", ""),
            license_info=data.get("license_info", ""),
            create_time=data.get("create_time", "Unknow")
        )

    def refresh_id(self):
        self.id = generate_id()

    def copy(self):
        data = self.to_dict()
        data["id"] = generate_id()
        return self.from_dict(data)

    @property
    def make_time(self):
        return sum(project.make_time for project in self.projects)
