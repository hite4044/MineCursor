import wx


def select_all(lc: wx.ListCtrl):
    crt_select = lc.GetFirstSelected()
    for idx in range(lc.GetItemCount()):
        if not lc.IsSelected(idx):
            lc.Select(idx, True)
    if crt_select != -1:
        lc.Select(crt_select, False)
        lc.Select(crt_select, True)