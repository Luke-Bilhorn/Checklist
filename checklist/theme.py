from __future__ import annotations

from PySide6.QtGui import QColor

BG_PRIMARY = "#ffffff"
BG_SECONDARY = "#f3f3f3"
BG_HOVER = "#e8e8e8"
BG_SELECTED = "#e0e0e0"
BG_INPUT = "#ffffff"
TEXT_PRIMARY = "#333333"
TEXT_SECONDARY = "#6e6e6e"
TEXT_MUTED = "#aaaaaa"
BORDER = "#e0e0e0"
ACCENT = "#505050"

MIME_ITEM = "application/x-checklist-item"


def blend_with_bg(color_hex: str, alpha: float = 0.10) -> str:
    fg = QColor(color_hex)
    bg = QColor(BG_PRIMARY)
    r = int(fg.red() * alpha + bg.red() * (1 - alpha))
    g = int(fg.green() * alpha + bg.green() * (1 - alpha))
    b = int(fg.blue() * alpha + bg.blue() * (1 - alpha))
    return QColor(r, g, b).name()


def global_qss() -> str:
    return (
        "* { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }"
        " QMainWindow { background-color: #ffffff; }"
        " QWidget { background-color: transparent; color: #333333; font-size: 13px; }"
        " QSplitter::handle { background-color: #e0e0e0; width: 1px; }"
        " QScrollArea { border: none; background-color: #ffffff; }"
        " QScrollBar:vertical { background: #f3f3f3; width: 10px; margin: 0; }"
        " QScrollBar::handle:vertical { background: #c1c1c1; min-height: 30px;"
        " border-radius: 5px; }"
        " QScrollBar::handle:vertical:hover { background: #a0a0a0; }"
        " QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        " QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical"
        " { background: none; }"
        " QToolTip { background-color: #f3f3f3; color: #333333;"
        " border: 1px solid #e0e0e0; padding: 4px; }"
    )


def sidebar_qss() -> str:
    return (
        "QWidget#sidebar { background-color: #f3f3f3; }"
        " QLabel#sidebarTitle { font-weight: 600; font-size: 11px; color: #6e6e6e;"
        " padding: 12px 12px 4px 12px; letter-spacing: 1px; }"
        " QListWidget { background-color: #f3f3f3; border: none;"
        " outline: none; padding: 2px 4px; }"
        " QListWidget::item { padding: 6px 12px; border-radius: 4px;"
        " color: #333333; }"
        " QListWidget::item:selected { background-color: #e0e0e0; }"
        " QListWidget::item:hover:!selected { background-color: #e8e8e8; }"
        " QPushButton#sidebarBtn { background-color: transparent;"
        " border: 1px solid #d0d0d0; border-radius: 4px; padding: 5px 12px;"
        " color: #333333; font-size: 12px; }"
        " QPushButton#sidebarBtn:hover { background-color: #e8e8e8;"
        " border-color: #bbb; }"
        " QPushButton#statesBtn { background-color: transparent; border: none;"
        " padding: 5px 12px; color: #6e6e6e; font-size: 12px; }"
        " QPushButton#statesBtn:hover { color: #333333; }"
    )
