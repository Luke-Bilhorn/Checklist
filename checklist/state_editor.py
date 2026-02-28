from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .indicators import draw_symbol
from .models import AVAILABLE_SYMBOLS, DEFAULT_STATES, ChecklistState, _short_id

_DLG_QSS = (
    "QDialog { background-color: #ffffff; }"
    " QListWidget { background: #fafafa; border: 1px solid #e0e0e0;"
    " border-radius: 6px; outline: none; padding: 4px; }"
    " QListWidget::item { padding: 7px 10px; border-radius: 5px; }"
    " QListWidget::item:selected { background-color: #e8e8e8; }"
    " QListWidget::item:hover:!selected { background-color: #f2f2f2; }"
    " QLineEdit, QSpinBox, QComboBox { background: #fff; border: 1px solid #ddd;"
    " border-radius: 5px; padding: 5px 8px; color: #333; }"
    " QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #aaa; }"
    " QPushButton { background: #f5f5f5; border: 1px solid #ddd;"
    " border-radius: 5px; padding: 6px 14px; color: #333; font-size: 12px; }"
    " QPushButton:hover { background: #ebebeb; border-color: #ccc; }"
    " QPushButton:pressed { background: #e0e0e0; }"
    " QLabel { color: #666; font-size: 11px; }"
    " QCheckBox { color: #444; font-size: 11px; spacing: 4px; }"
    " QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px;"
    " border: 1px solid #ccc; background: #fff; }"
    " QCheckBox::indicator:checked { background: #4CAF50; border-color: #4CAF50; }"
    " QComboBox::drop-down { border: none; }"
    " QComboBox QAbstractItemView { background: #fff; border: 1px solid #ddd;"
    " border-radius: 4px; selection-background-color: #e8e8e8; }"
)


