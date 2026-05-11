from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QCursor, QKeySequence
from PyQt5.QtWidgets import QApplication, QAbstractItemView, QFrame, QHBoxLayout, QLabel, QMenu, QStackedWidget, QTableWidgetItem, QVBoxLayout, QWidget

from qfluentwidgets import BodyLabel, CaptionLabel, PushButton, ScrollArea, SimpleCardWidget, SubtitleLabel, TableWidget

from sql_batch_executor.database.manager import ExecutionResult, StatementExecutionResult
from sql_batch_executor.ui import theme


class ResultsMixin:
    def _result_tab_icon(self, result: ExecutionResult) -> str:
        if result.cancelled:
            return "..."
        if result.statement_results and not result.success:
            executed = len(result.statement_results)
            if executed < result.statements_total and all(item.success for item in result.statement_results):
                return "..."
        if not result.statement_results and result.statements_total:
            return "..."
        return "OK" if result.success else "X"

    def _show_results(self):
        while self._results_lay.count():
            item = self._results_lay.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

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
        summary_lay.addWidget(SubtitleLabel("执行结果"))
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

        for index, result in enumerate(self.results):
            icon = self._result_tab_icon(result)
            button = PushButton(f"  {icon} {result.connection_name}")
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(36)
            button.setStyleSheet(self._tab_style(index == 0))
            button.clicked.connect(lambda checked, idx=index: self._select_tab(idx))
            tab_lay.addWidget(button)
            self._tab_buttons.append(button)

        tab_lay.addStretch()
        self._results_lay.addWidget(tab_bar)

        self._content_stack = QStackedWidget()
        self._content_stack.setStyleSheet("background: transparent; border: none;")
        placeholder = QWidget()
        placeholder.setStyleSheet("background: transparent;")
        self._content_stack.addWidget(placeholder)
        self._page_cache = {}
        self._results_lay.addWidget(self._content_stack, 1)

        if self.results:
            self._select_tab(0)

    def _refresh_result_view(self, index: int):
        if not self.results or not hasattr(self, "_content_stack") or self._content_stack is None:
            self._show_results()
            return
        if not (0 <= index < len(self.results)):
            return

        if self._tab_buttons and index < len(self._tab_buttons):
            result = self.results[index]
            icon = self._result_tab_icon(result)
            self._tab_buttons[index].setText(f"  {icon} {result.connection_name}")

        old_page = self._page_cache.pop(index, None)
        was_current = index == self._current_tab
        if old_page is not None:
            stack_index = self._content_stack.indexOf(old_page)
            if stack_index >= 0:
                replacement = self._build_result_page(self.results[index])
                self._content_stack.insertWidget(stack_index, replacement)
                self._content_stack.removeWidget(old_page)
                old_page.deleteLater()
                self._page_cache[index] = replacement
                if was_current:
                    self._content_stack.setCurrentWidget(replacement)
                return

        if was_current:
            self._select_tab(index)

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
        if index not in self._page_cache:
            result = self.results[index]
            page = self._build_result_page(result)
            self._content_stack.addWidget(page)
            self._page_cache[index] = page

        if index != self._current_tab and self._tab_buttons:
            self._tab_buttons[self._current_tab].setStyleSheet(self._tab_style(False))
            self._tab_buttons[index].setStyleSheet(self._tab_style(True))

        self._content_stack.setCurrentIndex(index + 1)
        self._current_tab = index

    def _copy_to_clipboard(self, text: str):
        QApplication.clipboard().setText(text)

    def _make_copyable_label(self, label: QLabel):
        label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        label.setCursor(Qt.IBeamCursor)
        label.setContextMenuPolicy(Qt.CustomContextMenu)
        label.customContextMenuRequested.connect(lambda pos, item=label: self._show_text_context_menu(item, pos))
        label.installEventFilter(self)
        return label

    def _copy_label_text(self, label: QLabel, selected_only: bool = False):
        selected = label.selectedText()
        text = selected if selected_only and selected else selected or label.text()
        text = text.replace("\u2029", "\n")
        if text:
            self._copy_to_clipboard(text)

    def _show_text_context_menu(self, label: QLabel, pos):
        menu = QMenu(label)
        menu.setStyleSheet(f"""
            QMenu {{ background: {theme.SURFACE}; color: {theme.TEXT_PRIMARY};
                     border: 1px solid {theme.BORDER}; border-radius: 8px; padding: 4px; font-size: 12px; }}
            QMenu::item {{ padding: 7px 24px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {theme.PRIMARY_SOFT}; color: {theme.PRIMARY}; }}
            QMenu::item:disabled {{ color: {theme.TEXT_SUBTLE}; }}
        """)
        selected = bool(label.selectedText())
        selected_action = menu.addAction("复制选中文本", lambda: self._copy_label_text(label, selected_only=True))
        selected_action.setEnabled(selected)
        all_action = menu.addAction("复制全部文本", lambda: self._copy_label_text(label))
        all_action.setEnabled(bool(label.text()))
        menu.exec_(label.mapToGlobal(pos))

    def _table_cell_text(self, table: TableWidget, row: int, col: int) -> str:
        item = table.item(row, col)
        return item.text() if item else ""

    def _table_text(self, table: TableWidget, rows, cols, include_headers: bool = False) -> str:
        lines = []
        cols = list(cols)
        if include_headers:
            headers = []
            for col in cols:
                header = table.horizontalHeaderItem(col)
                headers.append(header.text() if header else "")
            lines.append("\t".join(headers))
        for row in rows:
            line = "\t".join(self._table_cell_text(table, row, col) for col in cols)
            lines.append(line)
        return "\n".join(lines)

    def _copy_table_selection(self, table: TableWidget):
        indexes = table.selectedIndexes()
        if not indexes:
            self._copy_table_current_cell(table)
            return
        rows = sorted({index.row() for index in indexes})
        cols = sorted({index.column() for index in indexes})
        self._copy_to_clipboard(self._table_text(table, rows, cols))

    def _copy_table_current_cell(self, table: TableWidget):
        item = table.currentItem()
        if item:
            self._copy_to_clipboard(item.text())

    def _copy_table_all(self, table: TableWidget, include_headers: bool = True):
        rows = range(table.rowCount())
        cols = range(table.columnCount())
        self._copy_to_clipboard(self._table_text(table, rows, cols, include_headers=include_headers))

    def _show_table_context_menu(self, table: TableWidget):
        menu = QMenu(table)
        menu.setStyleSheet(f"""
            QMenu {{ background: {theme.SURFACE}; color: {theme.TEXT_PRIMARY};
                     border: 1px solid {theme.BORDER}; border-radius: 8px; padding: 4px; font-size: 12px; }}
            QMenu::item {{ padding: 7px 24px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {theme.PRIMARY_SOFT}; color: {theme.PRIMARY}; }}
            QMenu::item:disabled {{ color: {theme.TEXT_SUBTLE}; }}
        """)
        selection_action = menu.addAction("复制选中内容", lambda: self._copy_table_selection(table))
        selection_action.setEnabled(bool(table.selectedIndexes()))
        cell_action = menu.addAction("复制当前单元格", lambda: self._copy_table_current_cell(table))
        cell_action.setEnabled(table.currentItem() is not None)
        menu.addSeparator()
        menu.addAction("复制全部结果", lambda: self._copy_table_all(table, include_headers=False))
        menu.addAction("复制全部结果（含表头）", lambda: self._copy_table_all(table, include_headers=True))
        menu.exec_(QCursor.pos())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.matches(QKeySequence.Copy):
            if isinstance(obj, TableWidget):
                self._copy_table_selection(obj)
                return True
            if isinstance(obj, QLabel):
                self._copy_label_text(obj)
                return True
        return super().eventFilter(obj, event)

    def _compact_sql(self, sql: str, limit: int = 320) -> str:
        compact = " ".join(sql.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1] + "..."

    def _create_result_table(self, columns: list[str], data: list[tuple], limit: int = 2000) -> TableWidget:
        table = TableWidget()
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.setRowCount(min(len(data), limit))
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
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
                for col_idx, value in enumerate(row_data):
                    if value is None:
                        text = "NULL"
                    elif isinstance(value, bytes):
                        text = value.decode("utf-8", errors="replace")
                    else:
                        text = str(value)
                    item = QTableWidgetItem(text)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    table.setItem(row_idx, col_idx, item)
            QApplication.processEvents()

        table.resizeColumnsToContents()
        table.installEventFilter(self)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos: self._show_table_context_menu(table))
        return table

    def _build_script_result_page(self, result: ExecutionResult):
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
        title = self._make_copyable_label(SubtitleLabel(result.connection_name))
        header.addWidget(title)
        summary = self._make_copyable_label(CaptionLabel(f"{result.message} · {result.duration_ms:.0f}ms"))
        summary.setWordWrap(True)
        theme.set_label_color(summary, theme.SUCCESS if result.success else theme.DANGER)
        header.addWidget(summary, 1, Qt.AlignRight)
        content_lay.addLayout(header)

        for statement in result.statement_results:
            content_lay.addWidget(self._build_statement_card(statement))

        skipped = result.statements_total - len(result.statement_results)
        if skipped > 0:
            skipped_label = self._make_copyable_label(CaptionLabel(f"后续 {skipped} 条 SQL 未执行"))
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
        title = self._make_copyable_label(SubtitleLabel(f"SQL {statement.index} · 第 {statement.start_line} 行"))
        header.addWidget(title)
        header.addStretch()
        status = self._make_copyable_label(CaptionLabel("成功" if statement.success else "失败"))
        theme.set_label_color(status, theme.SUCCESS if statement.success else theme.DANGER)
        header.addWidget(status)
        duration = self._make_copyable_label(CaptionLabel(f"{statement.duration_ms:.0f}ms"))
        theme.set_label_color(duration, theme.TEXT_MUTED)
        header.addWidget(duration)
        card_lay.addLayout(header)

        preview = self._make_copyable_label(CaptionLabel(self._compact_sql(statement.sql)))
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

        message = self._make_copyable_label(BodyLabel(statement.message))
        message.setWordWrap(True)
        theme.set_label_color(message, theme.SUCCESS if statement.success else theme.DANGER)
        card_lay.addWidget(message)

        if statement.columns:
            table = self._create_result_table(statement.columns, statement.data, limit=500)
            table.setMinimumHeight(150)
            table.setMaximumHeight(320)
            card_lay.addWidget(table)
            if len(statement.data) > 500:
                limit_label = self._make_copyable_label(CaptionLabel("仅显示前 500 行"))
                theme.set_label_color(limit_label, theme.WARNING)
                card_lay.addWidget(limit_label)

        return card

    def _build_result_page(self, result: ExecutionResult):
        if result.statements_total > 1 or len(result.statement_results) > 1:
            return self._build_script_result_page(result)

        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(0)

        if result.success and result.columns:
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
            name = self._make_copyable_label(SubtitleLabel(result.connection_name))
            title_col.addWidget(name)
            info_label = self._make_copyable_label(CaptionLabel(f"{result.message} · {result.duration_ms:.0f}ms"))
            theme.set_label_color(info_label, theme.SUCCESS)
            title_col.addWidget(info_label)
            header.addLayout(title_col)
            header.addStretch()
            rows_label = self._make_copyable_label(CaptionLabel(f"{len(result.data)} 行"))
            theme.set_label_color(rows_label, theme.TEXT_MUTED)
            header.addWidget(rows_label)
            if len(result.data) > 2000:
                limit_label = self._make_copyable_label(CaptionLabel("仅显示前 2000 行"))
                theme.set_label_color(limit_label, theme.WARNING)
                header.addWidget(limit_label)
            container_lay.addLayout(header)

            table = self._create_result_table(result.columns, result.data, limit=2000)
            container_lay.addWidget(table, 1)
            if not result.data:
                empty_note = self._make_copyable_label(CaptionLabel("查询成功，但没有返回数据行。"))
                empty_note.setAlignment(Qt.AlignCenter)
                theme.set_label_color(empty_note, theme.TEXT_MUTED)
                container_lay.addWidget(empty_note)
            layout.addWidget(container, 1)
        else:
            color = theme.SUCCESS if result.success else theme.DANGER
            wrapper = SimpleCardWidget()
            wrapper.setObjectName("resultStatusCard")
            wrapper.setStyleSheet(f"""
                #resultStatusCard {{
                    background: {theme.SURFACE};
                    border: 1px solid {theme.BORDER};
                    border-radius: 10px;
                }}
            """)
            wrapper_lay = QVBoxLayout(wrapper)
            wrapper_lay.setAlignment(Qt.AlignCenter)
            wrapper_lay.setSpacing(8)

            icon = QLabel("OK" if result.success else "X")
            icon.setFixedSize(46, 46)
            icon.setStyleSheet(f"""
                font-size: 26px;
                font-weight: 700;
                color: {color};
                background: transparent;
            """)
            icon.setAlignment(Qt.AlignCenter)
            wrapper_lay.addWidget(icon)

            name = self._make_copyable_label(SubtitleLabel(result.connection_name))
            name.setAlignment(Qt.AlignCenter)
            wrapper_lay.addWidget(name)

            message = self._make_copyable_label(BodyLabel(result.message))
            theme.set_label_color(message, color)
            message.setAlignment(Qt.AlignCenter)
            message.setWordWrap(True)
            wrapper_lay.addWidget(message)

            duration = self._make_copyable_label(CaptionLabel(f"耗时: {result.duration_ms:.0f}ms"))
            theme.set_label_color(duration, theme.TEXT_MUTED)
            duration.setAlignment(Qt.AlignCenter)
            wrapper_lay.addWidget(duration)

            layout.addWidget(wrapper, 1)

        return page
