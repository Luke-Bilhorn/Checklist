from __future__ import annotations

from PySide6.QtCore import QEvent, QMimeData, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QDrag,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .models import Checklist, _short_id
from .theme import ACCENT, TEXT_MUTED, TEXT_PRIMARY, MIME_ITEM, blend_with_bg


class _DragGrip(QLabel):
    drag_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("\u2807")
        self.setFixedSize(14, 24)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setStyleSheet(
            "QLabel { color: #bbbbbb; font-size: 16px;"
            " background: transparent; padding: 0; }"
        )
        self._start = None

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._start = ev.position().toPoint()

    def mouseMoveEvent(self, ev):
        if self._start is None:
            return
        delta = (ev.position().toPoint() - self._start).manhattanLength()
        if delta >= QApplication.startDragDistance():
            self._start = None
            self.drag_requested.emit()

    def mouseReleaseEvent(self, ev):
        self._start = None


class ChecklistItemWidget(QFrame):
    changed = Signal()
    focused = Signal(object)
    enter_pressed = Signal(object)
    delete_requested = Signal(object)
    add_child_requested = Signal(object)

    def __init__(self, item_id: str, text: str, state_id: str,
                 checklist: Checklist, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.state_id = state_id
        self._checklist = checklist
        self._border_color = "#888888"
        self._fill_color = "#f8f8f8"
        self._drop_zone: str | None = None

        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 7, 10, 7)
        main_lay.setSpacing(2)

        header = QHBoxLayout()
        header.setSpacing(8)

        self._grip = _DragGrip(self)
        self._grip.drag_requested.connect(self._start_drag)
        header.addWidget(self._grip)

        self._dot = QPushButton()
        self._dot.setFixedSize(16, 16)
        self._dot.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dot.clicked.connect(self._cycle_state)
        header.addWidget(self._dot)

        self._text = QLineEdit(text)
        self._text.setStyleSheet(
            "QLineEdit { background: transparent; border: none;"
            " color: #333333; padding: 2px 4px;"
            " selection-background-color: #b3d7ff; }"
            " QLineEdit:focus { background: #f0f0f0;"
            " border: 1px solid #d0d0d0; border-radius: 3px; }"
        )
        self._text.textChanged.connect(lambda: self.changed.emit())
        self._text.returnPressed.connect(lambda: self.enter_pressed.emit(self))
        self._text.installEventFilter(self)
        header.addWidget(self._text, 1)

        self._add_btn = QPushButton("+")
        self._add_btn.setFixedSize(22, 22)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setToolTip("Add child")
        self._add_btn.setStyleSheet(
            "QPushButton { color: #bbbbbb; background: transparent;"
            " border: none; border-radius: 3px; font-size: 16px;"
            " font-weight: bold; }"
            " QPushButton:hover { color: #555555; background: #e8e8e8; }"
        )
        self._add_btn.clicked.connect(lambda: self.add_child_requested.emit(self))
        header.addWidget(self._add_btn)

        main_lay.addLayout(header)

        self._children_widget = QWidget()
        self._children_layout = QVBoxLayout(self._children_widget)
        self._children_layout.setContentsMargins(20, 4, 0, 4)
        self._children_layout.setSpacing(6)
        main_lay.addWidget(self._children_widget)

        self._update_colors()

    @property
    def children_layout(self) -> QVBoxLayout:
        return self._children_layout

    def text(self) -> str:
        return self._text.text()

    def focus_text(self, select_all=False):
        self._text.setFocus()
        if select_all:
            self._text.selectAll()

    def set_checklist_ref(self, cl: Checklist):
        self._checklist = cl

    def _update_colors(self):
        st = self._checklist.state_by_id(self.state_id) if self._checklist else None
        color = st.color if st else "#888888"
        self._border_color = color
        self._fill_color = blend_with_bg(color, 0.08)
        self._dot.setStyleSheet(
            "QPushButton { background-color: " + color + ";"
            " border: none; border-radius: 8px; }"
            " QPushButton:hover { border: 2px solid " + color + "; }"
        )
        self.update()

    def refresh_colors(self):
        self._update_colors()
        for i in range(self._children_layout.count()):
            w = self._children_layout.itemAt(i).widget()
            if isinstance(w, ChecklistItemWidget):
                w.set_checklist_ref(self._checklist)
                w.refresh_colors()

    def _cycle_state(self):
        if not self._checklist:
            return
        nxt = self._checklist.next_state(self.state_id)
        self.state_id = nxt.id
        self._update_colors()
        self.changed.emit()

    def set_state(self, state_id: str):
        self.state_id = state_id
        self._update_colors()
        self.changed.emit()

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        p.fillPath(path, QColor(self._fill_color))
        p.setPen(QPen(QColor(self._border_color), 2))
        p.drawRoundedRect(rect, 8, 8)

        if self._drop_zone == "before":
            p.setPen(QPen(QColor(ACCENT), 3))
            p.drawLine(QPointF(8, 1.5), QPointF(self.width() - 8, 1.5))
        elif self._drop_zone == "after":
            p.setPen(QPen(QColor(ACCENT), 3))
            y = self.height() - 1.5
            p.drawLine(QPointF(8, y), QPointF(self.width() - 8, y))
        elif self._drop_zone == "inside":
            p.setPen(QPen(QColor(ACCENT), 2, Qt.PenStyle.DashLine))
            inner = rect.adjusted(3, 3, -3, -3)
            p.drawRoundedRect(inner, 6, 6)
        p.end()

    # -- drag & drop -------------------------------------------------------

    def _start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_ITEM, self.item_id.encode())
        drag.setMimeData(mime)
        pix = self.grab()
        if pix.width() > 400:
            pix = pix.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation)
        drag.setPixmap(pix)
        drag.setHotSpot(self._grip.mapTo(self, self._grip.rect().center()))
        drag.exec(Qt.DropAction.MoveAction)

    def _source_id(self, event) -> str | None:
        md = event.mimeData()
        if md and md.hasFormat(MIME_ITEM):
            return md.data(MIME_ITEM).data().decode()
        return None

    def dragEnterEvent(self, event):
        sid = self._source_id(event)
        if sid and sid != self.item_id:
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        sid = self._source_id(event)
        if not sid or sid == self.item_id:
            return
        y = event.position().y()
        h = self.height()
        if h <= 0:
            return
        ratio = y / h
        if ratio < 0.25:
            self._drop_zone = "before"
        elif ratio > 0.75:
            self._drop_zone = "after"
        else:
            self._drop_zone = "inside"
        self.update()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._drop_zone = None
        self.update()

    def dropEvent(self, event):
        sid = self._source_id(event)
        zone = self._drop_zone
        self._drop_zone = None
        self.update()
        if sid and zone:
            event.acceptProposedAction()
            view = self._find_view()
            if view:
                view.handle_drop(sid, self.item_id, zone)

    def _find_view(self):
        from .checklist_view import ChecklistView
        w = self.parent()
        while w:
            if isinstance(w, ChecklistView):
                return w
            w = w.parent()
        return None

    # -- context menu ------------------------------------------------------

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        if self._checklist:
            state_menu = menu.addMenu("Set State")
            for st in self._checklist.states:
                a = QAction(st.label, self)
                a.triggered.connect(lambda checked, s=st.id: self.set_state(s))
                state_menu.addAction(a)
            menu.addSeparator()
        a_sib = menu.addAction("Add sibling below")
        a_sib.triggered.connect(lambda: self.enter_pressed.emit(self))
        a_child = menu.addAction("Add child")
        a_child.triggered.connect(lambda: self.add_child_requested.emit(self))
        menu.addSeparator()
        a_del = menu.addAction("Delete")
        a_del.triggered.connect(lambda: self.delete_requested.emit(self))
        menu.exec(event.globalPos())

    # -- key event filter on text field ------------------------------------

    def eventFilter(self, obj, event):
        if obj is self._text and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Tab and not event.modifiers():
                view = self._find_view()
                if view:
                    view.indent_item(self)
                return True
            if key == Qt.Key.Key_Backtab or (
                key == Qt.Key.Key_Tab
                and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            ):
                view = self._find_view()
                if view:
                    view.outdent_item(self)
                return True
            if key == Qt.Key.Key_Escape:
                self._text.clearFocus()
                return True
            if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                if not self._text.text() and not self._text.hasFocus():
                    self.delete_requested.emit(self)
                    return True
        return super().eventFilter(obj, event)
