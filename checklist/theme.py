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
        "* { font-family: 'Helvetica Neue', Helvetica, Arial; }"
        " QMainWindow { background-color: #ffffff; }"
        " QWidget { background-color: transparent; color: #333333; font-size: 13px; }"
        " QSplitter::handle { background-color: #e0e0e0; width: 1px; }"
        " QScrollArea { border: none; background-color: #ffffff; }"
        " QScrollBar:vertical { background: #f3f3f3; width: 8px; margin: 0; }"
        " QScrollBar::handle:vertical { background: #d0d0d0; min-height: 30px;"
        " border-radius: 4px; }"
        " QScrollBar::handle:vertical:hover { background: #aaaaaa; }"
        " QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        " QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }"
        " QToolTip { background-color: #f9f9f9; color: #333333;"
        " border: 1px solid #e0e0e0; padding: 4px 6px; border-radius: 4px; }"
        " QMenu { background-color: #ffffff; border: 1px solid #e0e0e0;"
        " border-radius: 8px; padding: 4px; font-size: 13px; }"
        " QMenu::item { padding: 6px 20px 6px 14px; border-radius: 4px; color: #333333; }"
        " QMenu::item:selected { background-color: #ebebeb; color: #111111; }"
        " QMenu::item:disabled { color: #bbbbbb; }"
        " QMenu::separator { height: 1px; background: #ebebeb; margin: 3px 6px; }"
        " QMenu QMenu { margin-left: -4px; }"
    )


def sidebar_qss() -> str:
    return (
        "QWidget#sidebar { background-color: #f7f7f7; }"
        " QLabel#sidebarTitle { font-weight: 600; font-size: 10px; color: #8a8a8a;"
        " padding: 14px 12px 6px 12px; letter-spacing: 1.2px;"
        " qproperty-alignment: AlignCenter; }"
        " QListWidget { background-color: #f7f7f7; border: none;"
        " outline: none; padding: 2px 6px; }"
        " QListWidget::item { padding: 7px 10px; border-radius: 6px;"
        " color: #333333; font-size: 13px; }"
        " QListWidget::item:selected { background-color: #e4e4e4; }"
        " QListWidget::item:hover:!selected { background-color: #eeeeee; }"
        " QPushButton#sidebarBtn { background-color: #ffffff;"
        " border: 1px solid #e0e0e0; border-radius: 6px; padding: 6px 14px;"
        " color: #444444; font-size: 12px; font-weight: 500; }"
        " QPushButton#sidebarBtn:hover { background-color: #f0f0f0;"
        " border-color: #cccccc; }"
        " QPushButton#sidebarBtn:pressed { background-color: #e8e8e8; }"
        " QPushButton#statesBtn { background-color: #ffffff;"
        " border: 1px solid #e0e0e0; border-radius: 6px; padding: 6px 14px;"
        " color: #666666; font-size: 12px; font-weight: 500; }"
        " QPushButton#statesBtn:hover { background-color: #f0f0f0;"
        " border-color: #cccccc; color: #333333; }"
        " QPushButton#statesBtn:pressed { background-color: #e8e8e8; }"
    )
