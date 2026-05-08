import json
from pathlib import Path

from sql_batch_executor.app.resources import data_path


PREFERENCES_FILE = "preferences.json"
DEFAULT_THEME_COLOR = "blue"


class PreferenceManager:
    def __init__(self, preferences_path: str | Path | None = None):
        self.preferences_path = Path(preferences_path) if preferences_path else data_path(PREFERENCES_FILE)
        self.preferences = self.load()

    def load(self) -> dict:
        if not self.preferences_path.exists():
            return {}
        try:
            with self.preferences_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self):
        self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
        with self.preferences_path.open("w", encoding="utf-8") as file:
            json.dump(self.preferences, file, ensure_ascii=False, indent=2)

    def theme_color(self) -> str:
        return str(self.preferences.get("theme_color", DEFAULT_THEME_COLOR) or DEFAULT_THEME_COLOR)

    def set_theme_color(self, color_key: str):
        if not color_key:
            color_key = DEFAULT_THEME_COLOR
        self.preferences["theme_color"] = color_key
        self.save()
