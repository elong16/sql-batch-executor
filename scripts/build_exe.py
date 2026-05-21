from __future__ import annotations

import os
import struct
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "SqlPulse"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
ICON_PNG = ROOT / "assets" / "app_icon.png"
ICON_SVG = ROOT / "assets" / "app_icon.svg"
ICON_ICO = BUILD_DIR / "app_icon.ico"


def _png_bytes(image: QImage) -> bytes:
    from PyQt5.QtCore import QBuffer, QByteArray, QIODevice

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError("Failed to encode PNG icon frame")
    buffer.close()
    return bytes(data)


def _write_multi_size_ico(source: QImage, output_path: Path) -> None:
    sizes = (16, 24, 32, 48, 64, 128, 256)
    frames: list[tuple[int, bytes]] = []
    for size in sizes:
        frame = source.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        canvas = QImage(size, size, QImage.Format_ARGB32)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.drawImage((size - frame.width()) // 2, (size - frame.height()) // 2, frame)
        painter.end()
        frames.append((size, _png_bytes(canvas)))

    header_size = 6 + len(frames) * 16
    offset = header_size
    directory = bytearray()
    payload = bytearray()
    for size, data in frames:
        directory.extend(
            struct.pack(
                "<BBBBHHII",
                0 if size == 256 else size,
                0 if size == 256 else size,
                0,
                0,
                1,
                32,
                len(data),
                offset,
            )
        )
        payload.extend(data)
        offset += len(data)

    with output_path.open("wb") as file:
        file.write(struct.pack("<HHH", 0, 1, len(frames)))
        file.write(directory)
        file.write(payload)


def make_icon() -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if ICON_PNG.exists():
        image = QImage(str(ICON_PNG))
        if image.isNull():
            raise RuntimeError(f"Invalid icon file: {ICON_PNG}")
        image = image.convertToFormat(QImage.Format_ARGB32)
    else:
        image = QImage(256, 256, QImage.Format_ARGB32)
        image.fill(Qt.transparent)

        painter = QPainter(image)
        renderer = QSvgRenderer(str(ICON_SVG))
        if not renderer.isValid():
            raise RuntimeError(f"Invalid icon file: {ICON_SVG}")
        renderer.render(painter, QRectF(0, 0, 256, 256))
        painter.end()

    _write_multi_size_ico(image, ICON_ICO)
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
