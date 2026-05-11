from PyQt5.QtCore import QMimeData, Qt
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    CheckBox,
    ComboBox,
    Dialog,
    InfoBar,
    LineEdit,
    PrimaryPushButton,
    ScrollArea,
    SimpleCardWidget,
    SubtitleLabel,
    TransparentPushButton,
)

from sql_batch_executor.core.config_manager import ConnectionConfig
from sql_batch_executor.core.services import ConnectionService
from sql_batch_executor.ui import theme


CONNECTION_DRAG_MIME = "application/x-sql-batch-connection-index"


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

        form.addWidget(BodyLabel("分组"))
        self.group_edit = LineEdit()
        self.group_edit.setPlaceholderText("例如：测试环境 / 正式环境")
        self.group_edit.setText(self._conn.group or "默认分组")
        self.group_edit.setClearButtonEnabled(True)
        form.addWidget(self.group_edit)

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

        for editor in (self.name_edit, self.group_edit, self.host_edit, self.port_edit, self.user_edit, self.pwd_edit, self.db_combo):
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
        self.fetch_btn.setText("...")
        self.fetch_status.setText("正在连接服务器...")
        theme.set_label_color(self.fetch_status, theme.TEXT_SUBTLE)

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
            group=self.group_edit.text().strip() or "默认分组",
            host=host,
            port=int(self.port_edit.text().strip() or 3306),
            user=self.user_edit.text().strip(),
            password=self.pwd_edit.text().strip(),
            database=self.db_combo.currentText().strip(),
            enabled=self._conn.enabled,
        )
        super().accept()


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

        for conn in self._connections:
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
        self._drag_start_pos = None

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

        menu_btn = TransparentPushButton("...")
        menu_btn.setFixedSize(32, 32)
        menu_btn.setStyleSheet(f"""
            TransparentPushButton {{ color: {theme.TEXT_MUTED}; border-radius: 10px; }}
            TransparentPushButton:hover {{ background: {theme.PRIMARY_SOFT}; color: {theme.PRIMARY}; }}
        """)
        menu_btn.clicked.connect(lambda: self._on_menu(self._index))
        lay.addWidget(menu_btn)

    def contextMenuEvent(self, e):
        self._on_menu(self._index)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self._drag_start_pos is None:
            super().mouseMoveEvent(event)
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < 8:
            super().mouseMoveEvent(event)
            return

        mime = QMimeData()
        mime.setData(CONNECTION_DRAG_MIME, str(self._index).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(Qt.MoveAction)


class GroupHeader(QWidget):
    def __init__(
        self,
        group_name: str,
        total: int,
        enabled: int,
        on_rename,
        on_drop_connection,
        parent=None,
    ):
        super().__init__(parent)
        self.group_name = group_name
        self._on_rename = on_rename
        self._on_drop_connection = on_drop_connection
        self.setAcceptDrops(True)
        self.setStyleSheet("background: transparent; border: none;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 10, 2, 2)
        layout.setSpacing(6)

        self.name_label = QLabel(group_name)
        self.name_label.setStyleSheet(f"""
            color: {theme.TEXT_PRIMARY};
            background: transparent;
            font-size: 12px;
            font-weight: 700;
        """)
        layout.addWidget(self.name_label)
        layout.addStretch()

        hint = QLabel("拖入")
        hint.setStyleSheet(f"""
            color: {theme.TEXT_SUBTLE};
            background: transparent;
            font-size: 11px;
        """)
        layout.addWidget(hint)

        count = QLabel(f"{enabled}/{total}")
        count.setStyleSheet(f"""
            color: {theme.TEXT_MUTED};
            background: {theme.SIDEBAR_SURFACE};
            border: 1px solid {theme.SIDEBAR_BORDER};
            border-radius: 7px;
            padding: 2px 7px;
            font-size: 11px;
        """)
        layout.addWidget(count)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_rename(self.group_name)
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        self._on_rename(self.group_name)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(CONNECTION_DRAG_MIME):
            self.setStyleSheet(f"""
                background: {theme.PRIMARY_SOFT};
                border: 1px solid {theme.PRIMARY_BORDER};
                border-radius: 8px;
            """)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("background: transparent; border: none;")
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.setStyleSheet("background: transparent; border: none;")
        if not event.mimeData().hasFormat(CONNECTION_DRAG_MIME):
            event.ignore()
            return
        try:
            index = int(bytes(event.mimeData().data(CONNECTION_DRAG_MIME)).decode("utf-8"))
        except ValueError:
            event.ignore()
            return
        self._on_drop_connection(index, self.group_name)
        event.acceptProposedAction()
