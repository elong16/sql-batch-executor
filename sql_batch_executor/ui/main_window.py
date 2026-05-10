import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea, QStackedWidget,
    QTableWidgetItem, QAbstractItemView, QMenu, QDialog, QPushButton,
)
from PyQt5.QtCore import Qt, QEvent, QThread
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QKeyEvent, QCursor

from qfluentwidgets import (
    CardWidget, SimpleCardWidget,
    PrimaryPushButton, PushButton, TransparentPushButton,
    LineEdit, ComboBox, CheckBox, PlainTextEdit,
    ProgressBar, BodyLabel, SubtitleLabel, CaptionLabel,
    InfoBar, InfoBarPosition, Dialog, MessageBox,
    TableWidget, ScrollArea, MSFluentTitleBar,
    setTheme, Theme, setThemeColor,
)
from qfluentwidgets.components.widgets.frameless_window import FramelessWindow

from sql_batch_executor.app.resources import APP_ICON_PATH
from sql_batch_executor.core.config_manager import ConnectionConfig
from sql_batch_executor.core.preferences import PreferenceManager
from sql_batch_executor.core.services import ConnectionService
from sql_batch_executor.database.manager import ExecutionResult, StatementExecutionResult
from sql_batch_executor.ui import theme
from sql_batch_executor.ui.workers import SqlExecutionWorker, TestConnectionWorker


class TitleControlButton(QPushButton):
    def __init__(self, role: str, object_name: str, parent=None):
        super().__init__("", parent)
        self._role = role
        self._restore = False
        self.setObjectName(object_name)
        self.setFixedSize(36, 28)
        self.setCursor(Qt.ArrowCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def set_restore_icon(self, is_restore: bool):
        self._restore = is_restore
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        is_hover = self.underMouse()
        is_pressed = self.isDown()
        bg = QColor(0, 0, 0, 0)
        border = QColor(0, 0, 0, 0)
        icon = QColor(theme.TEXT_MUTED)

        if is_hover or is_pressed:
            if self._role == "close":
                bg = QColor("#b91c1c" if is_pressed else theme.DANGER)
                border = bg
                icon = QColor("#ffffff")
            else:
                bg = QColor(theme.PRIMARY_SOFT if is_pressed else theme.APP_BACKGROUND)
                border = QColor(0, 0, 0, 0)
                icon = QColor(theme.PRIMARY_PRESSED if is_pressed else theme.PRIMARY)

        painter.setPen(border)
        painter.setBrush(bg)
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)

        pen = QPen(icon, 1.6)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if self._role == "min":
            painter.drawLine(12, 15, 22, 15)
        elif self._role == "max":
            if self._restore:
                painter.drawRect(12, 12, 8, 7)
                painter.drawLine(15, 9, 23, 9)
                painter.drawLine(23, 9, 23, 16)
            else:
                painter.drawRect(12, 10, 10, 10)
        else:
            painter.drawLine(12, 10, 22, 20)
            painter.drawLine(22, 10, 12, 20)


class AppTitleBar(MSFluentTitleBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("appTitleBar")
        self.setFixedHeight(42)
        self.setAttribute(Qt.WA_StyledBackground)
        self.iconLabel.setFixedSize(20, 20)
        self.iconLabel.setPixmap(QIcon(str(APP_ICON_PATH)).pixmap(20, 20))
        self.titleLabel.hide()

        self.appTitleLabel = QLabel(parent.windowTitle(), self)
        self.appTitleLabel.setFixedHeight(24)
        self.appTitleLabel.setMinimumWidth(180)
        self.apply_theme()
        self.hBoxLayout.insertWidget(3, self.appTitleLabel, 0, Qt.AlignVCenter)
        parent.windowTitleChanged.connect(self.appTitleLabel.setText)

        for button in (self.minBtn, self.maxBtn, self.closeBtn):
            button.hide()

        self.controlGroup = QFrame(self)
        self.controlGroup.setObjectName("windowControlGroup")
        self.controlGroup.setFixedHeight(34)
        self.controlGroup.setStyleSheet(f"""
            #windowControlGroup {{
                background: transparent;
                border: none;
            }}
        """)
        control_lay = QHBoxLayout(self.controlGroup)
        control_lay.setContentsMargins(0, 3, 4, 3)
        control_lay.setSpacing(4)

        self.minControlBtn = TitleControlButton("min", "titleMinButton", self.controlGroup)
        self.maxControlBtn = TitleControlButton("max", "titleMaxButton", self.controlGroup)
        self.closeControlBtn = TitleControlButton("close", "titleCloseButton", self.controlGroup)

        control_lay.addWidget(self.minControlBtn)
        control_lay.addWidget(self.maxControlBtn)
        control_lay.addWidget(self.closeControlBtn)
        self.hBoxLayout.addWidget(self.controlGroup, 0, Qt.AlignRight | Qt.AlignVCenter)

        self.minControlBtn.clicked.connect(parent.showMinimized)
        self.maxControlBtn.clicked.connect(self._toggle_max_restore)
        self.closeControlBtn.clicked.connect(parent.close)

        self.apply_theme()
        self._update_max_button()

    def apply_theme(self):
        self.appTitleLabel.setStyleSheet(f"""
            color: {theme.TEXT_PRIMARY};
            background: transparent;
            font-size: 13px;
            font-weight: 600;
        """)
        self.setStyleSheet(f"""
            #appTitleBar {{
                background: {theme.APP_CHROME};
                border-bottom: 1px solid {theme.BORDER};
            }}
        """)
        self.update()
        for name in ("minControlBtn", "maxControlBtn", "closeControlBtn"):
            button = getattr(self, name, None)
            if button:
                button.update()

    def _toggle_max_restore(self):
        if self.window().isMaximized():
            self.window().showNormal()
        else:
            self.window().showMaximized()
        self._update_max_button()

    def _update_max_button(self):
        self.maxControlBtn.set_restore_icon(self.window().isMaximized())

    def eventFilter(self, obj, event):
        result = super().eventFilter(obj, event)
        if obj is self.window() and event.type() == QEvent.WindowStateChange:
            self._update_max_button()
        return result

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.APP_CHROME))
        super().paintEvent(event)


