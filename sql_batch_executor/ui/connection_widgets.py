from PyQt5.QtCore import QMimeData, Qt
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

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
    SubtitleLabel,
    TransparentPushButton,
)

from sql_batch_executor.core.config_manager import ConnectionConfig
from sql_batch_executor.core.services import ConnectionService
from sql_batch_executor.ui import theme


CONNECTION_DRAG_MIME = "application/x-sql-batch-connection-index"


class GroupDialog(Dialog):
    def __init__(self, parent, title: str = "新建分组", initial_name: str = ""):
        super().__init__(title, "", parent)
        self.contentLabel.hide()
        self.setMinimumWidth(420)
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.result = None

        self.textLayout.addSpacing(4)
        intro = CaptionLabel("用于区分测试环境、预发环境、正式环境等连接集合。")
        theme.set_label_color(intro, theme.TEXT_MUTED)
        self.textLayout.addWidget(intro)
        self.textLayout.addSpacing(10)

        self.textLayout.addWidget(BodyLabel("分组名称"))
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("例如：测试环境")
        self.name_edit.setText(initial_name)
        self.name_edit.setClearButtonEnabled(True)
        self.name_edit.setFixedHeight(36)
        self.name_edit.setStyleSheet(f"""
            LineEdit {{
                background: {theme.EDITOR_BG};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 0 10px;
                color: {theme.TEXT_PRIMARY};
            }}
            LineEdit:focus {{
                border-color: {theme.PRIMARY};
                background: {theme.EDITOR_PANEL};
            }}
        """)
        self.textLayout.addWidget(self.name_edit)

        self.yesButton.setFixedHeight(34)
        self.cancelButton.setFixedHeight(34)
        self.yesButton.setStyleSheet(theme.primary_button_qss())
        self.cancelButton.setStyleSheet(f"""
            QPushButton {{
                background: {theme.SURFACE_SUBTLE};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: 7px;
                font-weight: 600;
                padding: 6px 18px;
            }}
            QPushButton:hover {{
                background: {theme.PRIMARY_SOFT};
                border-color: {theme.PRIMARY_BORDER};
                color: {theme.PRIMARY};
            }}
        """)
        self.setFixedSize(max(self.sizeHint().width(), 420), self.sizeHint().height())

    def validate(self):
        if not self.name_edit.text().strip():
            InfoBar.warning("提示", "分组名称不能为空", parent=self)
            return False
        return True

    def accept(self):
        if not self.validate():
            return
        self.result = self.name_edit.text().strip()
        super().accept()


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
        self.group_combo = ComboBox()
        self.group_combo.setPlaceholderText("选择分组")
        self._group_ids: list[str] = []
        groups = list(getattr(self.service.config, "groups", []) or [])
        current_group_id = self._conn.group_id or self.service.config.default_group_id()
        if self.service.config.group_by_id(current_group_id) is None:
            current_group_id = self.service.config.default_group_id()
        for group in groups:
            self.group_combo.addItem(group.name)
            self._group_ids.append(group.id)
        if current_group_id in self._group_ids:
            self.group_combo.setCurrentIndex(self._group_ids.index(current_group_id))
        form.addWidget(self.group_combo)

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

        for editor in (self.name_edit, self.group_combo, self.host_edit, self.port_edit, self.user_edit, self.pwd_edit, self.db_combo):
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
        group_index = self.group_combo.currentIndex()
        group_id = self._group_ids[group_index] if 0 <= group_index < len(self._group_ids) else self.service.config.default_group_id()
        self.result = ConnectionConfig(
            id=self._conn.id,
            name=self.name_edit.text().strip() or host,
            group_id=group_id,
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
        self.service = parent.service if parent is not None else None
        self._tree = None
        self._updating_checks = False
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

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["分组 / 连接", "地址 / 数据库"])
        self._tree.setRootIsDecorated(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.setColumnWidth(0, 230)
        self._tree.setMinimumHeight(280)
        self._tree.itemChanged.connect(self._on_tree_item_changed)
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {theme.SURFACE};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 4px;
                selection-background-color: {theme.SELECTED_BG};
                selection-color: {theme.TEXT_PRIMARY};
            }}
            QTreeWidget::item {{
                min-height: 28px;
                border-radius: 5px;
                padding: 4px;
            }}
            QTreeWidget::item:hover {{
                background: {theme.PRIMARY_SOFT};
            }}
            QHeaderView::section {{
                background: {theme.SURFACE_SUBTLE};
                color: {theme.TEXT_MUTED};
                border: none;
                border-bottom: 1px solid {theme.BORDER};
                padding: 7px;
                font-weight: 600;
            }}
        """)
        self.textLayout.addWidget(self._tree, 1)
        self._populate_tree()

        self._update_count()

    def _on_select_all(self, state):
        if not self._tree:
            return
        self._updating_checks = True
        check_state = Qt.Checked if state else Qt.Unchecked
        for index in range(self._tree.topLevelItemCount()):
            group_item = self._tree.topLevelItem(index)
            group_item.setCheckState(0, check_state)
            for child_index in range(group_item.childCount()):
                group_item.child(child_index).setCheckState(0, check_state)
        self._updating_checks = False
        self._update_count()

    def _populate_tree(self):
        grouped: dict[str, list[tuple[int, object]]] = {}
        for index, conn in enumerate(self._connections):
            group_name = self.service.config.group_name(conn.group_id) if self.service else "默认分组"
            grouped.setdefault(group_name, []).append((index, conn))

        self._updating_checks = True
        for group_name in sorted(grouped):
            items = grouped[group_name]
            group_item = QTreeWidgetItem([f"{group_name} ({len(items)})", ""])
            group_item.setFlags(group_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
            group_item.setCheckState(0, Qt.Checked)
            group_item.setExpanded(True)
            self._tree.addTopLevelItem(group_item)

            for index, conn in items:
                child = QTreeWidgetItem([
                    conn.name or conn.host,
                    f"{conn.host}:{conn.port}  /  {conn.database or '-'}",
                ])
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Checked)
                child.setData(0, Qt.UserRole, index)
                group_item.addChild(child)
        self._updating_checks = False

    def _on_tree_item_changed(self, item, column):
        if self._updating_checks or column != 0:
            return
        self._sync_select_all_state()
        self._update_count()

    def _checked_indices(self) -> list[int]:
        if not self._tree:
            return []
        selected: list[int] = []
        for group_index in range(self._tree.topLevelItemCount()):
            group_item = self._tree.topLevelItem(group_index)
            for child_index in range(group_item.childCount()):
                child = group_item.child(child_index)
                if child.checkState(0) == Qt.Checked:
                    selected.append(int(child.data(0, Qt.UserRole)))
        return selected

    def _sync_select_all_state(self):
        checked = len(self._checked_indices())
        total = len(self._connections)
        self._sel_all.blockSignals(True)
        self._sel_all.setChecked(total > 0 and checked == total)
        self._sel_all.blockSignals(False)

    def _update_count(self):
        total = len(self._connections)
        checked = len(self._checked_indices())
        self._count_label.setText(f"已选 {checked} / {total}")
        theme.set_label_color(self._count_label, theme.PRIMARY if checked else theme.TEXT_SUBTLE)
        if checked > 0:
            self.yesButton.setText(f"执行 ({checked})")
            self.yesButton.setEnabled(True)
        else:
            self.yesButton.setText("执行")
            self.yesButton.setEnabled(False)

    def accept(self):
        self.selected = self._checked_indices()
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
        self._connection_id = conn.id
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
        menu_btn.clicked.connect(lambda: self._on_menu(self._connection_id))
        lay.addWidget(menu_btn)

    def contextMenuEvent(self, e):
        self._on_menu(self._connection_id)

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
        mime.setData(CONNECTION_DRAG_MIME, self._connection_id.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(Qt.MoveAction)


class GroupHeader(QWidget):
    def __init__(
        self,
        group_id: str,
        group_name: str,
        total: int,
        enabled: int,
        on_rename,
        on_toggle,
        on_drop_connection,
        collapsed: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.group_id = group_id
        self.group_name = group_name
        self._on_rename = on_rename
        self._on_toggle = on_toggle
        self._on_drop_connection = on_drop_connection
        self._collapsed = collapsed
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("groupHeader")
        self._apply_normal_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 8, 6, 4)
        layout.setSpacing(6)

        toggle_btn = QToolButton()
        toggle_btn.setText("▸" if collapsed else "▾")
        toggle_btn.setFixedSize(22, 22)
        toggle_btn.setToolTip("展开分组" if collapsed else "折叠分组")
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                color: {theme.TEXT_MUTED};
                border-radius: 6px;
                font-size: 15px;
                font-weight: 700;
                padding: 0;
            }}
            QToolButton:hover {{
                background: {theme.PRIMARY_SOFT};
                color: {theme.PRIMARY};
            }}
        """)
        toggle_btn.clicked.connect(lambda: self._on_toggle(self.group_id))
        layout.addWidget(toggle_btn)
        self.toggle_btn = toggle_btn

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

    def _apply_normal_style(self):
        self.setStyleSheet("""
            #groupHeader {
                background: transparent;
                border: none;
                border-radius: 8px;
            }
        """)

    def _apply_hover_style(self):
        self.setStyleSheet(f"""
            #groupHeader {{
                background: {theme.SIDEBAR_SURFACE};
                border: 1px solid {theme.SIDEBAR_BORDER};
                border-radius: 8px;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_toggle(self.group_id)
            return
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._apply_hover_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_normal_style()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        self._on_rename(self.group_id)

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
        self._apply_normal_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._apply_normal_style()
        if not event.mimeData().hasFormat(CONNECTION_DRAG_MIME):
            event.ignore()
            return
        connection_id = bytes(event.mimeData().data(CONNECTION_DRAG_MIME)).decode("utf-8").strip()
        if not connection_id:
            event.ignore()
            return
        self._on_drop_connection(connection_id, self.group_id)
        event.acceptProposedAction()
