import sys
from PyQt5.QtWidgets import QApplication

if sys.platform == "win32":
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "sqlpulse.app.icon.v1"
    )

app = QApplication(sys.argv)

from qfluentwidgets import setTheme, Theme, setThemeColor
from sql_batch_executor.core.preferences import PreferenceManager
from sql_batch_executor.ui import theme
from sql_batch_executor.ui.icons import app_icon

setTheme(Theme.LIGHT)
theme.apply_theme_color(PreferenceManager().theme_color())
setThemeColor(theme.PRIMARY)
app.setWindowIcon(app_icon())

from sql_batch_executor.ui.main_window import MainWindow

win = MainWindow()
win.show()
sys.exit(app.exec_())
