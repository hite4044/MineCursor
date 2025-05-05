import ctypes

from win32con import OCR_NO
import win32con as con
from win32gui import LR_LOADFROMFILE, IMAGE_CURSOR, LoadImage

from ctypes import windll
ALL_OCR = {}
for name in dir(con):
    if name.startswith("OCR_"):
        ALL_OCR[getattr(con, name)] = name

SetSystemCursor = windll.user32.SetSystemCursor
CopyImage = windll.user32.CopyImage

path = "D:\CustomProgramData\Minecraft cursors by Exoridus\LoadingPickaxe.ani"
cursor = LoadImage(None, path, IMAGE_CURSOR, 32, 32, LR_LOADFROMFILE)
print(SetSystemCursor(32631, cursor))
exit()
print(cursor, ctypes.GetLastError())
for i in range(31512, 33650):
    new_cursor = CopyImage(cursor, IMAGE_CURSOR, 0, 0, 0)
    ret = SetSystemCursor(new_cursor, i)
    if ret == 1:
        if i in ALL_OCR:
            print("SetSystemCursor Success: ", i, ALL_OCR[i])
        else:
            print("SetSystemCursor Success: ", i)