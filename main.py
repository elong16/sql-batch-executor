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
from app_resources import APP_ICON_PATH
from ui_theme import PRIMARY
setTheme(Theme.LIGHT)
setThemeColor(PRIMARY)
app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

from gui import MainWindow

win = MainWindow()
win.show()
sys.exit(app.exec_())