class StateEditor(QDialog):
    def __init__(self, states: list[ChecklistState], default_state_number: int = 0,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit States")
        self.setMinimumSize(500, 480)
        self.setStyleSheet(_DLG_QSS)
        self._states = [
            ChecklistState(s.number, s.label, s.color, s.symbol, s.in_cycle)
            for s in states
        ]
        self._default_number = default_state_number
        self._sel: int | None = None

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.currentRowChanged.connect(self._on_row)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        lay.addWidget(self._list)

        form = QHBoxLayout()
        form.setSpacing(6)

        num_col = QVBoxLayout()
        num_col.addWidget(QLabel("Number"))
        self._num_spin = QSpinBox()
        self._num_spin.setRange(-1, 999)
        self._num_spin.valueChanged.connect(self._on_number)
        num_col.addWidget(self._num_spin)
        form.addLayout(num_col)

        lbl_col = QVBoxLayout()
        lbl_col.addWidget(QLabel("Label"))
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("State name...")
        self._label_edit.textChanged.connect(self._on_label)
        lbl_col.addWidget(self._label_edit)
        form.addLayout(lbl_col, 1)

        sym_col = QVBoxLayout()
        sym_col.addWidget(QLabel("Symbol"))
        self._sym_combo = QComboBox()
        for key, desc in AVAILABLE_SYMBOLS:
            self._sym_combo.addItem(desc, key)
        self._sym_combo.currentIndexChanged.connect(self._on_symbol)
        sym_col.addWidget(self._sym_combo)
        form.addLayout(sym_col)

        clr_col = QVBoxLayout()
        clr_col.addWidget(QLabel("Color"))
        self._color_btn = QPushButton("  ")
        self._color_btn.setFixedHeight(30)
        self._color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color_btn.clicked.connect(self._pick_color)
        clr_col.addWidget(self._color_btn)
        form.addLayout(clr_col)

        lay.addLayout(form)

        # Options row: in-cycle + set as default
        opts_row = QHBoxLayout()
        self._cycle_cb = QCheckBox("Include in click-cycle")
        self._cycle_cb.setToolTip(
            "When checked, clicking an indicator will cycle through this state"
        )
        self._cycle_cb.toggled.connect(self._on_cycle)
        opts_row.addWidget(self._cycle_cb)
        opts_row.addStretch()
        self._default_btn = QPushButton("Set as default for new items")
        self._default_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._default_btn.clicked.connect(self._set_default)
        opts_row.addWidget(self._default_btn)
        lay.addLayout(opts_row)

        btns = QHBoxLayout()
        add_btn = QPushButton("Add State")
        add_btn.clicked.connect(self._add)
        btns.addWidget(add_btn)
        rm_btn = QPushButton("Remove")
        rm_btn.clicked.connect(self._remove)
        btns.addWidget(rm_btn)
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btns.addWidget(reset_btn)
        btns.addStretch()
        done_btn = QPushButton("Done")
        done_btn.clicked.connect(self.accept)
        btns.addWidget(done_btn)
        lay.addLayout(btns)

        self._refresh()

    def result_states(self) -> list[ChecklistState]:
        return self._states

    def result_default(self) -> int:
        return self._default_number

    def _refresh(self):
        self._list.blockSignals(True)
        self._list.clear()
        for st in self._states:
            cycle_mark = " \u2B6E" if st.in_cycle else ""
            default_mark = " \u2605" if st.number == self._default_number else ""
            text = f"  [{st.number}]  {st.label}{cycle_mark}{default_mark}"
            it = QListWidgetItem(text)
            it.setForeground(QColor(st.color))
            self._list.addItem(it)
        self._list.blockSignals(False)
        if self._sel is not None and self._sel < len(self._states):
            self._list.setCurrentRow(self._sel)

    def _on_row(self, row: int):
        if row < 0 or row >= len(self._states):
            self._sel = None
            return
        self._sel = row
        st = self._states[row]

        self._num_spin.blockSignals(True)
        self._num_spin.setValue(st.number)
        self._num_spin.blockSignals(False)

        self._label_edit.blockSignals(True)
        self._label_edit.setText(st.label)
        self._label_edit.blockSignals(False)

        idx = self._sym_combo.findData(st.symbol)
        self._sym_combo.blockSignals(True)
        self._sym_combo.setCurrentIndex(max(idx, 0))
        self._sym_combo.blockSignals(False)

        self._cycle_cb.blockSignals(True)
        self._cycle_cb.setChecked(st.in_cycle)
        self._cycle_cb.blockSignals(False)

        is_default = st.number == self._default_number
        self._default_btn.setText(
            "✓ Default for new items" if is_default else "Set as default for new items"
        )
        self._default_btn.setEnabled(not is_default)

        self._color_btn.setStyleSheet(
            "QPushButton { background-color: " + st.color
            + "; border: 1px solid #ccc; border-radius: 5px; }"
        )

    def _on_number(self, val: int):
        if self._sel is None:
            return
        self._states[self._sel].number = val
        self._refresh()

    def _on_label(self, text: str):
        if self._sel is None:
            return
        self._states[self._sel].label = text
        it = self._list.item(self._sel)
        if it:
            st = self._states[self._sel]
            cycle_mark = " \u2B6E" if st.in_cycle else ""
            it.setText(f"  [{st.number}]  {text}{cycle_mark}")

    def _on_symbol(self, idx: int):
        if self._sel is None:
            return
        key = self._sym_combo.itemData(idx)
        if key:
            self._states[self._sel].symbol = key

    def _on_cycle(self, checked: bool):
        if self._sel is None:
            return
        self._states[self._sel].in_cycle = checked
        self._refresh()

    def _set_default(self):
        if self._sel is None:
            return
        self._default_number = self._states[self._sel].number
        self._refresh()
        # Refresh button label
        self._on_row(self._sel)

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
                + "; border: 1px solid #ccc; border-radius: 5px; }"
            )
            it = self._list.item(self._sel)
            if it:
                it.setForeground(QColor(h))

    def _add(self):
        nums = {s.number for s in self._states}
        n = max(nums) + 1 if nums else 0
        self._states.append(
            ChecklistState(number=n, label="New State", color="#FFB300",
                           symbol="square", in_cycle=True)
        )
        self._sel = len(self._states) - 1
        self._refresh()

    def _remove(self):
        if self._sel is None or len(self._states) <= 1:
            return
        self._states.pop(self._sel)
        if self._sel >= len(self._states):
            self._sel = len(self._states) - 1
        self._refresh()

    def _reset_defaults(self):
        self._states = [
            ChecklistState(s.number, s.label, s.color, s.symbol, s.in_cycle)
            for s in DEFAULT_STATES
        ]
        self._sel = 0
        self._refresh()

    def _on_rows_moved(self, parent, src, src_end, dest_parent, dest_row):
        moved = self._states.pop(src)
        insert_at = dest_row if dest_row <= src else dest_row - 1
        self._states.insert(insert_at, moved)
        self._sel = insert_at