# ═══════════════════════════════════════════════════════════════
#  Connection Dialog
# ═══════════════════════════════════════════════════════════════
class ConnDialog(Dialog):
    def __init__(self, parent, conn: ConnectionConfig, title="添加连接", service: ConnectionService | None = None):
        super().__init__(title, "", parent)
        self.contentLabel.hide()
        self.setMinimumWidth(520)
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.result = None
        self._conn = conn
        self.service = service or parent.service
        self._build_form()
        self.textLayout.addSpacing(8)
        self.setFixedSize(max(self.sizeHint().width(), 520), self.sizeHint().height())

    def _build_form(self):
        form = QVBoxLayout()
        form.setSpacing(12)

        intro = CaptionLabel("保存 MySQL 连接信息，用于后续批量执行 SQL。")
        theme.set_label_color(intro, theme.TEXT_MUTED)
        form.addWidget(intro)

        form.addWidget(BodyLabel("连接名称"))
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("给连接起个名字")
        self.name_edit.setText(self._conn.name)
        self.name_edit.setClearButtonEnabled(True)
        form.addWidget(self.name_edit)

        hp_row = QHBoxLayout()
        hp_row.setSpacing(12)
        col_host = QVBoxLayout()
        col_host.addWidget(BodyLabel("主机地址"))
        self.host_edit = LineEdit()
        self.host_edit.setPlaceholderText("localhost")
        self.host_edit.setText(self._conn.host)
        self.host_edit.setClearButtonEnabled(True)
        col_host.addWidget(self.host_edit)
        hp_row.addLayout(col_host, 3)

        col_port = QVBoxLayout()
        col_port.addWidget(BodyLabel("端口"))
        self.port_edit = LineEdit()
        self.port_edit.setPlaceholderText("3306")
        self.port_edit.setText(str(self._conn.port))
        col_port.addWidget(self.port_edit)
        hp_row.addLayout(col_port, 1)
        form.addLayout(hp_row)

        form.addWidget(BodyLabel("用户名"))
        self.user_edit = LineEdit()
        self.user_edit.setPlaceholderText("root")
        self.user_edit.setText(self._conn.user)
        self.user_edit.setClearButtonEnabled(True)
        form.addWidget(self.user_edit)

        form.addWidget(BodyLabel("密码"))
        self.pwd_edit = LineEdit()
        self.pwd_edit.setPlaceholderText("输入密码")
        self.pwd_edit.setEchoMode(LineEdit.Password)
        self.pwd_edit.setText(self._conn.password)
        form.addWidget(self.pwd_edit)

        form.addWidget(BodyLabel("数据库"))
        db_row = QHBoxLayout()
        db_row.setSpacing(8)
        self.db_combo = ComboBox()
        self.db_combo.setPlaceholderText("点击「获取」拉取数据库列表")
        if self._conn.database:
            self.db_combo.setCurrentText(self._conn.database)
        db_row.addWidget(self.db_combo, 1)

        self.fetch_btn = PrimaryPushButton("获取")
        self.fetch_btn.setFixedWidth(72)
        self.fetch_btn.setStyleSheet(theme.primary_button_qss())
        self.fetch_btn.clicked.connect(self._on_fetch)
        db_row.addWidget(self.fetch_btn)
        form.addLayout(db_row)

        self.fetch_status = CaptionLabel("")
        form.addWidget(self.fetch_status)

        for editor in (self.name_edit, self.host_edit, self.port_edit, self.user_edit, self.pwd_edit, self.db_combo):
            editor.setFixedHeight(34)

        self.textLayout.addLayout(form)

    def _on_fetch(self):
        host = self.host_edit.text().strip()
        port_str = self.port_edit.text().strip()
        user = self.user_edit.text().strip()
        pwd = self.pwd_edit.text().strip()

        if not host:
            InfoBar.warning("提示", "请先填写主机地址", parent=self)
            return
        if not user:
            InfoBar.warning("提示", "请先填写用户名", parent=self)
            return

        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("…")
        self.fetch_status.setText("正在连接服务器…")
        theme.set_label_color(self.fetch_status, theme.TEXT_SUBTLE)
        QApplication.processEvents()

        ok, result = self.service.fetch_databases(host, int(port_str or 3306), user, pwd)

        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("获取")

        if ok:
            self.db_combo.clear()
            self.db_combo.addItems(result)
            self.fetch_status.setText(f"找到 {len(result)} 个数据库")
            theme.set_label_color(self.fetch_status, theme.SUCCESS)
        else:
            self.fetch_status.setText(f"连接失败: {result}")
            theme.set_label_color(self.fetch_status, theme.DANGER)

    def validate(self):
        if not self.host_edit.text().strip():
            InfoBar.warning("提示", "主机地址不能为空", parent=self)
            return False
        try:
            int(self.port_edit.text().strip() or 3306)
        except ValueError:
            InfoBar.warning("提示", "端口必须是数字", parent=self)
            return False
        return True

    def accept(self):
        if not self.validate():
            return
        host = self.host_edit.text().strip()
        self.result = ConnectionConfig(
            name=self.name_edit.text().strip() or host,
            host=host,
            port=int(self.port_edit.text().strip() or 3306),
            user=self.user_edit.text().strip(),
            password=self.pwd_edit.text().strip(),
            database=self.db_combo.currentText().strip(),
            enabled=self._conn.enabled,
        )
        super().accept()


# ═══════════════════════════════════════════════════════════════
#  Execution Select Dialog
# ═══════════════════════════════════════════════════════════════
class ExecSelectDialog(Dialog):
    def __init__(self, parent, connections: list):
        super().__init__("选择执行目标", "", parent)
        self.contentLabel.hide()
        self.setMinimumWidth(540)
        self.yesButton.setText("执行")
        self.cancelButton.setText("取消")
        self.selected = []
        self._connections = connections
        self._checks = []
        self._build()
        self.setFixedSize(max(self.sizeHint().width(), 540), min(max(self.sizeHint().height(), 440), 680))

    def _build(self):
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        title = BodyLabel("本次执行会按顺序发送到所选连接")
        hdr.addWidget(title)
        hdr.addStretch()
        self._count_label = SubtitleLabel("")
        hdr.addWidget(self._count_label)
        self.textLayout.addLayout(hdr)
        self.textLayout.addSpacing(8)

        self._sel_all = CheckBox("全选")
        self._sel_all.setChecked(True)
        self._sel_all.stateChanged.connect(self._on_select_all)
        self.textLayout.addWidget(self._sel_all)
        self.textLayout.addSpacing(8)

        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_lay = QVBoxLayout(scroll_widget)
        scroll_lay.setContentsMargins(0, 0, 8, 0)
        scroll_lay.setSpacing(6)

        for i, conn in enumerate(self._connections):
            card = SimpleCardWidget()
            card.setCursor(Qt.PointingHandCursor)
            card.setStyleSheet(f"""
                SimpleCardWidget {{
                    background: {theme.SURFACE};
                    border: 1px solid {theme.BORDER};
                    border-radius: 10px;
                }}
                SimpleCardWidget:hover {{
                    background: {theme.SURFACE_SUBTLE};
                    border-color: {theme.PRIMARY_BORDER};
                }}
            """)
            card_lay = QHBoxLayout(card)
            card_lay.setContentsMargins(14, 10, 14, 10)
            card_lay.setSpacing(10)

            cb = CheckBox()
            cb.setChecked(True)
            cb.stateChanged.connect(self._update_count)
            card_lay.addWidget(cb)
            self._checks.append(cb)

            info_col = QVBoxLayout()
            info_col.setSpacing(2)
            name = BodyLabel(conn.name or conn.host)
            info_col.addWidget(name)
            sub = CaptionLabel(f"{conn.host}:{conn.port}  /  {conn.database or '-'}")
            theme.set_label_color(sub, theme.TEXT_MUTED)
            info_col.addWidget(sub)
            card_lay.addLayout(info_col, 1)

            def make_handler(_cb):
                return lambda e: _cb.setChecked(not _cb.isChecked())
            card.mousePressEvent = make_handler(cb)

            scroll_lay.addWidget(card)

        scroll_lay.addStretch()
        scroll.setWidget(scroll_widget)
        scroll.setMinimumHeight(280)
        self.textLayout.addWidget(scroll, 1)

        self._update_count()

    def _on_select_all(self, state):
        for cb in self._checks:
            cb.setChecked(bool(state))

    def _update_count(self):
        total = len(self._checks)
        checked = sum(1 for cb in self._checks if cb.isChecked())
        self._count_label.setText(f"已选 {checked} / {total}")
        theme.set_label_color(self._count_label, theme.PRIMARY if checked else theme.TEXT_SUBTLE)
        if checked > 0:
            self.yesButton.setText(f"执行 ({checked})")
            self.yesButton.setEnabled(True)
        else:
            self.yesButton.setText("执行")
            self.yesButton.setEnabled(False)

    def accept(self):
        self.selected = [i for i, cb in enumerate(self._checks) if cb.isChecked()]
        super().accept()


