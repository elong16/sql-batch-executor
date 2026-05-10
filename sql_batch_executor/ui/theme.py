from dataclasses import dataclass, replace


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
    primary_border: str = "#bfdbfe"
    selected_bg: str = "#dbeafe"
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


@dataclass(frozen=True)
class ThemeColorPreset:
    name: str
    primary: str
    primary_hover: str
    primary_pressed: str
    primary_soft: str
    primary_border: str  # derived
    selected_bg: str  # derived


DEFAULT_THEME_COLOR = "blue"
THEME_COLOR_PRESETS: dict[str, ThemeColorPreset] = {
    "blue": ThemeColorPreset("蓝色", "#2563eb", "#1d4ed8", "#1e40af", "#dbeafe", "#bfdbfe", "#dbeafe"),
    "cyan": ThemeColorPreset("青色", "#0891b2", "#0e7490", "#155e75", "#cffafe", "#a5f3fc", "#cffafe"),
    "green": ThemeColorPreset("绿色", "#059669", "#047857", "#065f46", "#d1fae5", "#6ee7b7", "#d1fae5"),
    "violet": ThemeColorPreset("紫色", "#7c3aed", "#6d28d9", "#5b21b6", "#ede9fe", "#c4b5fd", "#ede9fe"),
    "orange": ThemeColorPreset("橙色", "#ea580c", "#c2410c", "#9a3412", "#ffedd5", "#fdba74", "#ffedd5"),
    "rose": ThemeColorPreset("玫红", "#e11d48", "#be123c", "#9f1239", "#ffe4e6", "#fda4af", "#ffe4e6"),
}


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


_BASE_THEME = ThemeTokens()
_current_theme_color = DEFAULT_THEME_COLOR
THEME = _BASE_THEME
STYLE_FACTORY = StyleSheetFactory(THEME)


def _sync_exports():
    global APP_BACKGROUND, APP_CHROME, SURFACE, SURFACE_SUBTLE, BORDER, STRONG_BORDER
    global TEXT_PRIMARY, TEXT_MUTED, TEXT_SUBTLE, PRIMARY, PRIMARY_HOVER, PRIMARY_PRESSED
    global PRIMARY_SOFT, SUCCESS, SUCCESS_SOFT, DANGER, DANGER_SOFT, WARNING, WARNING_SOFT
    global SIDEBAR_BG, SIDEBAR_SURFACE, SIDEBAR_BORDER, EDITOR_BG, EDITOR_PANEL, EDITOR_TEXT
    global EDITOR_FONT, PRIMARY_BORDER, SELECTED_BG

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
    PRIMARY_BORDER = THEME.primary_border
    SELECTED_BG = THEME.selected_bg


def apply_theme_color(color_key: str) -> ThemeColorPreset:
    global THEME, STYLE_FACTORY, _current_theme_color

    normalized = color_key if color_key in THEME_COLOR_PRESETS else DEFAULT_THEME_COLOR
    preset = THEME_COLOR_PRESETS[normalized]
    THEME = replace(
        _BASE_THEME,
        primary=preset.primary,
        primary_hover=preset.primary_hover,
        primary_pressed=preset.primary_pressed,
        primary_soft=preset.primary_soft,
        primary_border=preset.primary_border,
        selected_bg=preset.selected_bg,
    )
    STYLE_FACTORY = StyleSheetFactory(THEME)
    _current_theme_color = normalized
    _sync_exports()
    return preset


def current_theme_color() -> str:
    return _current_theme_color


_sync_exports()


def set_label_color(label, color: str):
    label.setTextColor(color, color)


def pill_style(fg: str, bg: str):
    return STYLE_FACTORY.pill(fg, bg)


def primary_button_qss():
    return STYLE_FACTORY.primary_button()
