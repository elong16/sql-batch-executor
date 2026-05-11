import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    return resource_dir().joinpath(*parts)


def data_path(filename: str) -> Path:
    return app_dir() / filename


BASE_DIR = app_dir()
APP_ICON_PATH = resource_path("assets", "app_icon.svg")
APP_ICON_ICO_PATH = resource_path("assets", "app_icon.ico")