# ═══════════════════════════════════════════════════════════════
#  Connection Card
# ═══════════════════════════════════════════════════════════════
class ConnCard(CardWidget):
    def __init__(self, conn: ConnectionConfig, index: int, on_menu):
        super().__init__()
        self.setObjectName("connCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(68)
        self.setStyleSheet(f"""
            #connCard {{
                background: {theme.SURFACE};
                border: 1px solid {theme.SIDEBAR_BORDER};
                border-radius: 8px;
            }}
            #connCard:hover {{
                background: {theme.SIDEBAR_SURFACE};
                border-color: {theme.PRIMARY_BORDER};
            }}
        """)
        self._index = index
        self._on_menu = on_menu

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 8, 9)
        lay.setSpacing(9)

        dot = QLabel()
        dot.setFixedSize(8, 8)
        if conn.last_test_ok is False:
            dot_color = theme.DANGER
        elif conn.last_test_ok is True:
            dot_color = theme.SUCCESS
        elif conn.enabled:
            dot_color = theme.SUCCESS
        else:
            dot_color = "#cbd5e1"
        dot.setStyleSheet(f"background: {dot_color}; border-radius: 4px;")
        lay.addWidget(dot, 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(4)
        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        name = BodyLabel(conn.name or conn.host)
        name_color = theme.TEXT_PRIMARY if conn.enabled else theme.TEXT_MUTED
        if conn.last_test_ok is False:
            name_color = theme.DANGER
        theme.set_label_color(name, name_color)
        top_row.addWidget(name, 1)
        if conn.last_test_ok is False:
            status = CaptionLabel("失败")
            theme.set_label_color(status, theme.DANGER)
        elif conn.last_test_ok is True:
            status = CaptionLabel("启用")
            theme.set_label_color(status, theme.SUCCESS)
        elif conn.enabled:
            status = CaptionLabel("启用")
            theme.set_label_color(status, theme.SUCCESS)
        else:
            status = CaptionLabel("停用")
            theme.set_label_color(status, theme.TEXT_SUBTLE)
        top_row.addWidget(status)
        col.addLayout(top_row)
        sub = CaptionLabel(f"{conn.host}:{conn.port} · {conn.database or '未选择数据库'}")
        theme.set_label_color(sub, theme.TEXT_MUTED)
        col.addWidget(sub)
        lay.addLayout(col, 1)

        menu_btn = TransparentPushButton("⋯")
        menu_btn.setFixedSize(32, 32)
        menu_btn.setStyleSheet(f"""
            TransparentPushButton {{ color: {theme.TEXT_MUTED}; border-radius: 10px; }}
            TransparentPushButton:hover {{ background: {theme.PRIMARY_SOFT}; color: {theme.PRIMARY}; }}
        """)
        menu_btn.clicked.connect(lambda: self._on_menu(self._index))
        lay.addWidget(menu_btn)

    def contextMenuEvent(self, e):
        self._on_menu(self._index)


# ═══════════════════════════════════════════════════════════════
#  Main Window
# ═══════════════════════════════════════════════════════════════
class MainWindow(FramelessWindow):
    def __init__(self):
        super().__init__()
        self.preferences = PreferenceManager()
        theme.apply_theme_color(self.preferences.theme_color())
        setThemeColor(theme.PRIMARY)
        self.setWindowTitle("SQL 批量执行器")
        self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.app_title_bar = AppTitleBar(self)
        self.setTitleBar(self.app_title_bar)
        self.resize(1320, 840)
        self.setMinimumSize(960, 640)

        self.service = ConnectionService()
        self.results = []
        self._tab_buttons = []
        self._current_tab = 0
        self._threads = []
        self._root_lay = None
        self._current_worker = None

        self._build()
        self._restore_window_geometry()

    def _restore_window_geometry(self):
        geom = self.preferences.window_geometry()
        if geom:
            try:
                self.restoreGeometry(bytes.fromhex(geom))
                # Validate restored geometry is on screen
                screen = QApplication.primaryScreen()
                if screen and not screen.availableGeometry().intersects(self.geometry()):
                    self.resize(1320, 840)
            except Exception:
                pass

    def _save_window_geometry(self):
        geom = self.saveGeometry().toHex().data().decode('ascii')
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
        pixmap.fill(Qt.transparent)
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
            InfoBar.warning("稍后切换", "当前有任务正在运行，完成后再切换主题色。",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)
            return

        sql_text = self.sql_input.toPlainText() if hasattr(self, "sql_input") else ""
        results = list(self.results)
        search_text = self.search_edit.text() if hasattr(self, "search_edit") else ""
        continue_on_error = (
            self.continue_on_error_check.isChecked()
            if hasattr(self, "continue_on_error_check")
            else False
        )

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

    def _build(self):
        central = QWidget()
        central.setObjectName("appRoot")
        central.setStyleSheet(f"""
            #appRoot {{
                background: {theme.APP_BACKGROUND};
            }}
            QWidget {{
                font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
                color: {theme.TEXT_PRIMARY};
            }}
            QScrollBar:vertical {{
                width: 10px;
                background: transparent;
                margin: 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: #cbd5e1;
                border-radius: 5px;
                min-height: 32px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #94a3b8;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        if self._root_lay is None:
            self._root_lay = QVBoxLayout(self)
            self._root_lay.setContentsMargins(0, self.titleBar.height(), 0, 0)
            self._root_lay.setSpacing(0)
        else:
            while self._root_lay.count():
                item = self._root_lay.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        self._root_lay.addWidget(central)
        main_lay = QHBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setObjectName("sidePanel")
        sidebar.setStyleSheet(f"""
            #sidePanel {{
                background: {theme.APP_CHROME};
                border-right: 1px solid {theme.SIDEBAR_BORDER};
            }}
        """)
        sidebar.setFixedWidth(300)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(16, 18, 16, 16)
        sb_lay.setSpacing(0)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        brand_badge = QLabel("SQL")
        brand_badge.setAlignment(Qt.AlignCenter)
        brand_badge.setFixedSize(44, 36)
        brand_badge.setStyleSheet(f"""
            color: {theme.PRIMARY};
            background: {theme.PRIMARY_SOFT};
            border: 1px solid {theme.STRONG_BORDER};
            border-radius: 10px;
            font-size: 13px;
            font-weight: 700;
        """)
        logo_row.addWidget(brand_badge)
        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        sql_lbl = QLabel("SQL 批量执行器")
        sql_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {theme.TEXT_PRIMARY}; background: transparent; border: none;")
        brand_col.addWidget(sql_lbl)
        sub_lbl = QLabel("Batch Executor")
        sub_lbl.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; background: transparent; border: none;")
        brand_col.addWidget(sub_lbl)
        logo_row.addLayout(brand_col)
        logo_row.addStretch()
        sb_lay.addLayout(logo_row)
        sb_lay.addSpacing(16)

        overview_card = QFrame()
        overview_card.setObjectName("overviewCard")
        overview_card.setStyleSheet(f"""
            #overviewCard {{
                background: {theme.SIDEBAR_SURFACE};
                border: 1px solid {theme.SIDEBAR_BORDER};
                border-radius: 8px;
            }}
        """)
        overview_lay = QHBoxLayout(overview_card)
        overview_lay.setContentsMargins(12, 10, 12, 10)
        overview_lay.setSpacing(10)
        overview_title = BodyLabel("连接")
        overview_lay.addWidget(overview_title)
        overview_lay.addStretch()
        self.sidebar_count_label = CaptionLabel("0 个")
        theme.set_label_color(self.sidebar_count_label, theme.TEXT_MUTED)
        overview_lay.addWidget(self.sidebar_count_label)
        self.sidebar_enabled_label = CaptionLabel("0 启用")
        theme.set_label_color(self.sidebar_enabled_label, theme.PRIMARY)
        overview_lay.addWidget(self.sidebar_enabled_label)
        sb_lay.addWidget(overview_card)
        sb_lay.addSpacing(18)

        sec_row = QHBoxLayout()
        sec_lbl = QLabel("数据库连接")
        sec_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {theme.TEXT_PRIMARY}; background: transparent; border: none;")
        sec_row.addWidget(sec_lbl)
        sec_row.addStretch()
        add_btn = PrimaryPushButton("+ 添加")
        add_btn.setFixedSize(84, 34)
        add_btn.setStyleSheet(theme.primary_button_qss())
        add_btn.clicked.connect(self._on_add)
        sec_row.addWidget(add_btn)
        sb_lay.addLayout(sec_row)
        sb_lay.addSpacing(8)

        self.search_edit = LineEdit()
        self.search_edit.setPlaceholderText("搜索连接…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedHeight(32)
        self.search_edit.textChanged.connect(self._on_conn_search)
        sb_lay.addWidget(self.search_edit)
        sb_lay.addSpacing(8)

        self.conn_scroll = QScrollArea()
        self.conn_scroll.setWidgetResizable(True)
        self.conn_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.conn_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.conn_widget = QWidget()
        self.conn_widget.setStyleSheet("background: transparent;")
        self.conn_layout = QVBoxLayout(self.conn_widget)
        self.conn_layout.setContentsMargins(0, 0, 0, 0)
        self.conn_layout.setSpacing(8)
        self.conn_layout.addStretch()
        self.conn_scroll.setWidget(self.conn_widget)
        sb_lay.addWidget(self.conn_scroll, 1)

        main_lay.addWidget(sidebar)

        # ── Right Content ──
        right = QWidget()
        right.setObjectName("rightContent")
        right.setStyleSheet(f"""
            #rightContent {{
                background: {theme.APP_BACKGROUND};
                border: none;
            }}
        """)
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setStyleSheet(f"""
            #topBar {{
                background: {theme.APP_CHROME};
                border-bottom: 1px solid {theme.BORDER};
            }}
        """)
        top_bar.setFixedHeight(64)
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(24, 0, 24, 0)
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        ttl = QLabel("SQL 执行")
        ttl.setStyleSheet(f"""
            color: {theme.TEXT_PRIMARY};
            background: transparent;
            font-size: 18px;
            font-weight: 700;
        """)
        title_col.addWidget(ttl)
        hint = QLabel("选择目标连接后执行，结果在下方查看")
        hint.setStyleSheet(f"""
            color: {theme.TEXT_MUTED};
            background: transparent;
            font-size: 12px;
        """)
        title_col.addWidget(hint)
        tb_lay.addLayout(title_col)
        tb_lay.addStretch()
        self.theme_btn = PushButton("主题色")
        self.theme_btn.setFixedSize(78, 30)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setStyleSheet(self._theme_button_style())
        self.theme_btn.clicked.connect(self._show_theme_menu)
        tb_lay.addWidget(self.theme_btn)
        self.summary_label = QLabel("")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setFixedHeight(28)
        self.summary_label.setMinimumWidth(132)
        self.summary_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_MUTED};
                background: {theme.SURFACE};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 12px;
            }}
        """)
        tb_lay.addWidget(self.summary_label)
        right_lay.addWidget(top_bar)

        editor_card = SimpleCardWidget()
        editor_card.setObjectName("editorCard")
        editor_card.setStyleSheet(f"""
            #editorCard {{
                background: {theme.SURFACE};
                border: 1px solid {theme.BORDER};
                border-radius: 12px;
            }}
        """)
        ec_lay = QVBoxLayout(editor_card)
        ec_lay.setContentsMargins(18, 14, 18, 16)
        ec_lay.setSpacing(10)

        ed_hdr = QHBoxLayout()
        ed_hdr.setSpacing(10)
        ed_title_col = QVBoxLayout()
        ed_title_col.setSpacing(2)
        ed_title = QLabel("SQL")
        ed_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {theme.TEXT_PRIMARY}; background: transparent;")
        ed_title_col.addWidget(ed_title)
        ed_caption = CaptionLabel("执行前选择目标连接")
        theme.set_label_color(ed_caption, theme.TEXT_MUTED)
        ed_title_col.addWidget(ed_caption)
        ed_hdr.addLayout(ed_title_col)
        ed_hdr.addStretch()
        self.continue_on_error_check = CheckBox("出错继续")
        self.continue_on_error_check.setFixedHeight(32)
        self.continue_on_error_check.setToolTip("单条 SQL 失败后继续执行后续 SQL")
        ed_hdr.addWidget(self.continue_on_error_check)
        self.exec_btn = PrimaryPushButton("批量执行")
        self.exec_btn.setFixedSize(110, 34)
        self.exec_btn.setStyleSheet(theme.primary_button_qss())
        self.exec_btn.clicked.connect(self._on_execute)
        ed_hdr.addWidget(self.exec_btn)
        ec_lay.addLayout(ed_hdr)

        self.sql_input = PlainTextEdit()
        self.sql_input.setPlaceholderText("输入要执行的 SQL 语句…")
        self.sql_input.setMinimumHeight(150)
        self.sql_input.setMaximumHeight(220)
        self.sql_input.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {theme.EDITOR_BG};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-family: {theme.EDITOR_FONT};
                font-size: 14px;
                color: {theme.EDITOR_TEXT};
                selection-background-color: {theme.SELECTED_BG};
            }}
            QPlainTextEdit:focus {{
                border: 1px solid {theme.PRIMARY};
                background: {theme.EDITOR_PANEL};
            }}
        """)
        ec_lay.addWidget(self.sql_input)

        editor_wrap = QFrame()
        editor_wrap.setStyleSheet(f"background: transparent; border: none;")
        editor_wrap_lay = QVBoxLayout(editor_wrap)
        editor_wrap_lay.setContentsMargins(20, 16, 20, 12)
        editor_wrap_lay.addWidget(editor_card)
        right_lay.addWidget(editor_wrap)

        self.progress_frame = QFrame()
        self.progress_frame.setStyleSheet(f"""
            QFrame {{
                background: {theme.APP_CHROME};
                border-top: 1px solid {theme.BORDER};
                border-bottom: 1px solid {theme.BORDER};
            }}
        """)
        pf_lay = QHBoxLayout(self.progress_frame)
        pf_lay.setContentsMargins(28, 10, 28, 10)
        pf_lay.setSpacing(12)
        self.progress = ProgressBar()
        pf_lay.addWidget(self.progress, 1)
        self.cancel_btn = TransparentPushButton("取消")
        self.cancel_btn.setFixedSize(60, 28)
        self.cancel_btn.setStyleSheet(f"""
            TransparentPushButton {{ color: {theme.DANGER}; border-radius: 6px; }}
            TransparentPushButton:hover {{ background: {theme.DANGER_SOFT}; }}
        """)
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(self._on_cancel_execute)
        pf_lay.addWidget(self.cancel_btn)
        self.status_label = CaptionLabel("就绪")
        theme.set_label_color(self.status_label, theme.TEXT_SUBTLE)
        pf_lay.addWidget(self.status_label)
        self.progress_frame.hide()
        right_lay.addWidget(self.progress_frame)

        self.result_stack = QStackedWidget()
        self.result_stack.setStyleSheet("background: transparent; border: none;")

        empty = QWidget()
        empty.setStyleSheet("background: transparent;")
        empty_lay = QVBoxLayout(empty)
        empty_lay.setContentsMargins(20, 16, 20, 0)
        empty_lay.setSpacing(0)
        empty_lay.setAlignment(Qt.AlignTop)
        empty_card = SimpleCardWidget()
        empty_card.setObjectName("emptyCard")
        empty_card.setMinimumHeight(118)
        empty_card.setMaximumHeight(140)
        empty_card.setStyleSheet(f"""
            #emptyCard {{
                background: {theme.SURFACE};
                border: 1px solid {theme.BORDER};
                border-radius: 12px;
            }}
        """)
        empty_card_lay = QVBoxLayout(empty_card)
        empty_card_lay.setContentsMargins(18, 16, 18, 16)
        empty_card_lay.setAlignment(Qt.AlignVCenter)
        empty_card_lay.setSpacing(6)
        txt = QLabel("暂无执行结果")
        txt.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {theme.TEXT_PRIMARY}; background: transparent;")
        txt.setAlignment(Qt.AlignLeft)
        empty_card_lay.addWidget(txt)
        desc = QLabel("输入 SQL 并执行后，这里会显示各连接的执行结果。")
        desc.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED}; background: transparent;")
        desc.setAlignment(Qt.AlignLeft)
        empty_card_lay.addWidget(desc)
        empty_lay.addWidget(empty_card)
        empty_lay.addStretch()
        self.result_stack.addWidget(empty)

        self._results_page = QWidget()
        self._results_lay = QVBoxLayout(self._results_page)
        self._results_lay.setContentsMargins(0, 0, 0, 0)
        self._results_lay.setSpacing(0)
        self.result_stack.addWidget(self._results_page)

        right_lay.addWidget(self.result_stack, 1)
        main_lay.addWidget(right, 1)

        self._refresh_conn_list()

    # ── Connection List ─────────────────────────────────────────
    def _update_summary(self):
        total = len(self.service.connections)
        enabled = len(self.service.enabled_connections())
        self.summary_label.setText(f"{enabled} 个启用 / {total} 个连接")
        self.sidebar_count_label.setText(f"{total} 个")
        self.sidebar_enabled_label.setText(f"{enabled} 启用")

    def _refresh_conn_list(self, filter_text: str = ""):
        while self.conn_layout.count() > 1:
            item = self.conn_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._update_summary()
        conns = self.service.connections
        if not conns:
            lbl = BodyLabel("暂无连接\n点击「+ 添加」开始")
            lbl.setAlignment(Qt.AlignCenter)
            theme.set_label_color(lbl, "#94a3b8")
            lbl.setStyleSheet("padding: 48px 0; background: transparent; line-height: 1.5;")
            self.conn_layout.insertWidget(0, lbl)
            return

        keyword = filter_text.lower().strip()
        for i, conn in enumerate(conns):
            if keyword and keyword not in conn.name.lower() and keyword not in conn.host.lower() and keyword not in (conn.database or "").lower():
                continue
            card = ConnCard(conn, i, self._show_conn_menu)
            self.conn_layout.insertWidget(self.conn_layout.count() - 1, card)

    def _on_conn_search(self, text: str):
        self._refresh_conn_list(text)

    def _show_conn_menu(self, index: int):
        conn = self.service.connections[index]
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {theme.SIDEBAR_SURFACE};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.SIDEBAR_BORDER};
                border-radius: 10px;
                padding: 4px; font-size: 12px;
            }}
            QMenu::item {{ padding: 8px 24px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {theme.PRIMARY_SOFT}; color: {theme.PRIMARY}; }}
            QMenu::item#deleteAction {{ color: {theme.DANGER}; }}
            QMenu::item#deleteAction:selected {{ background: {theme.DANGER_SOFT}; color: {theme.DANGER}; }}
            QMenu::separator {{ height: 1px; background: {theme.SIDEBAR_BORDER}; margin: 4px 8px; }}
        """)
        menu.addAction("编辑连接", lambda: self._on_edit(index))
        menu.addAction("测试连接", lambda: self._on_test(index))
        toggle_text = "禁用" if conn.enabled else "启用"
        menu.addAction(toggle_text, lambda: self._on_toggle(index))
        menu.addSeparator()
        del_action = menu.addAction("删除", lambda: self._on_remove(index))
        del_action.setObjectName("deleteAction")
        menu.exec_(self.cursor().pos())

    # ── Actions ─────────────────────────────────────────────────
    def _on_add(self):
        dlg = ConnDialog(self, ConnectionConfig(), "添加连接", self.service)
        if dlg.exec_() == QDialog.Accepted and dlg.result:
            self.service.add(dlg.result)
            self._refresh_conn_list()
            InfoBar.success("成功", f"已添加连接 \"{dlg.result.name}\"",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _on_edit(self, index: int):
        dlg = ConnDialog(self, self.service.connections[index], "编辑连接", self.service)
        if dlg.exec_() == QDialog.Accepted and dlg.result:
            self.service.update(index, dlg.result)
            self._refresh_conn_list()
            InfoBar.success("成功", f"已更新连接 \"{dlg.result.name}\"",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _on_test(self, index: int):
        conn = self.service.connections[index]
        self.status_label.setText(f"正在测试: {conn.name}…")
        theme.set_label_color(self.status_label, theme.TEXT_SUBTLE)
        self.progress.setValue(0)
        self.progress.setMaximum(0)
        self.progress_frame.show()

        thread = QThread(self)
        worker = TestConnectionWorker(self.service.database, conn)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_test_finished)
        worker.finished.connect(self._on_test_thread_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._track_thread(thread)
        thread.start()

    def _on_test_finished(self, ok: bool, msg: str, conn_name: str):
        if ok:
            InfoBar.success("连接成功", f"{conn_name}: {msg}",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.error("连接失败", f"{conn_name}: {msg}",
                          parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _on_test_thread_finished(self, ok: bool, msg: str, conn_name: str):
        # Update connection test status and refresh UI
        for i, conn in enumerate(self.service.connections):
            if (conn.name or conn.host) == conn_name:
                self.service.config.connections[i].last_test_ok = ok
                self.service.config.save()
                self._refresh_conn_list()
                break
        self.progress.setMaximum(1)
        self.progress.setValue(1)
        self.progress_frame.hide()

    def _on_toggle(self, index: int):
        self.service.toggle(index)
        self._refresh_conn_list()

    def _on_remove(self, index: int):
        conn = self.service.connections[index]
        w = MessageBox("确认删除", f"确定要删除连接 \"{conn.name}\" 吗？", self)
        if w.exec_() == Dialog.Accepted:
            self.service.remove(index)
            self._refresh_conn_list()
            InfoBar.success("成功", "已删除连接",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)

    # ── Execute ─────────────────────────────────────────────────
    def _on_execute(self):
        sql = self.sql_input.toPlainText().strip()
        if not sql:
            InfoBar.warning("提示", "请输入 SQL 语句",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)
            return
        statements = self.service.split_sql(sql)
        if not statements:
            InfoBar.warning("提示", "没有可执行 SQL",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)
            return
        enabled = self.service.enabled_connections()
        if not enabled:
            InfoBar.warning("提示", "没有可用的数据库连接",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)
            return

        dlg = ExecSelectDialog(self, enabled)
        if dlg.exec_() != Dialog.Accepted or not dlg.selected:
            return

        targets = self.service.resolve_targets(enabled, dlg.selected)
        if not self._confirm_dangerous_sql(sql, len(targets), len(statements)):
            return
        total = len(targets) * len(statements)
        continue_on_error = self.continue_on_error_check.isChecked()

        self.exec_btn.setEnabled(False)
        self.exec_btn.setText("执行中…")
        self.progress.setValue(0)
        self.progress.setMaximum(total)
        self.progress_frame.show()
        self.cancel_btn.show()
        self.results = []

        thread = QThread(self)
        worker = SqlExecutionWorker(self.service.database, targets, sql, continue_on_error)
        worker.moveToThread(thread)
        self._current_worker = worker
        thread.started.connect(worker.run)
        worker.status_changed.connect(self._on_execute_status_changed)
        worker.progress_changed.connect(self._on_execute_progress_changed)
        worker.finished.connect(lambda results, executed_sql=sql: self._on_execute_finished(results, executed_sql))
        worker.cancelled.connect(self._on_execute_cancelled)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: setattr(self, '_current_worker', None))
        self._track_thread(thread)
        thread.start()

    def _confirm_dangerous_sql(self, sql: str, target_count: int, statement_count: int) -> bool:
        dangerous = self.service.dangerous_statements(sql)
        if not dangerous:
            return True

        operations = sorted({operation for _, item_operations in dangerous for operation in item_operations})
        detail_lines = [
            f"SQL {statement.index}（第 {statement.start_line} 行）：{', '.join(item_operations)}"
            for statement, item_operations in dangerous[:5]
        ]
        if len(dangerous) > 5:
            detail_lines.append(f"另有 {len(dangerous) - 5} 条危险语句")

        warning = MessageBox(
            "危险 SQL 确认",
            f"检测到危险操作：{', '.join(operations)}\n\n"
            + "\n".join(detail_lines)
            + "\n\n"
            f"本次会向 {target_count} 个连接发送 {statement_count} 条 SQL。"
            "请确认你已经备份或确认影响范围。",
            self,
        )
        warning.setWindowTitle("⚠️ 危险 SQL 确认")
        warning.yesButton.setText("确认执行")
        warning.yesButton.setStyleSheet(f"""
            QPushButton {{
                background: {theme.DANGER};
                color: white;
                border-radius: 7px;
                font-weight: 600;
                padding: 6px 20px;
            }}
            QPushButton:hover {{ background: #b91c1c; }}
        """)
        warning.cancelButton.setText("取消")
        return warning.exec_() == Dialog.Accepted

    def _on_cancel_execute(self):
        if self._current_worker:
            self._current_worker.cancel()

    def _on_execute_status_changed(self, text: str):
        self.status_label.setText(text)
        theme.set_label_color(self.status_label, theme.TEXT_SUBTLE)

    def _on_execute_progress_changed(self, current: int, total: int, result):
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def _on_execute_cancelled(self):
        self.progress.setMaximum(1)
        self.progress.setValue(self.progress.maximum())
        self.cancel_btn.hide()
        self.exec_btn.setEnabled(True)
        self.exec_btn.setText("批量执行")
        self.status_label.setText("已取消")
        theme.set_label_color(self.status_label, theme.WARNING)
        InfoBar.warning("已取消", "执行被用户取消", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _on_execute_finished(self, results: list[ExecutionResult], sql: str):
        self.results = results
        self.exec_btn.setEnabled(True)
        self.exec_btn.setText("批量执行")
        self.cancel_btn.hide()
        self.progress.setMaximum(1)
        self.progress.setValue(self.progress.maximum())
        summary = self.service.summarize(self.results)
        try:
            self.service.record_history(sql, self.results)
            history_note = "，已记录历史"
        except Exception as error:
            history_note = ""
            InfoBar.warning("历史记录失败", str(error), parent=self, position=InfoBarPosition.TOP_RIGHT)
        cancelled = any(result.cancelled for result in self.results)
        statement_note = ""
        if summary.statements_total:
            statement_note = f"，语句 {summary.statements_success}/{summary.statements_total}"
        if cancelled:
            self.status_label.setText(f"已取消: {summary.success}/{summary.total} 成功")
            theme.set_label_color(self.status_label, theme.WARNING)
            InfoBar.warning("已取消", f"已保留当前执行结果{history_note}",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)
        elif summary.success == summary.total:
            self.status_label.setText(f"完成: {summary.success}/{summary.total} 成功")
            theme.set_label_color(self.status_label, theme.SUCCESS)
            InfoBar.success("执行完成", f"{summary.success}/{summary.total} 个连接执行成功{statement_note}{history_note}",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)
        else:
            self.status_label.setText(f"完成: {summary.success}/{summary.total} 成功")
            theme.set_label_color(self.status_label, theme.DANGER)
            InfoBar.error("执行完成", f"{summary.failed} 个连接执行失败{statement_note}",
                          parent=self, position=InfoBarPosition.TOP_RIGHT)
        self._show_results()

    # ── Results ─────────────────────────────────────────────────
    def _show_results(self):
        while self._results_lay.count():
            item = self._results_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._tab_buttons.clear()
        self._current_tab = 0
        self._page_cache = {}
        self._content_stack = None

        if not self.results:
            self.result_stack.setCurrentIndex(0)
            return

        self.result_stack.setCurrentIndex(1)

        summary = self.service.summarize(self.results)

        summary_bar = QFrame()
        summary_bar.setStyleSheet(f"background: {theme.SURFACE}; border-bottom: 1px solid {theme.BORDER};")
        summary_lay = QHBoxLayout(summary_bar)
        summary_lay.setContentsMargins(20, 10, 20, 10)
        summary_lay.setSpacing(12)
        summary_title = SubtitleLabel("执行结果")
        summary_lay.addWidget(summary_title)
        total_label = CaptionLabel(f"目标 {summary.total}")
        theme.set_label_color(total_label, theme.TEXT_MUTED)
        summary_lay.addWidget(total_label)
        success_label = CaptionLabel(f"成功 {summary.success}")
        theme.set_label_color(success_label, theme.SUCCESS)
        summary_lay.addWidget(success_label)
        if summary.failed:
            failed_label = CaptionLabel(f"失败 {summary.failed}")
            theme.set_label_color(failed_label, theme.DANGER)
            summary_lay.addWidget(failed_label)
        if summary.statements_total:
            statement_label = CaptionLabel(f"语句 {summary.statements_success}/{summary.statements_total}")
            theme.set_label_color(
                statement_label,
                theme.SUCCESS if summary.statements_success == summary.statements_total else theme.WARNING,
            )
            summary_lay.addWidget(statement_label)
        summary_lay.addStretch()
        elapsed_label = CaptionLabel(f"累计耗时 {summary.elapsed_ms:.0f}ms")
        theme.set_label_color(elapsed_label, theme.TEXT_MUTED)
        summary_lay.addWidget(elapsed_label)
        self._results_lay.addWidget(summary_bar)

        tab_bar = QFrame()
        tab_bar.setStyleSheet(f"background: {theme.SURFACE}; border-bottom: 1px solid {theme.BORDER};")
        tab_lay = QHBoxLayout(tab_bar)
        tab_lay.setContentsMargins(12, 0, 0, 0)
        tab_lay.setSpacing(0)

        for i, r in enumerate(self.results):
            icon = "…" if r.cancelled else ("✓" if r.success else "✗")
            btn = PushButton(f"  {icon} {r.connection_name}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setStyleSheet(self._tab_style(i == 0))
            btn.clicked.connect(lambda checked, idx=i: self._select_tab(idx))
            tab_lay.addWidget(btn)
            self._tab_buttons.append(btn)

        tab_lay.addStretch()
        self._results_lay.addWidget(tab_bar)

        self._content_stack = QStackedWidget()
        self._content_stack.setStyleSheet("background: transparent; border: none;")
        # Add placeholder at index 0
        placeholder = QWidget()
        placeholder.setStyleSheet("background: transparent;")
        self._content_stack.addWidget(placeholder)
        self._page_cache = {}
        self._results_lay.addWidget(self._content_stack, 1)

        # Select first tab to load its content lazily
        if self.results:
            self._select_tab(0)

    def _tab_style(self, active: bool):
        if active:
            return f"""
                QPushButton {{
                    background: transparent; border: none;
                    border-bottom: 2px solid {theme.PRIMARY};
                    color: {theme.PRIMARY}; font-weight: bold;
                    padding: 0 16px; font-size: 13px;
                }}
                QPushButton:hover {{ background: {theme.PRIMARY_SOFT}; }}
            """
        return f"""
            QPushButton {{
                background: transparent; border: none;
                border-bottom: 2px solid transparent;
                color: {theme.TEXT_MUTED}; font-weight: normal;
                padding: 0 16px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {theme.SURFACE_SUBTLE}; }}
        """

    def _select_tab(self, index: int):
        # Build page content if not cached (regardless of current tab)
        if index not in self._page_cache:
            r = self.results[index]
            page = self._build_result_page(r)
            self._content_stack.addWidget(page)
            self._page_cache[index] = page

        # Update tab styles only if tab actually changed
        if index != self._current_tab and self._tab_buttons:
            self._tab_buttons[self._current_tab].setStyleSheet(self._tab_style(False))
            self._tab_buttons[index].setStyleSheet(self._tab_style(True))

        self._content_stack.setCurrentIndex(index + 1)  # +1 because placeholder is at 0
        self._current_tab = index

    def _copy_table_selection(self, table: 'TableWidget'):
        """Copy selected table rows to clipboard as tab-separated text."""
        selected = table.selectionModel().selectedRows()
        if not selected:
            return
        rows = sorted(set(r.row() for r in selected))
        cols = range(table.columnCount())
        lines = []
        for row in rows:
            line = "\t".join(
                table.item(row, c).text() if table.item(row, c) else ""
                for c in cols
            )
            lines.append(line)
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(lines))

    def _show_table_context_menu(self, table: 'TableWidget'):
        menu = QMenu(table)
        menu.setStyleSheet(f"""
            QMenu {{ background: {theme.SURFACE}; color: {theme.TEXT_PRIMARY};
                     border: 1px solid {theme.BORDER}; border-radius: 8px; padding: 4px; font-size: 12px; }}
            QMenu::item {{ padding: 7px 24px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {theme.PRIMARY_SOFT}; color: {theme.PRIMARY}; }}
        """)
        menu.addAction("复制选中行", lambda: self._copy_table_selection(table))
        menu.exec_(QCursor.pos())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.matches(QKeyEvent.Copy):
            if isinstance(obj, TableWidget):
                self._copy_table_selection(obj)
                return True
        return super().eventFilter(obj, event)

    def _compact_sql(self, sql: str, limit: int = 320) -> str:
        compact = " ".join(sql.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1] + "…"

    def _create_result_table(self, columns: list[str], data: list[tuple], limit: int = 2000) -> TableWidget:
        table = TableWidget()
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.setRowCount(min(len(data), limit))
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.verticalHeader().hide()
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        table.setStyleSheet(f"""
            QTableWidget {{
                background: {theme.SURFACE};
                border: 1px solid {theme.BORDER};
                border-radius: 6px;
                gridline-color: {theme.BORDER};
                selection-background-color: {theme.SELECTED_BG};
                selection-color: {theme.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background: {theme.SURFACE_SUBTLE};
                color: {theme.TEXT_MUTED};
                border: none;
                border-bottom: 1px solid {theme.BORDER};
                padding: 8px;
                font-weight: 600;
            }}
        """)

        data_batch = data[:limit]
        batch_size = 200
        for batch_start in range(0, len(data_batch), batch_size):
            batch_end = min(batch_start + batch_size, len(data_batch))
            for row_idx in range(batch_start, batch_end):
                row_data = data_batch[row_idx]
                for col_idx, val in enumerate(row_data):
                    if val is None:
                        text = "NULL"
                    elif isinstance(val, bytes):
                        text = val.decode("utf-8", errors="replace")
                    else:
                        text = str(val)
                    item = QTableWidgetItem(text)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    table.setItem(row_idx, col_idx, item)
            QApplication.processEvents()

        table.resizeColumnsToContents()
        table.installEventFilter(self)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos: self._show_table_context_menu(table))
        return table

    def _build_script_result_page(self, r: ExecutionResult):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        page_lay = QVBoxLayout(page)
        page_lay.setContentsMargins(20, 16, 20, 20)
        page_lay.setSpacing(0)

        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 8, 0)
        content_lay.setSpacing(10)

        header = QHBoxLayout()
        title = SubtitleLabel(r.connection_name)
        header.addWidget(title)
        summary = CaptionLabel(f"{r.message} · {r.duration_ms:.0f}ms")
        summary.setWordWrap(True)
        theme.set_label_color(summary, theme.SUCCESS if r.success else theme.DANGER)
        header.addWidget(summary, 1, Qt.AlignRight)
        content_lay.addLayout(header)

        for statement in r.statement_results:
            content_lay.addWidget(self._build_statement_card(statement))

        skipped = r.statements_total - len(r.statement_results)
        if skipped > 0:
            skipped_label = CaptionLabel(f"后续 {skipped} 条 SQL 未执行")
            skipped_label.setAlignment(Qt.AlignCenter)
            theme.set_label_color(skipped_label, theme.WARNING)
            content_lay.addWidget(skipped_label)

        content_lay.addStretch()
        scroll.setWidget(content)
        page_lay.addWidget(scroll, 1)
        return page

    def _build_statement_card(self, statement: StatementExecutionResult):
        card = SimpleCardWidget()
        card.setObjectName("statementResultCard")
        card.setStyleSheet(f"""
            #statementResultCard {{
                background: {theme.SURFACE};
                border: 1px solid {theme.BORDER};
                border-radius: 10px;
            }}
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(14, 12, 14, 14)
        card_lay.setSpacing(8)

        header = QHBoxLayout()
        title = SubtitleLabel(f"SQL {statement.index} · 第 {statement.start_line} 行")
        header.addWidget(title)
        header.addStretch()
        status = CaptionLabel("成功" if statement.success else "失败")
        theme.set_label_color(status, theme.SUCCESS if statement.success else theme.DANGER)
        header.addWidget(status)
        duration = CaptionLabel(f"{statement.duration_ms:.0f}ms")
        theme.set_label_color(duration, theme.TEXT_MUTED)
        header.addWidget(duration)
        card_lay.addLayout(header)

        preview = CaptionLabel(self._compact_sql(statement.sql))
        preview.setWordWrap(True)
        preview.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_MUTED};
                background: {theme.EDITOR_BG};
                border: 1px solid {theme.BORDER};
                border-radius: 6px;
                padding: 8px;
                font-family: {theme.EDITOR_FONT};
            }}
        """)
        card_lay.addWidget(preview)

        message = BodyLabel(statement.message)
        message.setWordWrap(True)
        theme.set_label_color(message, theme.SUCCESS if statement.success else theme.DANGER)
        card_lay.addWidget(message)

        if statement.columns:
            table = self._create_result_table(statement.columns, statement.data, limit=500)
            table.setMinimumHeight(150)
            table.setMaximumHeight(320)
            card_lay.addWidget(table)
            if len(statement.data) > 500:
                limit_label = CaptionLabel("仅显示前 500 行")
                theme.set_label_color(limit_label, theme.WARNING)
                card_lay.addWidget(limit_label)

        return card

    def _build_result_page(self, r: ExecutionResult):
        if r.statements_total > 1 or len(r.statement_results) > 1:
            return self._build_script_result_page(r)

        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(0)

        if r.success and r.columns:
            container = SimpleCardWidget()
            container.setObjectName("resultTableCard")
            container.setStyleSheet(f"""
                #resultTableCard {{
                    background: {theme.SURFACE};
                    border: 1px solid {theme.BORDER};
                    border-radius: 10px;
                }}
            """)
            container_lay = QVBoxLayout(container)
            container_lay.setContentsMargins(16, 12, 16, 16)
            container_lay.setSpacing(10)

            header = QHBoxLayout()
            title_col = QVBoxLayout()
            title_col.setSpacing(2)
            name = SubtitleLabel(r.connection_name)
            title_col.addWidget(name)
            info_lbl = CaptionLabel(f"{r.message} · {r.duration_ms:.0f}ms")
            theme.set_label_color(info_lbl, theme.SUCCESS)
            title_col.addWidget(info_lbl)
            header.addLayout(title_col)
            header.addStretch()
            rows_label = CaptionLabel(f"{len(r.data)} 行")
            theme.set_label_color(rows_label, theme.TEXT_MUTED)
            header.addWidget(rows_label)
            if len(r.data) > 2000:
                limit_label = CaptionLabel("仅显示前 2000 行")
                theme.set_label_color(limit_label, theme.WARNING)
                header.addWidget(limit_label)
            container_lay.addLayout(header)

            table = self._create_result_table(r.columns, r.data, limit=2000)
            container_lay.addWidget(table, 1)
            if not r.data:
                empty_note = CaptionLabel("查询成功，但没有返回数据行。")
                empty_note.setAlignment(Qt.AlignCenter)
                theme.set_label_color(empty_note, theme.TEXT_MUTED)
                container_lay.addWidget(empty_note)
            lay.addWidget(container, 1)
        else:
            color = theme.SUCCESS if r.success else theme.DANGER
            wrapper = SimpleCardWidget()
            wrapper.setObjectName("resultStatusCard")
            wrapper.setStyleSheet(f"""
                #resultStatusCard {{
                    background: {theme.SURFACE};
                    border: 1px solid {theme.BORDER};
                    border-radius: 10px;
                }}
            """)
            w_lay = QVBoxLayout(wrapper)
            w_lay.setAlignment(Qt.AlignCenter)
            w_lay.setSpacing(8)

            icon = QLabel("✓" if r.success else "✗")
            icon.setFixedSize(46, 46)
            icon.setStyleSheet(f"""
                font-size: 26px;
                font-weight: 700;
                color: {color};
                background: transparent;
            """)
            icon.setAlignment(Qt.AlignCenter)
            w_lay.addWidget(icon)

            name = SubtitleLabel(r.connection_name)
            name.setAlignment(Qt.AlignCenter)
            w_lay.addWidget(name)

            msg = BodyLabel(r.message)
            theme.set_label_color(msg, color)
            msg.setAlignment(Qt.AlignCenter)
            msg.setWordWrap(True)
            w_lay.addWidget(msg)

            dur = CaptionLabel(f"耗时: {r.duration_ms:.0f}ms")
            theme.set_label_color(dur, theme.TEXT_MUTED)
            dur.setAlignment(Qt.AlignCenter)
            w_lay.addWidget(dur)

            lay.addWidget(wrapper, 1)

        return page


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
