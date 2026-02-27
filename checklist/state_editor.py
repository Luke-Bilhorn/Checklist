from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from .models import ChecklistState, _short_id


_DIALOG_QSS = (
    "QDialog { background-color: #ffffff; }"
    " QListWidget { background: #f8f8f8; border: 1px solid #e0e0e0;"
    " border-radius: 4px; outline: none; padding: 4px; }"
    " QListWidget::item { padding: 6px 10px; border-radius: 4px; }"
    " QListWidget::item:selected { background-color: #e0e0e0; }"
    " QListWidget::item:hover:!selected { background-color: #f0f0f0; }"
    " QLineEdit { background: #ffffff; border: 1px solid #d0d0d0;"
    " border-radius: 4px; padding: 5px 8px; color: #333333; }"
    " QLineEdit:focus { border-color: #999999; }"
    " QPushButton { background: #f3f3f3; border: 1px solid #d0d0d0;"
    " border-radius: 4px; padding: 5px 14px; color: #333333; }"
    " QPushButton:hover { background: #e8e8e8; border-color: #bbb; }"
)


class StateEditor(QDialog):
    def __init__(self, states: list[ChecklistState], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit States")
        self.setMinimumSize(420, 370)
        self.setStyleSheet(_DIALOG_QSS)

        self._states = [
            ChecklistState(id=s.id, label=s.label, color=s.color) for s in states
        ]
        self._sel: int | None = None

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row)
        lay.addWidget(self._list)

        edit_row = QHBoxLayout()
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("State label...")
        self._label_edit.textChanged.connect(self._on_label)
        edit_row.addWidget(self._label_edit, 1)

        self._color_btn = QPushButton("  ")
        self._color_btn.setFixedSize(36, 30)
        self._color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color_btn.clicked.connect(self._pick_color)
        edit_row.addWidget(self._color_btn)
        lay.addLayout(edit_row)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add State")
        add_btn.clicked.connect(self._add)
        btn_row.addWidget(add_btn)

        rm_btn = QPushButton("Remove")
        rm_btn.clicked.connect(self._remove)
        btn_row.addWidget(rm_btn)

        btn_row.addStretch()

        done_btn = QPushButton("Done")
        done_btn.clicked.connect(self.accept)
        btn_row.addWidget(done_btn)
        lay.addLayout(btn_row)

        self._refresh()

    def result_states(self) -> list[ChecklistState]:
        return self._states

    def _refresh(self):
        self._list.blockSignals(True)
        self._list.clear()
        for st in self._states:
            it = QListWidgetItem("  " + st.label)
            it.setForeground(QColor(st.color))
            self._list.addItem(it)
        self._list.blockSignals(False)
        if self._sel is not None and self._sel < len(self._states):
            self._list.setCurrentRow(self._sel)

    def _on_row(self, row: int):
        if row < 0 or row >= len(self._states):
            self._sel = None
            self._label_edit.clear()
            return
        self._sel = row
        st = self._states[row]
        self._label_edit.blockSignals(True)
        self._label_edit.setText(st.label)
        self._label_edit.blockSignals(False)
        self._color_btn.setStyleSheet(
            "QPushButton { background-color: " + st.color
            + "; border: 1px solid #ccc; border-radius: 4px; }"
        )

    def _on_label(self, text: str):
        if self._sel is None:
            return
        self._states[self._sel].label = text
        it = self._list.item(self._sel)
        if it:
            it.setText("  " + text)

    def _pick_color(self):
        if self._sel is None:
            return
        cur = QColor(self._states[self._sel].color)
        c = QColorDialog.getColor(cur, self, "Pick state color")
        if c.isValid():
            h = c.name()
            self._states[self._sel].color = h
            self._color_btn.setStyleSheet(
                "QPushButton { background-color: " + h
                + "; border: 1px solid #ccc; border-radius: 4px; }"
            )
            it = self._list.item(self._sel)
            if it:
                it.setForeground(QColor(h))

    def _add(self):
        ns = ChecklistState(id=_short_id(), label="New State", color="#FFB300")
        self._states.append(ns)
        self._sel = len(self._states) - 1
        self._refresh()

    def _remove(self):
        if self._sel is None or len(self._states) <= 1:
            return
        self._states.pop(self._sel)
        if self._sel >= len(self._states):
            self._sel = len(self._states) - 1
        self._refresh()
