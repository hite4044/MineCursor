import json
from typing import Any

from lib.log import logger
from lib.struct import ThemeType

CFG_PATH = "config.json"


def get_user_name() -> str:
    import getpass
    return getpass.getuser()


USER_NAME = get_user_name()


class Config:
    first_launch: bool = True
    data_dir: str = "%APPDATA%\..\Mine Cursor"
    show_hidden_themes: bool = False
    live_save_time: float = 7.0
    theme_kind_order: list[ThemeType] = [ThemeType.NORMAL, ThemeType.PRE_DEFINE, ThemeType.TEMPLATE]
    default_author: str = USER_NAME
    enabled_sources: list[str] = None

    def __init__(self):
        self.load_config()

    def find_config_names(self):
        return list(self.__annotations__.keys())

    def load_config(self):
        logger.info(f"加载配置文件 {CFG_PATH}")
        try:
            with open(CFG_PATH, encoding="utf-8") as f:
                cfg_data: dict[str, Any] = json.load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件 {CFG_PATH} 不存在")
            return
        exist_names = self.find_config_names()
        for name, value in cfg_data.items():
            if name == "theme_kind_order":
                value = [ThemeType(t_value) for t_value in value]
            if name == "enabled_sources":
                value = list(set(value))
            if name in exist_names:
                setattr(self, name, value)
            else:
                logger.warning(f"配置项 {name}: {value} 不存在")

    def save_config(self):
        logger.info(f"保存配置文件 {CFG_PATH}")
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            data = {name: getattr(self, name) for name in self.find_config_names()}
            data["theme_kind_order"] = [kind.value for kind in data["theme_kind_order"]]
            json.dump(data, f, ensure_ascii=False, indent=4)


config = Config()
