import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

if sys.platform == "win32":
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "sql.batch.executor"
    )

app = QApplication(sys.argv)

from qfluentwidgets import setTheme, Theme, setThemeColor
from sql_batch_executor.app.resources import APP_ICON_PATH
from sql_batch_executor.core.preferences import PreferenceManager
from sql_batch_executor.ui import theme

setTheme(Theme.LIGHT)
theme.apply_theme_color(PreferenceManager().theme_color())
setThemeColor(theme.PRIMARY)
app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

from sql_batch_executor.ui.main_window import MainWindow

win = MainWindow()
win.show()
sys.exit(app.exec_())
