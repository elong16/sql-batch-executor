from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    app_background: str = "#f3f6fa"
    app_chrome: str = "#f8fafc"
    surface: str = "#ffffff"
    surface_subtle: str = "#f6f8fb"
    border: str = "#d8e0ea"
    strong_border: str = "#c8d2df"
    text_primary: str = "#0f172a"
    text_muted: str = "#64748b"
    text_subtle: str = "#94a3b8"
    primary: str = "#2563eb"
    primary_hover: str = "#1d4ed8"
    primary_pressed: str = "#1e40af"
    primary_soft: str = "#e8f1ff"
    success: str = "#16a34a"
    success_soft: str = "#dcfce7"
    danger: str = "#dc2626"
    danger_soft: str = "#fee2e2"
    warning: str = "#d97706"
    warning_soft: str = "#fef3c7"
    editor_bg: str = "#fbfcfe"
    editor_panel: str = "#ffffff"
    editor_text: str = "#111827"
    editor_font: str = '"Cascadia Code", "Consolas", monospace'


class StyleSheetFactory:
    def __init__(self, tokens: ThemeTokens = ThemeTokens()):
        self.tokens = tokens

    def pill(self, fg: str, bg: str) -> str:
        return f"""
            QLabel {{
                color: {fg};
                background: {bg};
                border-radius: 10px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 600;
            }}
        """

    def primary_button(self) -> str:
        t = self.tokens
        return f"""
            PrimaryPushButton {{
                background: {t.primary};
                color: #ffffff;
                border: 1px solid {t.primary};
                border-radius: 7px;
                font-weight: 600;
            }}
            PrimaryPushButton:hover {{
                background: {t.primary_hover};
                border-color: {t.primary_hover};
            }}
            PrimaryPushButton:pressed {{
                background: {t.primary_pressed};
                border-color: {t.primary_pressed};
            }}
            PrimaryPushButton:disabled {{
                background: #cbd5e1;
                border-color: #cbd5e1;
                color: #f8fafc;
            }}
        """


THEME = ThemeTokens()
STYLE_FACTORY = StyleSheetFactory(THEME)

APP_BACKGROUND = THEME.app_background
APP_CHROME = THEME.app_chrome
SURFACE = THEME.surface
SURFACE_SUBTLE = THEME.surface_subtle
BORDER = THEME.border
STRONG_BORDER = THEME.strong_border
TEXT_PRIMARY = THEME.text_primary
TEXT_MUTED = THEME.text_muted
TEXT_SUBTLE = THEME.text_subtle
PRIMARY = THEME.primary
PRIMARY_HOVER = THEME.primary_hover
PRIMARY_PRESSED = THEME.primary_pressed
PRIMARY_SOFT = THEME.primary_soft
SUCCESS = THEME.success
SUCCESS_SOFT = THEME.success_soft
DANGER = THEME.danger
DANGER_SOFT = THEME.danger_soft
WARNING = THEME.warning
WARNING_SOFT = THEME.warning_soft
SIDEBAR_BG = SURFACE
SIDEBAR_SURFACE = APP_CHROME
SIDEBAR_BORDER = BORDER
EDITOR_BG = THEME.editor_bg
EDITOR_PANEL = THEME.editor_panel
EDITOR_TEXT = THEME.editor_text
EDITOR_FONT = THEME.editor_font


def set_label_color(label, color: str):
    label.setTextColor(color, color)


def pill_style(fg: str, bg: str):
    return STYLE_FACTORY.pill(fg, bg)


def primary_button_qss():
    return STYLE_FACTORY.primary_button()
