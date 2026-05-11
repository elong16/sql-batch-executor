import sys

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer

from sql_batch_executor.app.resources import APP_ICON_ICO_PATH, APP_ICON_PATH


def _render_svg_icon(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    renderer = QSvgRenderer(str(APP_ICON_PATH))
    if not renderer.isValid():
        return QPixmap()

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


def app_icon() -> QIcon:
    if APP_ICON_ICO_PATH.exists():
        icon = QIcon(str(APP_ICON_ICO_PATH))
        if not icon.isNull():
            return icon

    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64, 128, 256):
        pixmap = _render_svg_icon(size)
        if not pixmap.isNull():
            icon.addPixmap(pixmap)
    if icon.isNull():
        return QIcon(str(APP_ICON_PATH))
    return icon


def app_icon_pixmap(size: int) -> QPixmap:
    pixmap = _render_svg_icon(size)
    if not pixmap.isNull():
        return pixmap
    return QIcon(str(APP_ICON_PATH)).pixmap(size, size)


def apply_windows_taskbar_icon(widget) -> None:
    if sys.platform != "win32" or not APP_ICON_ICO_PATH.exists():
        return

    try:
        import ctypes

        hwnd = int(widget.winId())
        if not hwnd:
            return

        user32 = ctypes.windll.user32
        image_icon = 1
        lr_default_size = 0x00000040
        lr_load_from_file = 0x00000010
        wm_seticon = 0x0080
        icon_small = 0
        icon_big = 1
        gclp_hicon = -14
        gclp_hiconsm = -34

        small = user32.LoadImageW(None, str(APP_ICON_ICO_PATH), image_icon, 16, 16, lr_load_from_file)
        big = user32.LoadImageW(None, str(APP_ICON_ICO_PATH), image_icon, 32, 32, lr_load_from_file)
        default_icon = user32.LoadImageW(None, str(APP_ICON_ICO_PATH), image_icon, 0, 0, lr_load_from_file | lr_default_size)
        if small:
            user32.SendMessageW(hwnd, wm_seticon, icon_small, small)
        if big:
            user32.SendMessageW(hwnd, wm_seticon, icon_big, big)
        if default_icon:
            user32.SendMessageW(hwnd, wm_seticon, icon_big, default_icon)

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            set_class_long_ptr = user32.SetClassLongPtrW
        else:
            set_class_long_ptr = user32.SetClassLongW
        set_class_long_ptr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        set_class_long_ptr.restype = ctypes.c_void_p
        if small:
            set_class_long_ptr(ctypes.c_void_p(hwnd), gclp_hiconsm, ctypes.c_void_p(small))
        if default_icon or big:
            set_class_long_ptr(ctypes.c_void_p(hwnd), gclp_hicon, ctypes.c_void_p(default_icon or big))

        widget._windows_icon_handles = (small, big, default_icon)
    except Exception:
        return
