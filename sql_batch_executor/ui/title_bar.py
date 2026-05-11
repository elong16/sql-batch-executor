from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from qfluentwidgets import MSFluentTitleBar

from sql_batch_executor.ui import theme
from sql_batch_executor.ui.icons import app_icon_pixmap


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
        self.iconLabel.setPixmap(app_icon_pixmap(20))
        self.iconLabel.show()
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
        self.controlGroup.setStyleSheet("""
            #windowControlGroup {
                background: transparent;
                border: none;
            }
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
        window = self.window()
        if window.isMaximized():
            if hasattr(window, "restore_normal_window"):
                window.restore_normal_window()
            else:
                window.showNormal()
        else:
            if hasattr(window, "_remember_normal_geometry"):
                window._remember_normal_geometry()
            window.showMaximized()
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
