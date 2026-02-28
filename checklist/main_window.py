from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .checklist_view import ChecklistView
from .models import Checklist
from .sidebar import SidebarView
from .state_editor import StateEditor
from .theme import sidebar_qss
from .xml_io import list_checklists, load_checklist, save_checklist

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_ACTIVITY_W = 44  # width of the narrow icon strip


# ---------------------------------------------------------------------------
# Narrow activity bar — always visible on the far left
# ---------------------------------------------------------------------------

_ACTIVITY_BTN_SS = (
    "QPushButton {{ background: {bg}; border: none; font-size: 18px;"
    " color: {fg}; border-radius: 8px; }}"
    " QPushButton:hover {{ background: #dcdcdc; color: #333; }}"
)


class _ActivityBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(_ACTIVITY_W)
        self.setStyleSheet("QWidget { background: #ebebeb; }")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 10, 6, 10)
        lay.setSpacing(4)

        self.lists_btn = self._make_btn("☰", "Checklists")
        lay.addWidget(self.lists_btn)
        lay.addStretch()
        self.settings_btn = self._make_btn("⚙", "Settings")
        lay.addWidget(self.settings_btn)

    @staticmethod
    def _make_btn(icon: str, tooltip: str) -> QPushButton:
        btn = QPushButton(icon)
        btn.setFixedSize(32, 32)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        btn.setStyleSheet(_ACTIVITY_BTN_SS.format(bg="transparent", fg="#888"))
        return btn

    def set_active(self, which: str | None):
        """Highlight the active button. which: 'lists' | 'settings' | None"""
        active_ss = _ACTIVITY_BTN_SS.format(bg="#d0d0d0", fg="#333")
        idle_ss = _ACTIVITY_BTN_SS.format(bg="transparent", fg="#888")
        self.lists_btn.setStyleSheet(active_ss if which == "lists" else idle_ss)
        self.settings_btn.setStyleSheet(active_ss if which == "settings" else idle_ss)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        p = QPainter(self)
        p.setPen(QPen(QColor("#d8d8d8"), 1))
        p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        p.end()


# ---------------------------------------------------------------------------
# Inline settings panel (lives in the sidebar stack)
# ---------------------------------------------------------------------------

class _SettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._edit_states_cb = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # title
        title = QLabel("SETTINGS")
        title.setObjectName("sidebarTitle")
        root.addWidget(title)

        body = QVBoxLayout()
        body.setContentsMargins(10, 4, 10, 10)
        body.setSpacing(8)

        sec = QLabel("CHECKLIST")
        sec.setStyleSheet(
            "QLabel { font-size: 10px; font-weight: 600; color: #9a9a9a;"
            " letter-spacing: 1px; padding: 6px 0 2px 0; background: transparent; }"
        )
        body.addWidget(sec)

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

        body.addStretch()
        root.addLayout(body, 1)

    def set_has_checklist(self, has: bool):
        self._edit_btn.setEnabled(has)
        self._hint.setVisible(not has)

    def set_edit_states_callback(self, cb):
        self._edit_states_cb = cb

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

        # --- activity bar (always visible) ---
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
        self._splitter.addWidget(self._view)

        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([self._sidebar_width, 700])

        self._activity.set_active("lists")

    # -- activity bar handlers ---------------------------------------------

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
            # sidebar was collapsed — re-open it
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
        paths = list_checklists(DATA_DIR)
        self._sidebar_view.load_paths(paths, self._current_path)

    def _on_checklist_selected(self, path: Path):
        self._load_checklist(path)

    def _on_checklist_deleted(self, path: Path):
        reply = QMessageBox.question(
            self, "Delete", f"Delete '{path.stem}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
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
            self.setWindowTitle("Checklist \u2014 " + new_name)

    def _load_checklist(self, path: Path):
        self._current_path = path
        self._current_checklist = load_checklist(path)
        self._view.load_checklist(self._current_checklist)
        self.setWindowTitle("Checklist \u2014 " + self._current_checklist.name)
        self._sidebar_view.set_active(path)
        self._settings_panel.set_has_checklist(True)

    def _new_checklist(self):
        self._sidebar_view.start_new_card()

    def _on_pending_committed(self, card, name: str):
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        path = DATA_DIR / (safe + ".xml")
        i = 1
        while path.exists():
            path = DATA_DIR / (safe + f"_{i}.xml")
            i += 1
        cl = Checklist(name=name)
        save_checklist(cl, path)
        card.finalize_new(path, name)
        card.rename_requested.connect(self._on_checklist_renamed)
        card.delete_requested.connect(lambda c: self._on_checklist_deleted(c.path))
        self._load_checklist(path)

    # -- save --------------------------------------------------------------

    def _save_current(self):
        if not self._current_path or not self._current_checklist:
            return
        self._current_checklist.items = self._view.to_model_items()
        save_checklist(self._current_checklist, self._current_path)

    # -- state editor ------------------------------------------------------

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
