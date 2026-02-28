from __future__ import annotations

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .item_widget import AddItemCard, ChecklistItemWidget
from .models import Checklist, ChecklistItem, _short_id
from .theme import ACCENT, BORDER, MIME_ITEM, TEXT_MUTED

_TITLE_SS = (
    "QLabel { font-size: 22px; font-weight: 700; color: #222;"
    " background: transparent; padding: 4px 0 8px 0; }"
)


class _ContentWidget(QWidget):
    """Inner widget of the scroll area; accepts drops on empty space."""

    drop_on_empty = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData() and event.mimeData().hasFormat(MIME_ITEM):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        md = event.mimeData()
        if md and md.hasFormat(MIME_ITEM):
            sid = md.data(MIME_ITEM).data().decode()
            self.drop_on_empty.emit(sid)
            event.acceptProposedAction()


class ChecklistView(QScrollArea):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checklist: Checklist | None = None

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = _ContentWidget()
        self._content.drop_on_empty.connect(
            lambda sid: self.handle_drop(sid, None, "end")
        )
        self.setWidget(self._content)

        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(6)

        self._title_label = QLabel()
        self._title_label.setStyleSheet(_TITLE_SS)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setVisible(False)
        self._layout.addWidget(self._title_label)

        self._add_btn = AddItemCard()
        self._add_btn.clicked.connect(self._add_top_level)
        self._layout.addWidget(self._add_btn)

        self._layout.addStretch()

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(lambda: self.changed.emit())

    def set_max_item_width(self, width: int):
        self._content.setMaximumWidth(width)

    @property
    def checklist(self) -> Checklist | None:
        return self._checklist

    def set_title(self, name: str):
        self._title_label.setText(name)
        self._title_label.setVisible(bool(name))

    # -- load / rebuild ----------------------------------------------------

    def load_checklist(self, checklist: Checklist) -> None:
        self._checklist = checklist
        self._rebuild()

    def _rebuild(self):
        keep = {self._add_btn, self._title_label}
        while True:
            item = self._layout.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w and w not in keep:
                w.setParent(None)
                w.deleteLater()

        self._layout.addWidget(self._title_label)

        if self._checklist:
            for mi in self._checklist.items:
                w = self._create_widget(mi)
                self._layout.insertWidget(self._item_insert_index(), w)

        self._add_btn.update_from_checklist(self._checklist)
        self._layout.addWidget(self._add_btn)
        self._layout.addStretch()

    def _item_insert_index(self) -> int:
        idx = self._layout.indexOf(self._add_btn)
        return idx if idx >= 0 else self._layout.count()

    def _create_widget(self, mi: ChecklistItem) -> ChecklistItemWidget:
        w = ChecklistItemWidget(
            mi.id, mi.text, mi.state_number, mi.collapsed,
            self._checklist, self._content,
        )
        w.changed.connect(self._schedule_save)
        w.enter_pressed.connect(self._on_enter)
        w.delete_requested.connect(self._on_delete)
        w.add_child_requested.connect(self._on_add_child)
        for child_mi in mi.children:
            cw = self._create_widget(child_mi)
            w.children_layout.addWidget(cw)
        w.update_collapse_visibility()
        return w

    # -- model extraction --------------------------------------------------

    def to_model_items(self) -> list[ChecklistItem]:
        items: list[ChecklistItem] = []
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, ChecklistItemWidget):
                items.append(self._widget_to_model(w))
        return items

    def _widget_to_model(self, w: ChecklistItemWidget) -> ChecklistItem:
        children: list[ChecklistItem] = []
        for i in range(w.children_layout.count()):
            cw = w.children_layout.itemAt(i).widget()
            if isinstance(cw, ChecklistItemWidget):
                children.append(self._widget_to_model(cw))
        return ChecklistItem(
            id=w.item_id, text=w.text(), state_number=w.state_number,
            collapsed=w.collapsed, children=children,
        )

    # -- add / delete ------------------------------------------------------

    def _default_state(self) -> int:
        return self._checklist.default_state_number if self._checklist else 0

    def _add_top_level(self):
        if not self._checklist:
            return
        mi = ChecklistItem(id=_short_id(), text="", state_number=self._default_state())
        w = self._create_widget(mi)
        idx = self._item_insert_index()
        self._layout.insertWidget(idx, w)
        w.focus_text()
        self._schedule_save()

    def _on_enter(self, ref_widget: ChecklistItemWidget):
        if not self._checklist:
            return
        mi = ChecklistItem(id=_short_id(), text="", state_number=self._default_state())
        w = self._create_widget(mi)
        parent_layout = self._parent_layout_of(ref_widget)
        if parent_layout is None:
            return
        idx = self._index_in_layout(parent_layout, ref_widget)
        if idx < 0:
            parent_layout.addWidget(w)
        else:
            parent_layout.insertWidget(idx + 1, w)
        w.focus_text()
        self._schedule_save()

    def _on_add_child(self, parent_widget: ChecklistItemWidget):
        if not self._checklist:
            return
        mi = ChecklistItem(id=_short_id(), text="", state_number=self._default_state())
        w = self._create_widget(mi)
        parent_widget.children_layout.addWidget(w)
        parent_widget.update_collapse_visibility()
        w.focus_text()
        self._schedule_save()

    def _on_delete(self, widget: ChecklistItemWidget):
        parent_layout = self._parent_layout_of(widget)
        if parent_layout is None:
            return
        parent_w = widget.parentWidget()
        parent_layout.removeWidget(widget)
        widget.setParent(None)
        widget.deleteLater()
        if parent_w:
            gp = parent_w.parentWidget()
            if isinstance(gp, ChecklistItemWidget):
                gp.update_collapse_visibility()
        self._schedule_save()

    # -- indent / outdent --------------------------------------------------

    def indent_item(self, widget: ChecklistItemWidget):
        items = self.to_model_items()
        if self._indent_in_model(items, widget.item_id):
            self._apply_model(items, widget.item_id)

    def outdent_item(self, widget: ChecklistItemWidget):
        items = self.to_model_items()
        if self._outdent_in_model(items, widget.item_id, None, -1):
            self._apply_model(items, widget.item_id)

    @staticmethod
    def _indent_in_model(items: list[ChecklistItem], target_id: str) -> bool:
        for i, it in enumerate(items):
            if it.id == target_id and i > 0:
                items.pop(i)
                items[i - 1].children.append(it)
                return True
            if ChecklistView._indent_in_model(it.children, target_id):
                return True
        return False

    @staticmethod
    def _outdent_in_model(
        items: list[ChecklistItem], target_id: str,
        parent_list: list[ChecklistItem] | None, parent_idx: int,
    ) -> bool:
        for i, it in enumerate(items):
            if it.id == target_id:
                if parent_list is not None:
                    items.pop(i)
                    parent_list.insert(parent_idx + 1, it)
                    return True
                return False
            if ChecklistView._outdent_in_model(it.children, target_id, items, i):
                return True
        return False

    # -- drag & drop -------------------------------------------------------

    def handle_drop(self, source_id: str, target_id: str | None, zone: str):
        items = self.to_model_items()
        if target_id and self._is_descendant(items, source_id, target_id):
            return
        moved = self._find_and_remove(items, source_id)
        if moved is None:
            return
        if target_id is None or zone == "end":
            items.append(moved)
        else:
            self._insert_relative(items, target_id, zone, moved)
        self._apply_model(items, source_id)

    @staticmethod
    def _find_and_remove(
        items: list[ChecklistItem], target_id: str,
    ) -> ChecklistItem | None:
        for i, it in enumerate(items):
            if it.id == target_id:
                return items.pop(i)
            found = ChecklistView._find_and_remove(it.children, target_id)
            if found:
                return found
        return None

    @staticmethod
    def _insert_relative(
        items: list[ChecklistItem], target_id: str,
        zone: str, item: ChecklistItem,
    ) -> bool:
        for i, it in enumerate(items):
            if it.id == target_id:
                if zone == "before":
                    items.insert(i, item)
                elif zone == "after":
                    items.insert(i + 1, item)
                elif zone == "inside":
                    it.children.append(item)
                return True
            if ChecklistView._insert_relative(it.children, target_id, zone, item):
                return True
        return False

    @staticmethod
    def _is_descendant(
        items: list[ChecklistItem], ancestor_id: str, target_id: str,
    ) -> bool:
        for it in items:
            if it.id == ancestor_id:
                return ChecklistView._contains(it.children, target_id)
            if ChecklistView._is_descendant(it.children, ancestor_id, target_id):
                return True
        return False

    @staticmethod
    def _contains(items: list[ChecklistItem], target_id: str) -> bool:
        for it in items:
            if it.id == target_id:
                return True
            if ChecklistView._contains(it.children, target_id):
                return True
        return False

    # -- helpers -----------------------------------------------------------

    def _apply_model(self, items: list[ChecklistItem], focus_id: str | None = None):
        if self._checklist:
            self._checklist.items = items
        self._rebuild()
        if focus_id:
            w = self._find_widget(focus_id)
            if w:
                w.focus_text()
        self._schedule_save()

    def _find_widget(self, item_id: str) -> ChecklistItemWidget | None:
        return self._search_layout(self._layout, item_id)

    def _search_layout(self, layout, item_id: str) -> ChecklistItemWidget | None:
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if isinstance(w, ChecklistItemWidget):
                if w.item_id == item_id:
                    return w
                found = self._search_layout(w.children_layout, item_id)
                if found:
                    return found
        return None

    def _parent_layout_of(self, widget: ChecklistItemWidget):
        parent = widget.parentWidget()
        if parent is self._content:
            return self._layout
        if parent is not None:
            lay = parent.layout()
            if lay and self._index_in_layout(lay, widget) >= 0:
                return lay
            grandparent = parent.parentWidget()
            if isinstance(grandparent, ChecklistItemWidget):
                return grandparent.children_layout
        return None

    @staticmethod
    def _index_in_layout(layout, widget) -> int:
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() is widget:
                return i
        return -1

    def _schedule_save(self):
        self._save_timer.start()

    def refresh_all_colors(self):
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, ChecklistItemWidget):
                w.refresh_colors()
        self._add_btn.update_from_checklist(self._checklist)
