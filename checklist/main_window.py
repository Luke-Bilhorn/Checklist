from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .checklist_view import ChecklistView
from .models import Checklist
from .state_editor import StateEditor
from .theme import sidebar_qss
from .xml_io import list_checklists, load_checklist, save_checklist

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Checklist")
        self.resize(900, 620)

        self._current_path: Path | None = None
        self._current_checklist: Checklist | None = None

        self._build_ui()
        self._refresh_sidebar()

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(splitter)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet(sidebar_qss())
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 8)
        sb_lay.setSpacing(0)

        title = QLabel("CHECKLISTS")
        title.setObjectName("sidebarTitle")
        sb_lay.addWidget(title)

        self._sidebar_list = QListWidget()
        self._sidebar_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._sidebar_list.customContextMenuRequested.connect(
            self._sidebar_context_menu
        )
        self._sidebar_list.currentRowChanged.connect(self._on_checklist_selected)
        sb_lay.addWidget(self._sidebar_list)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(8, 4, 8, 0)

        new_btn = QPushButton("+ New")
        new_btn.setObjectName("sidebarBtn")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self._new_checklist)
        btn_row.addWidget(new_btn)

        btn_row.addStretch()

        states_btn = QPushButton("Edit States...")
        states_btn.setObjectName("statesBtn")
        states_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        states_btn.clicked.connect(self._edit_states)
        btn_row.addWidget(states_btn)

        sb_lay.addLayout(btn_row)
        splitter.addWidget(sidebar)

        self._view = ChecklistView()
        self._view.changed.connect(self._save_current)
        splitter.addWidget(self._view)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

    # -- sidebar -----------------------------------------------------------

    def _refresh_sidebar(self):
        self._sidebar_list.blockSignals(True)
        self._sidebar_list.clear()
        self._checklist_paths: list[Path] = list_checklists(DATA_DIR)
        for p in self._checklist_paths:
            self._sidebar_list.addItem(p.stem)
        self._sidebar_list.blockSignals(False)

        if self._current_path and self._current_path in self._checklist_paths:
            self._sidebar_list.setCurrentRow(
                self._checklist_paths.index(self._current_path)
            )

    def _on_checklist_selected(self, row: int):
        if row < 0 or row >= len(self._checklist_paths):
            return
        self._load_checklist(self._checklist_paths[row])

    def _load_checklist(self, path: Path):
        self._current_path = path
        self._current_checklist = load_checklist(path)
        self._view.load_checklist(self._current_checklist)
        self.setWindowTitle("Checklist \u2014 " + self._current_checklist.name)

    def _new_checklist(self):
        name, ok = QInputDialog.getText(self, "New Checklist", "Name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        path = DATA_DIR / (safe + ".xml")
        if path.exists():
            QMessageBox.warning(self, "Exists", "A checklist with that name exists.")
            return
        cl = Checklist(name=name)
        save_checklist(cl, path)
        self._current_path = path
        self._refresh_sidebar()
        self._load_checklist(path)

    def _sidebar_context_menu(self, pos):
        item = self._sidebar_list.itemAt(pos)
        if not item:
            return
        row = self._sidebar_list.row(item)
        path = self._checklist_paths[row]
        menu = QMenu(self)
        rename_a = menu.addAction("Rename...")
        rename_a.triggered.connect(lambda: self._rename_checklist(path))
        del_a = menu.addAction("Delete")
        del_a.triggered.connect(lambda: self._delete_checklist(path))
        menu.exec(self._sidebar_list.mapToGlobal(pos))

    def _rename_checklist(self, path: Path):
        cl = load_checklist(path)
        new_name, ok = QInputDialog.getText(
            self, "Rename", "New name:", text=cl.name
        )
        if not ok or not new_name.strip():
            return
        cl.name = new_name.strip()
        save_checklist(cl, path)
        if path == self._current_path:
            self._current_checklist = cl
            self.setWindowTitle("Checklist \u2014 " + cl.name)
        self._refresh_sidebar()

    def _delete_checklist(self, path: Path):
        reply = QMessageBox.question(
            self, "Delete", "Delete '" + path.stem + "'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        path.unlink(missing_ok=True)
        if path == self._current_path:
            self._current_path = None
            self._current_checklist = None
            self._view.load_checklist(Checklist())
            self.setWindowTitle("Checklist")
        self._refresh_sidebar()

    # -- save --------------------------------------------------------------

    def _save_current(self):
        if not self._current_path or not self._current_checklist:
            return
        self._current_checklist.items = self._view.to_model_items()
        save_checklist(self._current_checklist, self._current_path)

    # -- state editor ------------------------------------------------------

    def _edit_states(self):
        if not self._current_checklist:
            QMessageBox.information(
                self, "No checklist", "Open or create a checklist first."
            )
            return
        dlg = StateEditor(self._current_checklist.states, self)
        if dlg.exec() == StateEditor.DialogCode.Accepted:
            self._current_checklist.states = dlg.result_states()
            self._view.refresh_all_colors()
            self._save_current()
