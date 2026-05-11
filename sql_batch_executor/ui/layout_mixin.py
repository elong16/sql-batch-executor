from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from qfluentwidgets import (
    CaptionLabel,
    CheckBox,
    LineEdit,
    PlainTextEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SimpleCardWidget,
    TransparentPushButton,
)

from sql_batch_executor.ui import theme


class LayoutMixin:
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
        sql_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {theme.TEXT_PRIMARY}; background: transparent; border: none;"
        )
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
        overview_lay.addWidget(QLabel("连接"))
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
        sec_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {theme.TEXT_PRIMARY}; background: transparent; border: none;"
        )
        sec_row.addWidget(sec_lbl)
        sec_row.addStretch()
        group_btn = PushButton("+ 分组")
        group_btn.setFixedSize(76, 34)
        group_btn.setStyleSheet(self._theme_button_style())
        group_btn.clicked.connect(self._on_add_group)
        sec_row.addWidget(group_btn)
        add_btn = PrimaryPushButton("+ 添加")
        add_btn.setFixedSize(84, 34)
        add_btn.setStyleSheet(theme.primary_button_qss())
        add_btn.clicked.connect(self._on_add)
        sec_row.addWidget(add_btn)
        sb_lay.addLayout(sec_row)
        sb_lay.addSpacing(8)

        self.search_edit = LineEdit()
        self.search_edit.setPlaceholderText("搜索连接...")
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
        ttl.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; background: transparent; font-size: 18px; font-weight: 700;")
        title_col.addWidget(ttl)
        hint = QLabel("选择目标连接后执行，结果在下方查看")
        hint.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent; font-size: 12px;")
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
        self.sql_input.setPlaceholderText("输入要执行的 SQL 语句...")
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
        editor_wrap.setStyleSheet("background: transparent; border: none;")
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
        empty_card_lay.addWidget(txt)
        desc = QLabel("输入 SQL 并执行后，这里会显示各连接的执行结果。")
        desc.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED}; background: transparent;")
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
