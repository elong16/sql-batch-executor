from PyQt5.QtCore import QThread, Qt
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QMenu, QWidget

from qfluentwidgets import BodyLabel, Dialog, InfoBar, InfoBarPosition, MessageBox

from sql_batch_executor.core.config_manager import ConnectionConfig
from sql_batch_executor.ui import theme
from sql_batch_executor.ui.connection_widgets import ConnCard, ConnDialog, GroupDialog, GroupHeader
from sql_batch_executor.ui.workers import TestConnectionWorker


class ConnectionMixin:
    def _add_group_header(self, group, total: int, enabled: int, collapsed: bool | None = None):
        if collapsed is None:
            collapsed = group.collapsed
        header = GroupHeader(
            group.id,
            group.name,
            total,
            enabled,
            self._rename_group,
            self._toggle_group_collapsed,
            self._move_connection_to_group,
            collapsed,
        )
        self.conn_layout.insertWidget(self.conn_layout.count() - 1, header)

    def _groups(self):
        return sorted(getattr(self.service.config, "groups", []) or [], key=lambda group: group.name)

    def _toggle_group_collapsed(self, group_id: str):
        group = self.service.config.group_by_id(group_id)
        if group is None:
            return
        self.service.config.set_group_collapsed(group_id, not group.collapsed)
        self._refresh_conn_list(self.search_edit.text() if hasattr(self, "search_edit") else "")

    def _on_add_group(self):
        dialog = GroupDialog(self, "新建分组")
        if dialog.exec_() != QDialog.Accepted or not dialog.result:
            return
        group = self.service.config.add_group(dialog.result)
        if group:
            self._refresh_conn_list(self.search_edit.text() if hasattr(self, "search_edit") else "")
            InfoBar.success("成功", f"已创建分组「{dialog.result}」", parent=self, position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.warning("提示", f"分组「{dialog.result}」已存在", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _rename_group(self, group_id: str):
        group = self.service.config.group_by_id(group_id)
        if group is None:
            return
        old_name = group.name
        dialog = GroupDialog(self, "编辑分组", old_name)
        if dialog.exec_() != QDialog.Accepted or not dialog.result:
            return
        new_name = dialog.result.strip() or "默认分组"
        if new_name == old_name:
            return
        if not self.service.config.rename_group(group_id, new_name):
            InfoBar.warning("提示", f"分组「{new_name}」已存在", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return
        self._refresh_conn_list(self.search_edit.text() if hasattr(self, "search_edit") else "")
        InfoBar.success("成功", f"已将分组改为「{new_name}」", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _move_connection_to_group(self, connection_id: str, group_id: str):
        index = self.service.index_for_connection_id(connection_id)
        if index is None:
            return
        conn = self.service.connections[index]
        group = self.service.config.group_by_id(group_id)
        if group is None or conn.group_id == group_id:
            return
        conn.group_id = group_id
        self.service.config.save()
        self._refresh_conn_list(self.search_edit.text() if hasattr(self, "search_edit") else "")
        InfoBar.success("已移动", f"{conn.name or conn.host} -> {group.name}", parent=self, position=InfoBarPosition.TOP_RIGHT)

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
        groups = self._groups()
        if not conns and not groups:
            label = BodyLabel("暂无连接\n点击「+ 添加」开始")
            label.setAlignment(Qt.AlignCenter)
            theme.set_label_color(label, "#94a3b8")
            label.setStyleSheet("padding: 48px 0; background: transparent; line-height: 1.5;")
            self.conn_layout.insertWidget(0, label)
            return

        keyword = filter_text.lower().strip()
        grouped: dict[str, list[tuple[int, object]]] = {group.id: [] for group in groups}
        group_by_id = {group.id: group for group in groups}
        for index, conn in enumerate(conns):
            group = group_by_id.get(conn.group_id)
            if group is None:
                group = self.service.config.group_by_id(self.service.config.default_group_id())
                conn.group_id = group.id
                group_by_id[group.id] = group
                grouped.setdefault(group.id, [])
            group_name = group.name
            haystack = " ".join([conn.name, conn.host, conn.database or "", group_name]).lower()
            if keyword and keyword not in haystack:
                continue
            grouped.setdefault(group.id, []).append((index, conn))

        grouped = {group_id: items for group_id, items in grouped.items() if items or not keyword}
        if not grouped:
            label = BodyLabel("没有匹配的连接")
            label.setAlignment(Qt.AlignCenter)
            theme.set_label_color(label, "#94a3b8")
            label.setStyleSheet("padding: 48px 0; background: transparent;")
            self.conn_layout.insertWidget(0, label)
            return

        for group_id in sorted(grouped, key=lambda item: group_by_id[item].name if item in group_by_id else item):
            group = group_by_id.get(group_id)
            if group is None:
                continue
            items = grouped[group_id]
            enabled = sum(1 for _, conn in items if conn.enabled)
            collapsed = not keyword and group.collapsed
            self._add_group_header(group, len(items), enabled, collapsed)
            if collapsed:
                continue
            for index, conn in items:
                card = ConnCard(conn, index, self._show_conn_menu)
                card_wrap = QWidget()
                card_wrap.setStyleSheet("background: transparent; border: none;")
                card_lay = QHBoxLayout(card_wrap)
                card_lay.setContentsMargins(18, 0, 6, 0)
                card_lay.setSpacing(0)
                card_lay.addWidget(card)
                self.conn_layout.insertWidget(self.conn_layout.count() - 1, card_wrap)

    def _on_conn_search(self, text: str):
        self._refresh_conn_list(text)

    def _show_conn_menu(self, connection_id: str):
        index = self.service.index_for_connection_id(connection_id)
        if index is None:
            return
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
        menu.addAction("编辑连接", lambda: self._on_edit(connection_id))
        menu.addAction("测试连接", lambda: self._on_test(connection_id))
        move_menu = menu.addMenu("移动到分组")
        for group in self._groups():
            move_menu.addAction(group.name, lambda checked=False, gid=group.id: self._move_connection_to_group(connection_id, gid))
        move_menu.addSeparator()
        move_menu.addAction("新建分组...", lambda: self._move_connection_to_new_group(connection_id))
        toggle_text = "禁用" if conn.enabled else "启用"
        menu.addAction(toggle_text, lambda: self._on_toggle(connection_id))
        menu.addSeparator()
        delete_action = menu.addAction("删除", lambda: self._on_remove(connection_id))
        delete_action.setObjectName("deleteAction")
        menu.exec_(self.cursor().pos())

    def _move_connection_to_new_group(self, connection_id: str):
        dialog = GroupDialog(self, "新建分组")
        if dialog.exec_() != QDialog.Accepted or not dialog.result:
            return
        group = self.service.config.add_group(dialog.result)
        if group is None:
            InfoBar.warning("提示", f"分组「{dialog.result}」已存在", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return
        self._move_connection_to_group(connection_id, group.id)

    def _on_add(self):
        dialog = ConnDialog(self, ConnectionConfig(), "添加连接", self.service)
        if dialog.exec_() == QDialog.Accepted and dialog.result:
            self.service.add(dialog.result)
            self._refresh_conn_list()
            InfoBar.success("成功", f"已添加连接 \"{dialog.result.name}\"", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _on_edit(self, connection_id: str):
        index = self.service.index_for_connection_id(connection_id)
        if index is None:
            return
        dialog = ConnDialog(self, self.service.connections[index], "编辑连接", self.service)
        if dialog.exec_() == QDialog.Accepted and dialog.result:
            self.service.update(index, dialog.result)
            self._refresh_conn_list()
            InfoBar.success("成功", f"已更新连接 \"{dialog.result.name}\"", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _on_test(self, connection_id: str):
        index = self.service.index_for_connection_id(connection_id)
        if index is None:
            return
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

    def _on_test_finished(self, ok: bool, msg: str, connection_id: str):
        index = self.service.index_for_connection_id(connection_id)
        conn_name = connection_id
        if index is not None:
            conn = self.service.connections[index]
            conn_name = conn.name or conn.host
        if ok:
            InfoBar.success("连接成功", f"{conn_name}: {msg}", parent=self, position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.error("连接失败", f"{conn_name}: {msg}", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _on_test_thread_finished(self, ok: bool, msg: str, connection_id: str):
        for index, conn in enumerate(self.service.connections):
            if conn.id == connection_id:
                self.service.config.connections[index].last_test_ok = ok
                self.service.config.save()
                self._refresh_conn_list()
                break
        self.progress.setMaximum(1)
        self.progress.setValue(1)
        self.progress_frame.hide()

    def _on_toggle(self, connection_id: str):
        self.service.toggle_by_id(connection_id)
        self._refresh_conn_list()

    def _on_remove(self, connection_id: str):
        index = self.service.index_for_connection_id(connection_id)
        if index is None:
            return
        conn = self.service.connections[index]
        dialog = MessageBox("确认删除", f"确定要删除连接 \"{conn.name}\" 吗？", self)
        if dialog.exec_() == Dialog.Accepted:
            self.service.remove_by_id(connection_id)
            self._refresh_conn_list()
            InfoBar.success("成功", "已删除连接", parent=self, position=InfoBarPosition.TOP_RIGHT)
