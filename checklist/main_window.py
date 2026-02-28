from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .checklist_view import ChecklistView
from .config import (
    MAX_MAX_ITEM_WIDTH,
    MIN_MAX_ITEM_WIDTH,
    load_max_item_width,
    save_max_item_width,
)
from .models import Checklist
from .sidebar import SidebarView
from .state_editor import StateEditor
from .theme import sidebar_qss
from .paths import get_data_dir
from .xml_io import list_checklists, load_checklist, save_checklist

_ACTIVITY_W = 44


# ---------------------------------------------------------------------------
# Narrow activity bar — always visible on the far left
# ---------------------------------------------------------------------------

_ACT_BTN_QSS = (
    "QPushButton {{ background: {bg}; border: none; border-radius: 8px; }}"
    " QPushButton:hover {{ background: #dcdcdc; }}"
)


class _ActivityButton(QPushButton):
    """Base class for geometrically-drawn activity bar buttons."""

    def __init__(self, tooltip: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self._active = False
        self._update_ss()
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def set_active_style(self, active: bool):
        self._active = active
        self._update_ss()
        self.update()

    def _update_ss(self):
        bg = "#d0d0d0" if self._active else "transparent"
        self.setStyleSheet(_ACT_BTN_QSS.format(bg=bg))

    def _icon_color(self) -> QColor:
        if self._active or self.underMouse():
            return QColor("#333333")
        return QColor("#888888")

    def enterEvent(self, ev):
        super().enterEvent(ev)
        self.update()

    def leaveEvent(self, ev):
        super().leaveEvent(ev)
        self.update()


class _HamburgerButton(_ActivityButton):
    def __init__(self, parent=None):
        super().__init__("Checklists", parent)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = self._icon_color()
        p.setPen(QPen(col, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        cx = self.width() / 2
        cy = self.height() / 2
        hw = 7
        for dy in (-5, 0, 5):
            p.drawLine(QPointF(cx - hw, cy + dy), QPointF(cx + hw, cy + dy))
        p.end()


class _GearButton(_ActivityButton):
    def __init__(self, parent=None):
        super().__init__("Settings", parent)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = self._icon_color()
        p.setPen(QPen(col, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2, self.height() / 2
        r_out, r_in = 9.0, 6.5
        teeth = 8
        path = QPainterPath()
        for i in range(teeth):
            a1 = math.radians(i * 360 / teeth - 12)
            a2 = math.radians(i * 360 / teeth + 12)
            a3 = math.radians((i + 0.5) * 360 / teeth - 12)
            a4 = math.radians((i + 0.5) * 360 / teeth + 12)
            if i == 0:
                path.moveTo(cx + r_out * math.cos(a1), cy + r_out * math.sin(a1))
            else:
                path.lineTo(cx + r_out * math.cos(a1), cy + r_out * math.sin(a1))
            path.lineTo(cx + r_out * math.cos(a2), cy + r_out * math.sin(a2))
            path.lineTo(cx + r_in * math.cos(a3), cy + r_in * math.sin(a3))
            path.lineTo(cx + r_in * math.cos(a4), cy + r_in * math.sin(a4))
        path.closeSubpath()
        p.drawPath(path)
        p.drawEllipse(QPointF(cx, cy), 3.0, 3.0)
        p.end()


class _ActivityBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(_ACTIVITY_W)
        self.setStyleSheet("QWidget { background: #ebebeb; }")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 10, 6, 10)
        lay.setSpacing(4)

        self.lists_btn = _HamburgerButton()
        lay.addWidget(self.lists_btn)
        self.settings_btn = _GearButton()
        lay.addWidget(self.settings_btn)
        lay.addStretch()

    def set_active(self, which: str | None):
        self.lists_btn.set_active_style(which == "lists")
        self.settings_btn.set_active_style(which == "settings")

    def paintEvent(self, ev):
        super().paintEvent(ev)
        p = QPainter(self)
        p.setPen(QPen(QColor("#d8d8d8"), 1))
        p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        p.end()


# ---------------------------------------------------------------------------
# Delete confirmation dialog — styled to match app
# ---------------------------------------------------------------------------

class _DeleteConfirmDialog(QDialog):
    """Styled confirmation dialog for deleting a checklist."""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Delete")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #ffffff; border: none; border-radius: 10px; }"
        )
        frame.setMinimumWidth(380)
        root = QVBoxLayout(frame)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        msg = QLabel(f'Are you sure you want to delete the list "{name}"?')
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(
            "QLabel { font-size: 13px; color: #333; background: transparent;"
            " border: none; }"
        )
        msg.setWordWrap(True)
        msg.setMinimumWidth(340)
        root.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton { background: #f0f0f0; border: 1px solid #d8d8d8;"
            " border-radius: 6px; padding: 5px 14px; color: #444; font-size: 12px; }"
            " QPushButton:hover { background: #e8e8e8; border-color: #ccc; }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        del_btn = QPushButton("Delete")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(
            "QPushButton { background: #f5f5f5; border: 1px solid #d8d8d8;"
            " border-radius: 6px; padding: 5px 14px; color: #c44; font-size: 12px; }"
            " QPushButton:hover { background: #fee; border-color: #c88; }"
        )
        del_btn.clicked.connect(self.accept)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

    @staticmethod
    def ask(parent: QWidget, name: str) -> bool:
        dlg = _DeleteConfirmDialog(name, parent)
        dlg.adjustSize()
        dlg.move(
            parent.x() + (parent.width() - dlg.width()) // 2,
            parent.y() + (parent.height() - dlg.height()) // 2,
        )
        return dlg.exec() == QDialog.DialogCode.Accepted


# ---------------------------------------------------------------------------
# Inline settings panel (lives in the sidebar stack)
# ---------------------------------------------------------------------------

class _SettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._edit_states_cb = None
        self._max_width_cb = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        title = QLabel("SETTINGS")
        title.setObjectName("sidebarTitle")
        root.addWidget(title)

        body = QVBoxLayout()
        body.setContentsMargins(10, 4, 10, 10)
        body.setSpacing(8)

        # States row
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: #efefef; border-radius: 8px; border: 1px solid #e2e2e2; }"
        )
        row_lay = QVBoxLayout(row)
        row_lay.setContentsMargins(12, 10, 10, 10)
        row_lay.setSpacing(4)

        row_header = QHBoxLayout()
        t = QLabel("States")
        t.setStyleSheet(
            "QLabel { font-size: 13px; color: #333; font-weight: 500;"
            " border: none; background: transparent; }"
        )
        row_header.addWidget(t, 1)

        self._edit_btn = QPushButton("Edit…")
        self._edit_btn.setEnabled(False)
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.setStyleSheet(
            "QPushButton { background: #fff; border: 1px solid #d8d8d8;"
            " border-radius: 6px; padding: 4px 12px; color: #444; font-size: 12px; }"
            " QPushButton:hover { background: #f0f0f0; border-color: #bbb; }"
            " QPushButton:disabled { color: #ccc; border-color: #e5e5e5; }"
        )
        self._edit_btn.clicked.connect(self._on_edit)
        row_header.addWidget(self._edit_btn)
        row_lay.addLayout(row_header)

        self._hint = QLabel("Open a checklist first.")
        self._hint.setStyleSheet(
            "QLabel { font-size: 11px; color: #bbb; border: none; background: transparent; }"
        )
        row_lay.addWidget(self._hint)
        body.addWidget(row)

        # Max item width row
        width_row = QFrame()
        width_row.setStyleSheet(
            "QFrame { background: #efefef; border-radius: 8px; border: 1px solid #e2e2e2; }"
        )
        wr_lay = QVBoxLayout(width_row)
        wr_lay.setContentsMargins(12, 10, 10, 10)
        wr_lay.setSpacing(6)

        wr_header = QHBoxLayout()
        wl = QLabel("Max item width")
        wl.setStyleSheet(
            "QLabel { font-size: 13px; color: #333; font-weight: 500;"
            " border: none; background: transparent; }"
        )
        wr_header.addWidget(wl, 1)
        self._width_value = QLabel("800 px")
        self._width_value.setStyleSheet(
            "QLabel { font-size: 12px; color: #666; border: none; background: transparent; }"
        )
        wr_header.addWidget(self._width_value)
        wr_lay.addLayout(wr_header)

        self._width_slider = QSlider(Qt.Orientation.Horizontal)
        self._width_slider.setRange(MIN_MAX_ITEM_WIDTH, MAX_MAX_ITEM_WIDTH)
        self._width_slider.setValue(load_max_item_width())
        self._width_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #ddd; border-radius: 3px; }"
            " QSlider::handle:horizontal { width: 14px; margin: -4px 0; background: #fff;"
            " border: 1px solid #ccc; border-radius: 7px; }"
            " QSlider::handle:horizontal:hover { background: #f5f5f5; border-color: #aaa; }"
            " QSlider::sub-page:horizontal { background: #bbb; border-radius: 3px; }"
        )
        self._width_slider.valueChanged.connect(self._on_width_changed)
        wr_lay.addWidget(self._width_slider)
        body.addWidget(width_row)

        self._update_width_label(load_max_item_width())

        body.addStretch()
        root.addLayout(body, 1)

    def _update_width_label(self, value: int):
        self._width_value.setText(f"{value} px")

    def _on_width_changed(self, value: int):
        self._update_width_label(value)
        save_max_item_width(value)
        if self._max_width_cb:
            self._max_width_cb(value)

    def set_has_checklist(self, has: bool):
        self._edit_btn.setEnabled(has)
        self._hint.setVisible(not has)

    def set_edit_states_callback(self, cb):
        self._edit_states_cb = cb

    def set_max_width_callback(self, cb):
        self._max_width_cb = cb

    def _on_edit(self):
        if self._edit_states_cb:
            self._edit_states_cb()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Checklist")
        self.resize(920, 640)

        self._current_path: Path | None = None
        self._current_checklist: Checklist | None = None
        self._sidebar_width = 220
        # which panel is shown: 'lists' | 'settings' | None (closed)
        self._active_panel: str | None = "lists"

        self._build_ui()
        self._refresh_sidebar()

    def _build_ui(self):
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        root_lay = QHBoxLayout(root_widget)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # --- activity bar ---
        self._activity = _ActivityBar()
        self._activity.lists_btn.clicked.connect(self._on_lists_btn)
        self._activity.settings_btn.clicked.connect(self._on_settings_btn)
        root_lay.addWidget(self._activity)

        # --- splitter: sidebar stack | main view ---
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        root_lay.addWidget(self._splitter, 1)

        # sidebar stack
        self._stack = QStackedWidget()
        self._splitter.addWidget(self._stack)

        # page 0 — checklists
        lists_page = QWidget()
        lists_page.setObjectName("sidebar")
        lists_page.setStyleSheet(sidebar_qss())
        lp_lay = QVBoxLayout(lists_page)
        lp_lay.setContentsMargins(0, 0, 0, 8)
        lp_lay.setSpacing(4)

        title = QLabel("CHECKLISTS")
        title.setObjectName("sidebarTitle")
        lp_lay.addWidget(title)

        self._sidebar_view = SidebarView()
        self._sidebar_view.checklist_selected.connect(self._on_checklist_selected)
        self._sidebar_view.checklist_deleted.connect(self._on_checklist_deleted)
        self._sidebar_view.checklist_renamed.connect(self._on_checklist_renamed)
        self._sidebar_view.settings_requested.connect(self._on_settings_for_list)
        self._sidebar_view.pending_committed.connect(self._on_pending_committed)
        self._sidebar_view.add_requested.connect(self._new_checklist)
        lp_lay.addWidget(self._sidebar_view, 1)

        self._stack.addWidget(lists_page)   # index 0

        # page 1 — settings
        self._settings_panel = _SettingsPanel()
        self._settings_panel.setObjectName("sidebar")
        self._settings_panel.setStyleSheet(sidebar_qss())
        self._settings_panel.set_edit_states_callback(self._edit_states)
        self._stack.addWidget(self._settings_panel)  # index 1

        # main view
        self._view = ChecklistView()
        self._view.changed.connect(self._save_current)
        self._view.set_max_item_width(load_max_item_width())
        self._settings_panel.set_max_width_callback(self._view.set_max_item_width)
        self._splitter.addWidget(self._view)

        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([self._sidebar_width, 700])

        self._activity.set_active("lists")

    # -- activity bar / panel handlers -------------------------------------

    def _on_lists_btn(self):
        if self._active_panel == "lists":
            self._close_sidebar()
        else:
            self._open_panel("lists")

    def _on_settings_btn(self):
        if self._active_panel == "settings":
            self._close_sidebar()
        else:
            self._open_panel("settings")

    def _open_panel(self, which: str):
        sizes = self._splitter.sizes()
        if sum(sizes) > 0 and sizes[0] == 0:
            total = sum(sizes)
            self._splitter.setSizes([self._sidebar_width, total - self._sidebar_width])
        self._stack.setCurrentIndex(0 if which == "lists" else 1)
        self._active_panel = which
        self._activity.set_active(which)

    def _close_sidebar(self):
        sizes = self._splitter.sizes()
        self._sidebar_width = max(sizes[0], self._sidebar_width)
        self._splitter.setSizes([0, sum(sizes)])
        self._active_panel = None
        self._activity.set_active(None)

    # -- sidebar -----------------------------------------------------------

    def _refresh_sidebar(self):
        paths = list_checklists(get_data_dir())
        self._sidebar_view.load_paths(paths, self._current_path)

    def _on_checklist_selected(self, path: Path):
        self._load_checklist(path)

    def _on_checklist_deleted(self, path: Path):
        if not _DeleteConfirmDialog.ask(self, path.stem):
            return
        path.unlink(missing_ok=True)
        self._sidebar_view.remove_path(path)
        if path == self._current_path:
            self._current_path = None
            self._current_checklist = None
            self._view.load_checklist(Checklist())
            self.setWindowTitle("Checklist")
        self._settings_panel.set_has_checklist(self._current_checklist is not None)

    def _on_checklist_renamed(self, path: Path, new_name: str):
        try:
            cl = load_checklist(path)
        except Exception:
            return
        cl.name = new_name
        save_checklist(cl, path)
        self._sidebar_view.update_name(path, new_name)
        if path == self._current_path:
            self._current_checklist = cl
            self._view.set_title(new_name)
            self.setWindowTitle("Checklist \u2014 " + new_name)

    def _load_checklist(self, path: Path):
        self._current_path = path
        self._current_checklist = load_checklist(path)
        self._view.load_checklist(self._current_checklist)
        self._view.set_title(self._current_checklist.name)
        self.setWindowTitle("Checklist \u2014 " + self._current_checklist.name)
        self._sidebar_view.set_active(path)
        self._settings_panel.set_has_checklist(True)

    def _new_checklist(self):
        self._sidebar_view.start_new_card()

    def _on_pending_committed(self, card, name: str):
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        path = get_data_dir() / (safe + ".xml")
        i = 1
        while path.exists():
            path = get_data_dir() / (safe + f"_{i}.xml")
            i += 1
        cl = Checklist(name=name)
        save_checklist(cl, path)
        card.finalize_new(path, name)
        self._load_checklist(path)

    # -- save --------------------------------------------------------------

    def _save_current(self):
        if not self._current_path or not self._current_checklist:
            return
        self._current_checklist.items = self._view.to_model_items()
        save_checklist(self._current_checklist, self._current_path)

    # -- state editor ------------------------------------------------------

    def _on_settings_for_list(self, path: Path):
        if path != self._current_path:
            self._load_checklist(path)
        self._edit_states()

    def _edit_states(self):
        if not self._current_checklist:
            return
        dlg = StateEditor(self._current_checklist.states,
                          self._current_checklist.default_state_number, self)
        if dlg.exec() == StateEditor.DialogCode.Accepted:
            self._current_checklist.states = dlg.result_states()
            self._current_checklist.default_state_number = dlg.result_default()
            self._view.refresh_all_colors()
            self._save_current()
