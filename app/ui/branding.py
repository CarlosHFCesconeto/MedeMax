"""Brand assets: source checkout, bundled EXE and optional external logos."""
from pathlib import Path
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel


def asset_path(name):
    if Path(name).name != name:
        raise ValueError('Nome de recurso inválido')
    root = Path(__file__).resolve().parents[2]
    locations = []
    if getattr(sys, 'frozen', False):
        external = Path(sys.executable).resolve().parent
        locations.extend((external / 'assets' / name, external / name))
    locations.extend((root / 'assets' / name, root / name))
    return next((p for p in locations if p.is_file()), None)


def logo(name, width, height, accessible_name):
    label = QLabel()
    label.setAccessibleName(accessible_name)
    label.setAlignment(Qt.AlignCenter)
    label.setFixedSize(width, height)
    label.setStyleSheet('background: transparent; border: none;')
    path = asset_path(name)
    pixmap = QPixmap(str(path)) if path else QPixmap()
    if not pixmap.isNull():
        label.setPixmap(pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    else:
        label.setText(accessible_name)
    return label
