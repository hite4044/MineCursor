from lib.data import CursorTheme


class ThemeManager:
    def __init__(self):
        self.themes: list[CursorTheme] = []

    def add_theme(self, theme: CursorTheme):
        self.themes.append(theme)

    def remove_theme(self, theme: CursorTheme):
        self.themes.remove(theme)

    def clear_all_theme(self):
        self.themes.clear()


theme_manager = ThemeManager()
