from PyQt5.QtCore import Qt, QThread
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout

from qfluentwidgets import Dialog, InfoBar, InfoBarPosition

from sql_batch_executor.database.manager import ExecutionResult
from sql_batch_executor.ui import theme
from sql_batch_executor.ui.connection_widgets import ExecSelectDialog
from sql_batch_executor.ui.workers import SqlExecutionWorker


class DangerousSqlDialog(QDialog):
    def __init__(
        self,
        operations: list[str],
        detail_lines: list[str],
        target_count: int,
        statement_count: int,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("危险 SQL 确认")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setStyleSheet(f"""
            QDialog {{
                background: {theme.SURFACE};
                color: {theme.TEXT_PRIMARY};
            }}
            QLabel {{
                color: {theme.TEXT_PRIMARY};
                background: transparent;
            }}
            QTextEdit {{
                background: {theme.EDITOR_BG};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 8px;
                font-family: {theme.EDITOR_FONT};
            }}
            QPushButton {{
                min-width: 88px;
                min-height: 32px;
                border-radius: 7px;
                padding: 6px 16px;
                font-weight: 600;
            }}
            QPushButton#dangerConfirmButton {{
                background: {theme.DANGER};
                color: white;
                border: 1px solid {theme.DANGER};
            }}
            QPushButton#dangerConfirmButton:hover {{
                background: #b91c1c;
                border-color: #b91c1c;
            }}
            QPushButton#dangerCancelButton {{
                background: {theme.SURFACE_SUBTLE};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
            }}
            QPushButton#dangerCancelButton:hover {{
                background: {theme.PRIMARY_SOFT};
                border-color: {theme.PRIMARY_BORDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        title = QLabel("检测到危险 SQL 操作")
        title.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {theme.DANGER};")
        layout.addWidget(title)

        summary = QLabel(
            f"操作类型：{', '.join(operations)}\n"
            f"本次会向 {target_count} 个连接发送 {statement_count} 条 SQL。"
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        detail = QTextEdit()
        detail.setReadOnly(True)
        detail.setMinimumHeight(130)
        detail.setPlainText("\n".join(detail_lines))
        layout.addWidget(detail)

        note = QLabel("请确认你已经备份或确认影响范围。")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent;")
        layout.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("dangerCancelButton")
        confirm_button = QPushButton("确认执行")
        confirm_button.setObjectName("dangerConfirmButton")
        cancel_button.clicked.connect(self.reject)
        confirm_button.clicked.connect(self.accept)
        buttons.addWidget(cancel_button)
        buttons.addWidget(confirm_button)
        layout.addLayout(buttons)

        cancel_button.setDefault(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)


class ExecutionMixin:
    def _on_execute(self):
        sql = self.sql_input.toPlainText().strip()
        if not sql:
            InfoBar.warning("提示", "请输入 SQL 语句", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return
        statements = self.service.split_sql(sql)
        if not statements:
            InfoBar.warning("提示", "没有可执行 SQL", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return
        enabled = self.service.enabled_connections()
        if not enabled:
            InfoBar.warning("提示", "没有可用的数据库连接", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return

        dialog = ExecSelectDialog(self, enabled)
        if dialog.exec_() != Dialog.Accepted or not dialog.selected:
            return

        targets = self.service.resolve_targets(enabled, dialog.selected)
        if not self._confirm_dangerous_sql(sql, len(targets), len(statements)):
            return
        total = len(targets) * len(statements)
        continue_on_error = self.continue_on_error_check.isChecked()

        self.exec_btn.setEnabled(False)
        self.exec_btn.setText("执行中...")
        self.progress.setValue(0)
        self.progress.setMaximum(total)
        self.progress_frame.show()
        self.cancel_btn.show()
        self._result_targets = list(targets)
        self.results = [
            ExecutionResult(
                connection_name=target.name or target.host,
                success=False,
                message="等待执行",
                statements_total=len(statements),
            )
            for target in targets
        ]
        self._show_results()

        thread = QThread(self)
        worker = SqlExecutionWorker(self.service.database, targets, sql, continue_on_error)
        worker.moveToThread(thread)
        self._current_worker = worker
        thread.started.connect(worker.run)
        worker.status_changed.connect(self._on_execute_status_changed)
        worker.progress_changed.connect(self._on_execute_progress_changed)
        worker.statement_finished.connect(self._on_statement_finished)
        worker.connection_finished.connect(self._on_connection_finished)
        worker.finished.connect(lambda results, executed_sql=sql: self._on_execute_finished(results, executed_sql))
        worker.cancelled.connect(self._on_execute_cancelled)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: setattr(self, "_current_worker", None))
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

        dialog = DangerousSqlDialog(operations, detail_lines, target_count, statement_count, self)
        return dialog.exec_() == QDialog.Accepted

    def _on_cancel_execute(self):
        if self._current_worker:
            self._current_worker.cancel()

    def _on_execute_status_changed(self, text: str):
        self.status_label.setText(text)
        theme.set_label_color(self.status_label, theme.TEXT_SUBTLE)

    def _on_execute_progress_changed(self, current: int, total: int, result):
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def _on_statement_finished(self, target_index: int, statement_result):
        if not (0 <= target_index < len(self.results)):
            return
        result = self.results[target_index]
        result.statement_results.append(statement_result)
        result.statements_total = max(result.statements_total, statement_result.index)
        result.message = f"执行中: SQL {statement_result.index}/{result.statements_total}"
        result.rows_affected = sum(max(item.rows_affected, 0) for item in result.statement_results)
        if statement_result.columns:
            result.columns = statement_result.columns
            result.data = statement_result.data
        if self.result_stack.currentIndex() == 0:
            self._show_results()
        else:
            self._refresh_result_view(target_index)

    def _on_connection_finished(self, target_index: int, result: ExecutionResult):
        if not (0 <= target_index < len(self.results)):
            return
        self.results[target_index] = result
        if self.result_stack.currentIndex() == 0:
            self._show_results()
        else:
            self._refresh_result_view(target_index)

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
            InfoBar.warning("已取消", f"已保留当前执行结果{history_note}", parent=self, position=InfoBarPosition.TOP_RIGHT)
        elif summary.success == summary.total:
            self.status_label.setText(f"完成: {summary.success}/{summary.total} 成功")
            theme.set_label_color(self.status_label, theme.SUCCESS)
            InfoBar.success(
                "执行完成",
                f"{summary.success}/{summary.total} 个连接执行成功{statement_note}{history_note}",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
            )
        else:
            self.status_label.setText(f"完成: {summary.success}/{summary.total} 成功")
            theme.set_label_color(self.status_label, theme.DANGER)
            InfoBar.error("执行完成", f"{summary.failed} 个连接执行失败{statement_note}", parent=self, position=InfoBarPosition.TOP_RIGHT)
        self._show_results()
