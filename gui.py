import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea, QStackedWidget,
    QTableWidgetItem, QAbstractItemView, QMenu, QDialog, QPushButton,
)
from PyQt5.QtCore import Qt, QEvent, QThread
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen

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

from config_manager import ConnectionConfig
from db_manager import ExecutionResult
from app_resources import APP_ICON_PATH
from services import ConnectionService
from workers import SqlExecutionWorker, TestConnectionWorker
from ui_theme import (
    APP_BACKGROUND, APP_CHROME, BORDER, DANGER, DANGER_SOFT,
    EDITOR_BG, EDITOR_FONT, EDITOR_PANEL, EDITOR_TEXT, PRIMARY,
    PRIMARY_PRESSED, PRIMARY_SOFT, SIDEBAR_BORDER, SIDEBAR_SURFACE,
    STRONG_BORDER, SUCCESS, SUCCESS_SOFT, SURFACE, SURFACE_SUBTLE,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SUBTLE, WARNING, WARNING_SOFT,
    pill_style, primary_button_qss, set_label_color,
)


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
        icon = QColor(TEXT_MUTED)

        if is_hover or is_pressed:
            if self._role == "close":
                bg = QColor("#b91c1c" if is_pressed else DANGER)
                border = bg
                icon = QColor("#ffffff")
            else:
                bg = QColor("#dbeafe" if is_pressed else "#eef4ff")
                border = QColor(0, 0, 0, 0)
                icon = QColor(PRIMARY_PRESSED if is_pressed else PRIMARY)

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
        self.appTitleLabel.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            background: transparent;
            font-size: 13px;
            font-weight: 600;
        """)
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

        self.setStyleSheet(f"""
            #appTitleBar {{
                background: {APP_CHROME};
                border-bottom: 1px solid {BORDER};
            }}
        """)
        self._update_max_button()

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
        painter.fillRect(self.rect(), QColor(APP_CHROME))
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
        set_label_color(intro, TEXT_MUTED)
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
        self.fetch_btn.setStyleSheet(primary_button_qss())
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
        set_label_color(self.fetch_status, TEXT_SUBTLE)
        QApplication.processEvents()

        ok, result = self.service.fetch_databases(host, int(port_str or 3306), user, pwd)

        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("获取")

        if ok:
            self.db_combo.clear()
            self.db_combo.addItems(result)
            self.fetch_status.setText(f"找到 {len(result)} 个数据库")
            set_label_color(self.fetch_status, SUCCESS)
        else:
            self.fetch_status.setText(f"连接失败: {result}")
            set_label_color(self.fetch_status, DANGER)

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
                    background: {SURFACE};
                    border: 1px solid {BORDER};
                    border-radius: 10px;
                }}
                SimpleCardWidget:hover {{
                    background: {SURFACE_SUBTLE};
                    border-color: #bfdbfe;
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
            set_label_color(sub, TEXT_MUTED)
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
        set_label_color(self._count_label, PRIMARY if checked else TEXT_SUBTLE)
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
                background: {SURFACE};
                border: 1px solid {SIDEBAR_BORDER};
                border-radius: 8px;
            }}
            #connCard:hover {{
                background: {SIDEBAR_SURFACE};
                border-color: #b8c2d1;
            }}
        """)
        self._index = index
        self._on_menu = on_menu

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 8, 9)
        lay.setSpacing(9)

        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {SUCCESS if conn.enabled else '#cbd5e1'}; border-radius: 4px;")
        lay.addWidget(dot, 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(4)
        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        name = BodyLabel(conn.name or conn.host)
        set_label_color(name, TEXT_PRIMARY if conn.enabled else TEXT_MUTED)
        top_row.addWidget(name, 1)
        status = CaptionLabel("启用" if conn.enabled else "停用")
        set_label_color(status, SUCCESS if conn.enabled else TEXT_SUBTLE)
        top_row.addWidget(status)
        col.addLayout(top_row)
        sub = CaptionLabel(f"{conn.host}:{conn.port} · {conn.database or '未选择数据库'}")
        set_label_color(sub, TEXT_MUTED)
        col.addWidget(sub)
        lay.addLayout(col, 1)

        menu_btn = TransparentPushButton("⋯")
        menu_btn.setFixedSize(32, 32)
        menu_btn.setStyleSheet(f"""
            TransparentPushButton {{ color: {TEXT_MUTED}; border-radius: 10px; }}
            TransparentPushButton:hover {{ background: {PRIMARY_SOFT}; color: {PRIMARY}; }}
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
        setThemeColor(PRIMARY)
        self.setWindowTitle("SQL 批量执行器")
        self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.setTitleBar(AppTitleBar(self))
        self.resize(1320, 840)
        self.setMinimumSize(960, 640)

        self.service = ConnectionService()
        self.results = []
        self._tab_buttons = []
        self._current_tab = 0
        self._threads = []

        self._build()

    def _track_thread(self, thread: QThread):
        self._threads.append(thread)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)

    def _build(self):
        central = QWidget()
        central.setObjectName("appRoot")
        central.setStyleSheet(f"""
            #appRoot {{
                background: {APP_BACKGROUND};
            }}
            QWidget {{
                font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
                color: {TEXT_PRIMARY};
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
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, self.titleBar.height(), 0, 0)
        root_lay.setSpacing(0)
        root_lay.addWidget(central)
        main_lay = QHBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setObjectName("sidePanel")
        sidebar.setStyleSheet(f"""
            #sidePanel {{
                background: {APP_CHROME};
                border-right: 1px solid {SIDEBAR_BORDER};
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
            color: {PRIMARY};
            background: {PRIMARY_SOFT};
            border: 1px solid {STRONG_BORDER};
            border-radius: 10px;
            font-size: 13px;
            font-weight: 700;
        """)
        logo_row.addWidget(brand_badge)
        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        sql_lbl = QLabel("SQL 批量执行器")
        sql_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        brand_col.addWidget(sql_lbl)
        sub_lbl = QLabel("Batch Executor")
        sub_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED}; background: transparent; border: none;")
        brand_col.addWidget(sub_lbl)
        logo_row.addLayout(brand_col)
        logo_row.addStretch()
        sb_lay.addLayout(logo_row)
        sb_lay.addSpacing(16)

        overview_card = QFrame()
        overview_card.setObjectName("overviewCard")
        overview_card.setStyleSheet(f"""
            #overviewCard {{
                background: {SIDEBAR_SURFACE};
                border: 1px solid {SIDEBAR_BORDER};
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
        set_label_color(self.sidebar_count_label, TEXT_MUTED)
        overview_lay.addWidget(self.sidebar_count_label)
        self.sidebar_enabled_label = CaptionLabel("0 启用")
        set_label_color(self.sidebar_enabled_label, PRIMARY)
        overview_lay.addWidget(self.sidebar_enabled_label)
        sb_lay.addWidget(overview_card)
        sb_lay.addSpacing(18)

        sec_row = QHBoxLayout()
        sec_lbl = QLabel("数据库连接")
        sec_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        sec_row.addWidget(sec_lbl)
        sec_row.addStretch()
        add_btn = PrimaryPushButton("+ 添加")
        add_btn.setFixedSize(84, 34)
        add_btn.setStyleSheet(primary_button_qss())
        add_btn.clicked.connect(self._on_add)
        sec_row.addWidget(add_btn)
        sb_lay.addLayout(sec_row)
        sb_lay.addSpacing(12)

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
                background: {APP_BACKGROUND};
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
                background: {APP_CHROME};
                border-bottom: 1px solid {BORDER};
            }}
        """)
        top_bar.setFixedHeight(64)
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(24, 0, 24, 0)
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        ttl = QLabel("SQL 执行")
        ttl.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            background: transparent;
            font-size: 18px;
            font-weight: 700;
        """)
        title_col.addWidget(ttl)
        hint = QLabel("选择目标连接后执行，结果在下方查看")
        hint.setStyleSheet(f"""
            color: {TEXT_MUTED};
            background: transparent;
            font-size: 12px;
        """)
        title_col.addWidget(hint)
        tb_lay.addLayout(title_col)
        tb_lay.addStretch()
        self.summary_label = QLabel("")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setFixedHeight(28)
        self.summary_label.setMinimumWidth(132)
        self.summary_label.setStyleSheet(f"""
            QLabel {{
                color: {TEXT_MUTED};
                background: {SURFACE};
                border: 1px solid {BORDER};
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
                background: {SURFACE};
                border: 1px solid {BORDER};
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
        ed_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {TEXT_PRIMARY}; background: transparent;")
        ed_title_col.addWidget(ed_title)
        ed_caption = CaptionLabel("执行前选择目标连接")
        set_label_color(ed_caption, TEXT_MUTED)
        ed_title_col.addWidget(ed_caption)
        ed_hdr.addLayout(ed_title_col)
        ed_hdr.addStretch()
        self.exec_btn = PrimaryPushButton("批量执行")
        self.exec_btn.setFixedSize(110, 34)
        self.exec_btn.setStyleSheet(primary_button_qss())
        self.exec_btn.clicked.connect(self._on_execute)
        ed_hdr.addWidget(self.exec_btn)
        ec_lay.addLayout(ed_hdr)

        self.sql_input = PlainTextEdit()
        self.sql_input.setPlaceholderText("输入要执行的 SQL 语句…")
        self.sql_input.setMinimumHeight(150)
        self.sql_input.setMaximumHeight(220)
        self.sql_input.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {EDITOR_BG};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 12px;
                font-family: {EDITOR_FONT};
                font-size: 14px;
                color: {EDITOR_TEXT};
                selection-background-color: #bfdbfe;
            }}
            QPlainTextEdit:focus {{
                border: 1px solid {PRIMARY};
                background: {EDITOR_PANEL};
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
                background: {APP_CHROME};
                border-top: 1px solid {BORDER};
                border-bottom: 1px solid {BORDER};
            }}
        """)
        pf_lay = QVBoxLayout(self.progress_frame)
        pf_lay.setContentsMargins(28, 10, 28, 10)
        pf_lay.setSpacing(6)
        self.progress = ProgressBar()
        pf_lay.addWidget(self.progress)
        self.status_label = CaptionLabel("就绪")
        set_label_color(self.status_label, TEXT_SUBTLE)
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
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        empty_card_lay = QVBoxLayout(empty_card)
        empty_card_lay.setContentsMargins(18, 16, 18, 16)
        empty_card_lay.setAlignment(Qt.AlignVCenter)
        empty_card_lay.setSpacing(6)
        txt = QLabel("暂无执行结果")
        txt.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {TEXT_PRIMARY}; background: transparent;")
        txt.setAlignment(Qt.AlignLeft)
        empty_card_lay.addWidget(txt)
        desc = QLabel("输入 SQL 并执行后，这里会显示各连接的执行结果。")
        desc.setStyleSheet(f"font-size: 13px; color: {TEXT_MUTED}; background: transparent;")
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

    def _refresh_conn_list(self):
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
            set_label_color(lbl, "#94a3b8")
            lbl.setStyleSheet("padding: 48px 0; background: transparent; line-height: 1.5;")
            self.conn_layout.insertWidget(0, lbl)
            return

        for i, conn in enumerate(conns):
            card = ConnCard(conn, i, self._show_conn_menu)
            self.conn_layout.insertWidget(i, card)

    def _show_conn_menu(self, index: int):
        conn = self.service.connections[index]
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {SIDEBAR_SURFACE};
                color: {TEXT_PRIMARY};
                border: 1px solid {SIDEBAR_BORDER};
                border-radius: 10px;
                padding: 4px; font-size: 12px;
            }}
            QMenu::item {{ padding: 8px 24px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {PRIMARY_SOFT}; color: {PRIMARY}; }}
            QMenu::item#deleteAction {{ color: {DANGER}; }}
            QMenu::item#deleteAction:selected {{ background: {DANGER_SOFT}; color: {DANGER}; }}
            QMenu::separator {{ height: 1px; background: {SIDEBAR_BORDER}; margin: 4px 8px; }}
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
        set_label_color(self.status_label, TEXT_SUBTLE)
        self.progress.setValue(0)
        self.progress.setMaximum(0)
        self.progress_frame.show()

        thread = QThread(self)
        worker = TestConnectionWorker(self.service.database, conn)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_test_finished)
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
        enabled = self.service.enabled_connections()
        if not enabled:
            InfoBar.warning("提示", "没有可用的数据库连接",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)
            return

        dlg = ExecSelectDialog(self, enabled)
        if dlg.exec_() != Dialog.Accepted or not dlg.selected:
            return

        targets = self.service.resolve_targets(enabled, dlg.selected)
        if not self._confirm_dangerous_sql(sql, len(targets)):
            return
        total = len(targets)

        self.exec_btn.setEnabled(False)
        self.exec_btn.setText("执行中…")
        self.progress.setValue(0)
        self.progress.setMaximum(total)
        self.progress_frame.show()
        self.results = []

        thread = QThread(self)
        worker = SqlExecutionWorker(self.service.database, targets, sql)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status_changed.connect(self._on_execute_status_changed)
        worker.progress_changed.connect(self._on_execute_progress_changed)
        worker.finished.connect(lambda results, executed_sql=sql: self._on_execute_finished(results, executed_sql))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._track_thread(thread)
        thread.start()

    def _confirm_dangerous_sql(self, sql: str, target_count: int) -> bool:
        operations = self.service.dangerous_operations(sql)
        if not operations:
            return True

        warning = MessageBox(
            "危险 SQL 确认",
            f"检测到危险操作：{', '.join(operations)}\n\n"
            f"这条 SQL 将发送到 {target_count} 个连接。请确认你已经备份或确认影响范围。",
            self,
        )
        warning.yesButton.setText("确认执行")
        warning.cancelButton.setText("取消")
        return warning.exec_() == Dialog.Accepted

    def _on_execute_status_changed(self, text: str):
        self.status_label.setText(text)
        set_label_color(self.status_label, TEXT_SUBTLE)

    def _on_execute_progress_changed(self, current: int, total: int, result: ExecutionResult):
        self.results.append(result)
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def _on_execute_finished(self, results: list[ExecutionResult], sql: str):
        self.results = results
        self.exec_btn.setEnabled(True)
        self.exec_btn.setText("批量执行")
        summary = self.service.summarize(self.results)
        try:
            self.service.record_history(sql, self.results)
            history_note = "，已记录历史"
        except Exception as error:
            history_note = ""
            InfoBar.warning("历史记录失败", str(error), parent=self, position=InfoBarPosition.TOP_RIGHT)
        if summary.success == summary.total:
            self.status_label.setText(f"完成: {summary.success}/{summary.total} 成功")
            set_label_color(self.status_label, SUCCESS)
            InfoBar.success("执行完成", f"{summary.success}/{summary.total} 个连接执行成功{history_note}",
                            parent=self, position=InfoBarPosition.TOP_RIGHT)
        else:
            self.status_label.setText(f"完成: {summary.success}/{summary.total} 成功")
            set_label_color(self.status_label, DANGER)
            InfoBar.error("执行完成", f"{summary.failed} 个连接执行失败",
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

        if not self.results:
            self.result_stack.setCurrentIndex(0)
            return

        self.result_stack.setCurrentIndex(1)

        summary = self.service.summarize(self.results)

        summary_bar = QFrame()
        summary_bar.setStyleSheet(f"background: {SURFACE}; border-bottom: 1px solid {BORDER};")
        summary_lay = QHBoxLayout(summary_bar)
        summary_lay.setContentsMargins(20, 10, 20, 10)
        summary_lay.setSpacing(12)
        summary_title = SubtitleLabel("执行结果")
        summary_lay.addWidget(summary_title)
        total_label = CaptionLabel(f"目标 {summary.total}")
        set_label_color(total_label, TEXT_MUTED)
        summary_lay.addWidget(total_label)
        success_label = CaptionLabel(f"成功 {summary.success}")
        set_label_color(success_label, SUCCESS)
        summary_lay.addWidget(success_label)
        if summary.failed:
            failed_label = CaptionLabel(f"失败 {summary.failed}")
            set_label_color(failed_label, DANGER)
            summary_lay.addWidget(failed_label)
        summary_lay.addStretch()
        elapsed_label = CaptionLabel(f"累计耗时 {summary.elapsed_ms:.0f}ms")
        set_label_color(elapsed_label, TEXT_MUTED)
        summary_lay.addWidget(elapsed_label)
        self._results_lay.addWidget(summary_bar)

        tab_bar = QFrame()
        tab_bar.setStyleSheet(f"background: {SURFACE}; border-bottom: 1px solid {BORDER};")
        tab_lay = QHBoxLayout(tab_bar)
        tab_lay.setContentsMargins(12, 0, 0, 0)
        tab_lay.setSpacing(0)

        for i, r in enumerate(self.results):
            icon = "✓" if r.success else "✗"
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
        for r in self.results:
            page = self._build_result_page(r)
            self._content_stack.addWidget(page)
        self._results_lay.addWidget(self._content_stack, 1)

    def _tab_style(self, active: bool):
        if active:
            return f"""
                QPushButton {{
                    background: transparent; border: none;
                    border-bottom: 2px solid {PRIMARY};
                    color: {PRIMARY}; font-weight: bold;
                    padding: 0 16px; font-size: 13px;
                }}
                QPushButton:hover {{ background: {PRIMARY_SOFT}; }}
            """
        return f"""
            QPushButton {{
                background: transparent; border: none;
                border-bottom: 2px solid transparent;
                color: {TEXT_MUTED}; font-weight: normal;
                padding: 0 16px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {SURFACE_SUBTLE}; }}
        """

    def _select_tab(self, index: int):
        if index == self._current_tab:
            return
        self._tab_buttons[self._current_tab].setStyleSheet(self._tab_style(False))
        self._tab_buttons[index].setStyleSheet(self._tab_style(True))
        self._content_stack.setCurrentIndex(index)
        self._current_tab = index

    def _build_result_page(self, r: ExecutionResult):
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
                    background: {SURFACE};
                    border: 1px solid {BORDER};
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
            set_label_color(info_lbl, SUCCESS)
            title_col.addWidget(info_lbl)
            header.addLayout(title_col)
            header.addStretch()
            rows_label = CaptionLabel(f"{len(r.data)} 行")
            set_label_color(rows_label, TEXT_MUTED)
            header.addWidget(rows_label)
            if len(r.data) > 2000:
                limit_label = CaptionLabel("仅显示前 2000 行")
                set_label_color(limit_label, WARNING)
                header.addWidget(limit_label)
            container_lay.addLayout(header)

            table = TableWidget()
            table.setAlternatingRowColors(True)
            table.setWordWrap(False)
            table.setRowCount(min(len(r.data), 2000))
            table.setColumnCount(len(r.columns))
            table.setHorizontalHeaderLabels(r.columns)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
            table.verticalHeader().hide()
            table.horizontalHeader().setStretchLastSection(True)
            table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
            table.setStyleSheet(f"""
                QTableWidget {{
                    background: {SURFACE};
                    border: 1px solid {BORDER};
                    border-radius: 6px;
                    gridline-color: {BORDER};
                    selection-background-color: #dbeafe;
                    selection-color: {TEXT_PRIMARY};
                }}
                QHeaderView::section {{
                    background: {SURFACE_SUBTLE};
                    color: {TEXT_MUTED};
                    border: none;
                    border-bottom: 1px solid {BORDER};
                    padding: 8px;
                    font-weight: 600;
                }}
            """)

            for row_idx, row_data in enumerate(r.data[:2000]):
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

            table.resizeColumnsToContents()
            container_lay.addWidget(table, 1)
            if not r.data:
                empty_note = CaptionLabel("查询成功，但没有返回数据行。")
                empty_note.setAlignment(Qt.AlignCenter)
                set_label_color(empty_note, TEXT_MUTED)
                container_lay.addWidget(empty_note)
            lay.addWidget(container, 1)
        else:
            color = SUCCESS if r.success else DANGER
            bg = SUCCESS_SOFT if r.success else DANGER_SOFT
            wrapper = SimpleCardWidget()
            wrapper.setObjectName("resultStatusCard")
            wrapper.setStyleSheet(f"""
                #resultStatusCard {{
                    background: {SURFACE};
                    border: 1px solid {BORDER};
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
            set_label_color(msg, color)
            msg.setAlignment(Qt.AlignCenter)
            msg.setWordWrap(True)
            w_lay.addWidget(msg)

            dur = CaptionLabel(f"耗时: {r.duration_ms:.0f}ms")
            set_label_color(dur, TEXT_MUTED)
            dur.setAlignment(Qt.AlignCenter)
            w_lay.addWidget(dur)

            lay.addWidget(wrapper, 1)

        return page


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    setTheme(Theme.LIGHT)
    setThemeColor(PRIMARY)
    win = MainWindow()
    win.show()
    if not app.topLevelWidgets():
        app.exec_()


if __name__ == "__main__":
    main()
