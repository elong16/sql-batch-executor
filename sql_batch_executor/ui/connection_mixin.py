from PyQt5.QtCore import QThread, Qt
from PyQt5.QtWidgets import QDialog, QInputDialog, QMenu

from qfluentwidgets import BodyLabel, Dialog, InfoBar, InfoBarPosition, MessageBox

from sql_batch_executor.core.config_manager import ConnectionConfig
from sql_batch_executor.ui import theme
from sql_batch_executor.ui.connection_widgets import ConnCard, ConnDialog, GroupHeader
from sql_batch_executor.ui.workers import TestConnectionWorker


class ConnectionMixin:
    def _add_group_header(self, group_name: str, total: int, enabled: int):
        header = GroupHeader(
            group_name,
            total,
            enabled,
            self._rename_group,
            self._move_connection_to_group,
        )
        self.conn_layout.insertWidget(self.conn_layout.count() - 1, header)

    def _group_names(self) -> list[str]:
        names = {
            (getattr(conn, "group", "") or "默认分组").strip() or "默认分组"
            for conn in self.service.connections
        }
        return sorted(names)

    def _rename_group(self, old_name: str):
        new_name, ok = QInputDialog.getText(self, "编辑分组", "分组名称", text=old_name)
        if not ok:
            return
        new_name = new_name.strip() or "默认分组"
        if new_name == old_name:
            return
        for conn in self.service.connections:
            group_name = (getattr(conn, "group", "") or "默认分组").strip() or "默认分组"
            if group_name == old_name:
                conn.group = new_name
        self.service.config.save()
        self._refresh_conn_list(self.search_edit.text() if hasattr(self, "search_edit") else "")
        InfoBar.success("成功", f"已将分组改为「{new_name}」", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _move_connection_to_group(self, index: int, group_name: str):
        if not (0 <= index < len(self.service.connections)):
            return
        conn = self.service.connections[index]
        group_name = group_name.strip() or "默认分组"
        current = (getattr(conn, "group", "") or "默认分组").strip() or "默认分组"
        if current == group_name:
            return
        conn.group = group_name
        self.service.config.save()
        self._refresh_conn_list(self.search_edit.text() if hasattr(self, "search_edit") else "")
        InfoBar.success("已移动", f"{conn.name or conn.host} -> {group_name}", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _update_summary(self):
        total = len(self.service.connections)
        enabled = len(self.service.enabled_connections())
        self.summary_label.setText(f"{enabled} 个启用 / {total} 个连接")
        self.sidebar_count_label.setText(f"{total} 个")
        self.sidebar_enabled_label.setText(f"{enabled} 启用")

    def _refresh_conn_list(self, filter_text: str = ""):
        while self.conn_layout.count() > 1:
            item = self.conn_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._update_summary()
        conns = self.service.connections
        if not conns:
            label = BodyLabel("暂无连接\n点击「+ 添加」开始")
            label.setAlignment(Qt.AlignCenter)
            theme.set_label_color(label, "#94a3b8")
            label.setStyleSheet("padding: 48px 0; background: transparent; line-height: 1.5;")
            self.conn_layout.insertWidget(0, label)
            return

        keyword = filter_text.lower().strip()
        grouped: dict[str, list[tuple[int, object]]] = {}
        for index, conn in enumerate(conns):
            group_name = (getattr(conn, "group", "") or "默认分组").strip() or "默认分组"
            haystack = " ".join([conn.name, conn.host, conn.database or "", group_name]).lower()
            if keyword and keyword not in haystack:
                continue
            grouped.setdefault(group_name, []).append((index, conn))

        if not grouped:
            label = BodyLabel("没有匹配的连接")
            label.setAlignment(Qt.AlignCenter)
            theme.set_label_color(label, "#94a3b8")
            label.setStyleSheet("padding: 48px 0; background: transparent;")
            self.conn_layout.insertWidget(0, label)
            return

        for group_name in sorted(grouped):
            items = grouped[group_name]
            enabled = sum(1 for _, conn in items if conn.enabled)
            self._add_group_header(group_name, len(items), enabled)
            for index, conn in items:
                card = ConnCard(conn, index, self._show_conn_menu)
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
        move_menu = menu.addMenu("移动到分组")
        for group_name in self._group_names():
            move_menu.addAction(group_name, lambda checked=False, name=group_name: self._move_connection_to_group(index, name))
        move_menu.addSeparator()
        move_menu.addAction("新建分组...", lambda: self._move_connection_to_new_group(index))
        toggle_text = "禁用" if conn.enabled else "启用"
        menu.addAction(toggle_text, lambda: self._on_toggle(index))
        menu.addSeparator()
        delete_action = menu.addAction("删除", lambda: self._on_remove(index))
        delete_action.setObjectName("deleteAction")
        menu.exec_(self.cursor().pos())

    def _move_connection_to_new_group(self, index: int):
        name, ok = QInputDialog.getText(self, "新建分组", "分组名称")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        self._move_connection_to_group(index, name)

    def _on_add(self):
        dialog = ConnDialog(self, ConnectionConfig(), "添加连接", self.service)
        if dialog.exec_() == QDialog.Accepted and dialog.result:
            self.service.add(dialog.result)
            self._refresh_conn_list()
            InfoBar.success("成功", f"已添加连接 \"{dialog.result.name}\"", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _on_edit(self, index: int):
        dialog = ConnDialog(self, self.service.connections[index], "编辑连接", self.service)
        if dialog.exec_() == QDialog.Accepted and dialog.result:
            self.service.update(index, dialog.result)
            self._refresh_conn_list()
            InfoBar.success("成功", f"已更新连接 \"{dialog.result.name}\"", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _on_test(self, index: int):
        conn = self.service.connections[index]
        self.status_label.setText(f"正在测试: {conn.name}...")
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
            InfoBar.success("连接成功", f"{conn_name}: {msg}", parent=self, position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.error("连接失败", f"{conn_name}: {msg}", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _on_test_thread_finished(self, ok: bool, msg: str, conn_name: str):
        for index, conn in enumerate(self.service.connections):
            if (conn.name or conn.host) == conn_name:
                self.service.config.connections[index].last_test_ok = ok
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
        dialog = MessageBox("确认删除", f"确定要删除连接 \"{conn.name}\" 吗？", self)
        if dialog.exec_() == Dialog.Accepted:
            self.service.remove(index)
            self._refresh_conn_list()
            InfoBar.success("成功", "已删除连接", parent=self, position=InfoBarPosition.TOP_RIGHT)
