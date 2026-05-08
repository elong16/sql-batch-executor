from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "SQL批量执行器"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
ICON_SVG = ROOT / "assets" / "app_icon.svg"
ICON_ICO = BUILD_DIR / "app_icon.ico"


def make_icon() -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    image = QImage(256, 256, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    renderer = QSvgRenderer(str(ICON_SVG))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid icon file: {ICON_SVG}")
    renderer.render(painter, QRectF(0, 0, 256, 256))
    painter.end()

    if not image.save(str(ICON_ICO), "ICO"):
        raise RuntimeError(f"Failed to write icon: {ICON_ICO}")
    return ICON_ICO


def build() -> None:
    icon_path = make_icon()
    add_data = f"{ROOT / 'assets'}{os.pathsep}assets"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR / "pyinstaller"),
        "--specpath",
        str(BUILD_DIR),
        "--icon",
        str(icon_path),
        "--add-data",
        add_data,
        "--collect-all",
        "qfluentwidgets",
        "--collect-all",
        "qframelesswindow",
        str(ROOT / "main.py"),
    ]

    subprocess.run(command, cwd=ROOT, check=True)
    print(f"\nEXE: {DIST_DIR / (APP_NAME + '.exe')}")


if __name__ == "__main__":
    build()
