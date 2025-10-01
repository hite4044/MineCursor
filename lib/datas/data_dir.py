from os import makedirs
from os.path import expandvars, abspath, join
from typing import cast

from lib.config import config


class DataDir(str):
    def __new__(cls, path: str, *args, **kwargs) -> 'DataDir':
        makedirs(path, exist_ok=True)
        instance = str.__new__(cls, path)
        instance.make_sub_dir = lambda name: DataDir.make_sub_dir(cast(DataDir, instance), name)
        return cast(DataDir, instance)

    def make_sub_dir(self, name: str) -> 'DataDir':
        makedirs(join(self, name), exist_ok=True)
        return DataDir(join(self, name))


main_dir = DataDir(abspath(expandvars(config.data_dir)))
path_user_sources = main_dir.make_sub_dir("User Sources")
path_theme_cursors = main_dir.make_sub_dir("Theme Cursors")
path_theme_data = main_dir.make_sub_dir(r"Theme Data")
path_deleted_theme_data = main_dir.make_sub_dir(r"Deleted Theme Backup")
