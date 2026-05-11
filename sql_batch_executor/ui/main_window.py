import sys

from PyQt5.QtCore import QThread, QRect
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QMenu

from qfluentwidgets import InfoBar, InfoBarPosition, PushButton, Theme, setTheme, setThemeColor
from qfluentwidgets.components.widgets.frameless_window import FramelessWindow

from sql_batch_executor.core.preferences import PreferenceManager
from sql_batch_executor.core.services import ConnectionService
from sql_batch_executor.ui import theme
from sql_batch_executor.ui.connection_mixin import ConnectionMixin
from sql_batch_executor.ui.execution_mixin import ExecutionMixin
from sql_batch_executor.ui.icons import app_icon, apply_windows_taskbar_icon
from sql_batch_executor.ui.layout_mixin import LayoutMixin
from sql_batch_executor.ui.results_mixin import ResultsMixin
from sql_batch_executor.ui.title_bar import AppTitleBar


class MainWindow(LayoutMixin, ConnectionMixin, ExecutionMixin, ResultsMixin, FramelessWindow):
    def __init__(self):
        super().__init__()
        self.BORDER_WIDTH = 10
        self.setResizeEnabled(True)
        self.preferences = PreferenceManager()
        theme.apply_theme_color(self.preferences.theme_color())
        setThemeColor(theme.PRIMARY)
        self.setWindowTitle("SQL 批量执行器")
        self.setWindowIcon(app_icon())
        self.app_title_bar = AppTitleBar(self)
        self.setTitleBar(self.app_title_bar)
        self.resize(1320, 840)
        self.setMinimumSize(960, 640)

        self.service = ConnectionService()
        self.results = []
        self._tab_buttons = []
        self._current_tab = 0
        self._threads: list[QThread] = []
        self._root_lay = None
        self._current_worker = None
        self._page_cache = {}
        self._content_stack = None
        self._normal_geometry = None

        self._build()
        self._restore_window_geometry()

    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowIcon(app_icon())
        apply_windows_taskbar_icon(self)

    def _restore_window_geometry(self):
        geom = self.preferences.window_geometry()
        if geom:
            try:
                self.restoreGeometry(bytes.fromhex(geom))
                self._ensure_normal_geometry_in_screen()
            except Exception:
                pass

    def _screen_available_geometry(self) -> QRect | None:
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        return screen.availableGeometry() if screen else None

    def _clamped_normal_geometry(self, geometry: QRect | None = None) -> QRect:
        available = self._screen_available_geometry()
        if available is None:
            return geometry or QRect(80, 80, 1320, 840)

        minimum = self.minimumSize()
        max_width = max(minimum.width(), min(1320, available.width() - 80))
        max_height = max(minimum.height(), min(840, available.height() - 80))
        source = geometry if geometry and geometry.isValid() else QRect(0, 0, max_width, max_height)

        width = min(max(source.width(), minimum.width()), max_width)
        height = min(max(source.height(), minimum.height()), max_height)
        left = min(max(source.left(), available.left() + 40), available.right() - width + 1)
        top = min(max(source.top(), available.top() + 40), available.bottom() - height + 1)
        return QRect(left, top, width, height)

    def _ensure_normal_geometry_in_screen(self):
        if self.isMaximized():
            return
        available = self._screen_available_geometry()
        geometry = self.geometry()
        if available is None:
            return
        if (
            geometry.width() > available.width()
            or geometry.height() > available.height()
            or not available.intersects(geometry)
        ):
            self.setGeometry(self._clamped_normal_geometry(geometry))
        self._normal_geometry = self.geometry()

    def _remember_normal_geometry(self):
        if not self.isMaximized() and not self.isMinimized():
            self._normal_geometry = self._clamped_normal_geometry(self.geometry())

    def restore_normal_window(self):
        self.showNormal()
        self.setGeometry(self._clamped_normal_geometry(self._normal_geometry or self.geometry()))
        self._normal_geometry = self.geometry()

    def _save_window_geometry(self):
        self._remember_normal_geometry()
        geom = self.saveGeometry().toHex().data().decode("ascii")
        self.preferences.set_window_geometry(geom)

    def closeEvent(self, event):
        self._save_window_geometry()
        super().closeEvent(event)

    def _track_thread(self, thread: QThread):
        self._threads.append(thread)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)

    def _theme_button_style(self) -> str:
        return f"""
            PushButton {{
                background: {theme.SURFACE};
                color: {theme.PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                font-weight: 600;
            }}
            PushButton:hover {{
                background: {theme.PRIMARY_SOFT};
                border-color: {theme.PRIMARY};
            }}
            PushButton:pressed {{
                background: {theme.PRIMARY_SOFT};
                border-color: {theme.PRIMARY_PRESSED};
            }}
        """

    def _theme_icon(self, color: str) -> QIcon:
        pixmap = QPixmap(18, 18)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(2, 2, 14, 14, 4, 4)
        painter.end()
        return QIcon(pixmap)

    def _show_theme_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {theme.SURFACE};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 4px;
                font-size: 12px;
            }}
            QMenu::item {{
                padding: 7px 24px 7px 8px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background: {theme.PRIMARY_SOFT};
                color: {theme.PRIMARY};
            }}
        """)
        current = theme.current_theme_color()
        for color_key, preset in theme.THEME_COLOR_PRESETS.items():
            action = menu.addAction(self._theme_icon(preset.primary), preset.name)
            action.setCheckable(True)
            action.setChecked(color_key == current)
            action.triggered.connect(lambda checked=False, key=color_key: self._set_theme_color(key))
        menu.exec_(self.theme_btn.mapToGlobal(self.theme_btn.rect().bottomLeft()))

    def _set_theme_color(self, color_key: str):
        if color_key == theme.current_theme_color():
            return
        if self._threads:
            InfoBar.warning("稍后切换", "当前有任务正在运行，完成后再切换主题色。", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return

        sql_text = self.sql_input.toPlainText() if hasattr(self, "sql_input") else ""
        results = list(self.results)
        search_text = self.search_edit.text() if hasattr(self, "search_edit") else ""
        continue_on_error = self.continue_on_error_check.isChecked() if hasattr(self, "continue_on_error_check") else False

        preset = theme.apply_theme_color(color_key)
        setThemeColor(theme.PRIMARY)
        self.preferences.set_theme_color(color_key)
        self.app_title_bar.apply_theme()

        self._tab_buttons = []
        self._current_tab = 0
        self._build()
        self.sql_input.setPlainText(sql_text)
        if hasattr(self, "continue_on_error_check"):
            self.continue_on_error_check.setChecked(continue_on_error)
        self.results = results
        if hasattr(self, "search_edit"):
            self.search_edit.setText(search_text)
        if self.results:
            self._show_results()

        InfoBar.success("主题色已切换", preset.name, parent=self, position=InfoBarPosition.TOP_RIGHT)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    setTheme(Theme.LIGHT)
    setThemeColor(theme.PRIMARY)
    win = MainWindow()
    win.show()
    if not app.topLevelWidgets():
        app.exec_()


if __name__ == "__main__":
    main()
