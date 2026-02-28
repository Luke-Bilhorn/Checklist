from __future__ import annotations

import time

from PySide6.QtCore import QMimeData, QPointF, QRectF, QSize, QTimer, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QDrag,
    QPainter,
    QPainterPath,
    QPen,
    QTextOption,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .indicators import draw_symbol
from .models import Checklist, _short_id
from .theme import ACCENT, MIME_ITEM, blend_with_bg

BTN_SIZE = 28
SPACING = 4


# ---------------------------------------------------------------------------
# Auto-resizing text editor
# ---------------------------------------------------------------------------

class _AutoTextEdit(QTextEdit):
    enter_pressed = Signal()
    text_changed_signal = Signal()

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.setPlainText(text)
        self.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            "QTextEdit { background: transparent; border: none;"
            " color: #333333; padding: 0px 4px; }"
            " QTextEdit:focus { background: rgba(0,0,0,0.04);"
            " border: 1px solid #d8d8d8; border-radius: 4px; }"
        )
        self.setContentsMargins(0, 0, 0, 0)
        self.document().setDocumentMargin(2)
        self.document().contentsChanged.connect(self._adjust)
        self._adjust()

    def _adjust(self):
        doc = self.document()
        doc.blockSignals(True)
        doc.setDocumentMargin(2)
        doc.setTextWidth(max(self.viewport().width(), 100))
        text_h = int(doc.size().height())
        widget_h = max(text_h + 4, BTN_SIZE)
        self.setFixedHeight(widget_h)
        extra = widget_h - text_h
        if extra > 0:
            doc.setDocumentMargin(2 + extra / 2)
            doc.setTextWidth(max(self.viewport().width(), 100))
        doc.blockSignals(False)
        self.text_changed_signal.emit()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._adjust()

    def sizeHint(self):
        return QSize(100, self.height())

    def keyPressEvent(self, ev):
        key, mods = ev.key(), ev.modifiers()
        if key == Qt.Key.Key_Return and not mods:
            self.clearFocus()
            iw = self._item_widget()
            if iw:
                iw.setFocus()
                iw._enter_armed = True
            return
        if key == Qt.Key.Key_Tab and not mods:
            self._relay(True)
            return
        if key == Qt.Key.Key_Backtab or (
            key == Qt.Key.Key_Tab and mods & Qt.KeyboardModifier.ShiftModifier
        ):
            self._relay(False)
            return
        if key == Qt.Key.Key_Escape:
            self.clearFocus()
            return
        super().keyPressEvent(ev)

    def _relay(self, indent: bool):
        from .checklist_view import ChecklistView
        w = self.parent()
        while w:
            if isinstance(w, ChecklistView):
                iw = self._item_widget()
                if iw:
                    w.indent_item(iw) if indent else w.outdent_item(iw)
                return
            w = w.parent()

    def _item_widget(self):
        w = self.parent()
        while w:
            if isinstance(w, ChecklistItemWidget):
                return w
            w = w.parent()
        return None


# ---------------------------------------------------------------------------
# Drag grip  (A) -- same height as BTN_SIZE
# ---------------------------------------------------------------------------

GRIP_W = 10  # width of drag grip (narrow, taller than wide)


class _DragGrip(QWidget):
    drag_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(GRIP_W, BTN_SIZE)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self._dot_color = QColor("#cccccc")
        self._start = None

    def set_item_color(self, fill_color: str):
        c = QColor(fill_color)
        self._dot_color = QColor(
            max(c.red()-50, 0),
            max(c.green()-50, 0),
            max(c.blue()-50, 0),
        )
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._dot_color)
        cx = self.width() / 2
        cy = self.height() / 2
        r = 2.2
        gap = 7.0
        for dy in (-gap, 0, gap):
            p.drawEllipse(QPointF(cx, cy + dy), r, r)
        p.end()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._start = ev.position().toPoint()

    def mouseMoveEvent(self, ev):
        if self._start and (ev.position().toPoint() - self._start).manhattanLength() >= QApplication.startDragDistance():
            self._start = None
            self.drag_requested.emit()

    def mouseReleaseEvent(self, ev):
        self._start = None


# ---------------------------------------------------------------------------
# Indicator button  (B)  -- BTN_SIZE x BTN_SIZE, custom painted
# ---------------------------------------------------------------------------

class _IndicatorButton(QPushButton):
    long_pressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(BTN_SIZE, BTN_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            " border-radius: 4px; }"
            " QPushButton:hover { background: #f0f0f0; }"
        )
        self._symbol = "empty"
        self._color = "#888888"

        self._long_timer = QTimer(self)
        self._long_timer.setSingleShot(True)
        self._long_timer.setInterval(500)
        self._long_timer.timeout.connect(self._fire_long)
        self._was_long = False

    def set_indicator(self, symbol: str, color: str):
        self._symbol = symbol
        self._color = color
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        draw_symbol(p, QRectF(self.rect()), self._symbol, self._color, BTN_SIZE)
        p.end()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._was_long = False
            self._long_timer.start()
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):
        self._long_timer.stop()
        if self._was_long:
            self._was_long = False
            ev.accept()
            return
        super().mouseReleaseEvent(ev)

    def _fire_long(self):
        self._was_long = True
        self.long_pressed.emit()


# ---------------------------------------------------------------------------
# Small square buttons  -- BTN_SIZE x BTN_SIZE
# ---------------------------------------------------------------------------

_SQ_BTN_QSS = (
    "QPushButton { background: transparent; border: none; border-radius: 4px; }"
)


def _hover_bg(item_color: str) -> QColor:
    """Return a darker tinted version of the item's fill color for hover."""
    c = QColor(item_color)
    return QColor(
        max(c.red() - 50, 0),
        max(c.green() - 50, 0),
        max(c.blue() - 50, 0),
        100,
    )


class _TintedButton(QPushButton):
    """Base class for buttons that tint on hover using the item's color."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(BTN_SIZE, BTN_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_SQ_BTN_QSS)
        self._item_color = "#888888"
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def set_item_color(self, color: str):
        self._item_color = color
        self.update()

    def _paint_hover_bg(self, p: QPainter):
        if self.underMouse():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_hover_bg(self._item_color))
            p.drawRoundedRect(QRectF(self.rect()), 4, 4)

    def enterEvent(self, ev):
        super().enterEvent(ev)
        self.update()

    def leaveEvent(self, ev):
        super().leaveEvent(ev)
        self.update()


class _CollapseButton(_TintedButton):
    """Equilateral triangle button (D). Down when open, negative-in-square when closed."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = True
        self._has_children = False

    def set_state(self, expanded: bool, has_children: bool):
        self._expanded = expanded
        self._has_children = has_children
        self.setVisible(has_children)
        self.setToolTip("Collapse" if expanded else "Expand")
        self.update()

    def paintEvent(self, ev):
        if not self._has_children:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2
        arm = 6.0  # 90-degree chevron: arms are equal, angle at tip is 90°
        col = QColor("#aaaaaa") if not self.underMouse() else QColor("#666666")

        if self._expanded:
            # ^ chevron pointing up
            self._paint_hover_bg(p)
            path = QPainterPath()
            path.moveTo(cx - arm, cy + arm / 2)
            path.lineTo(cx,       cy - arm / 2)
            path.lineTo(cx + arm, cy + arm / 2)
            p.setPen(QPen(col, 2.0, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        else:
            # filled square with V chevron cut out
            sq = QRectF(self.rect())
            stroke_w = 2.5
            chevron = QPainterPath()
            chevron.moveTo(cx - arm, cy - arm / 2)
            chevron.lineTo(cx,       cy + arm / 2)
            chevron.lineTo(cx + arm, cy - arm / 2)
            # stroke the chevron to a filled region for subtraction
            stroker = __import__('PySide6.QtGui', fromlist=['QPainterPathStroker']).QPainterPathStroker()
            stroker.setWidth(stroke_w)
            stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
            stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            filled_chevron = stroker.createStroke(chevron)
            shape = QPainterPath()
            shape.addRoundedRect(sq, 4, 4)
            cutout = shape.subtracted(filled_chevron)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawPath(cutout)
        p.end()


class _OptionsToggle(_TintedButton):
    """Four-dot grid button (C)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setToolTip("Options")

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_hover_bg(p)
        col = QColor("#aaaaaa") if not self.underMouse() else QColor("#666666")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        cx, cy = self.width() / 2, self.height() / 2
        r, sp = 2.2, 4.5
        for dx in (-sp, sp):
            for dy in (-sp, sp):
                p.drawEllipse(QPointF(cx + dx, cy + dy), r, r)
        p.end()


class _AddChildButton(_TintedButton):
    """Plus button (E) with a custom-painted centered cross."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setToolTip("Add child")

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_hover_bg(p)
        col = QColor("#aaaaaa") if not self.underMouse() else QColor("#666666")
        p.setPen(QPen(col, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        cx, cy = self.width() / 2, self.height() / 2
        arm = 6
        p.drawLine(QPointF(cx - arm, cy), QPointF(cx + arm, cy))
        p.drawLine(QPointF(cx, cy - arm), QPointF(cx, cy + arm))
        p.end()


class _DeleteButton(_TintedButton):
    """Trash can icon button — geometric, red icon."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setToolTip("Delete")

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_hover_bg(p)
        col = QColor("#cc4444") if not self.underMouse() else QColor("#aa2222")
        pen = QPen(col, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2, self.height() / 2
        # lid: horizontal line with small knob
        lid_y = cy - 5
        p.drawLine(QPointF(cx - 6, lid_y), QPointF(cx + 6, lid_y))
        p.drawLine(QPointF(cx - 2, lid_y), QPointF(cx - 2, lid_y - 2.5))
        p.drawLine(QPointF(cx - 2, lid_y - 2.5), QPointF(cx + 2, lid_y - 2.5))
        p.drawLine(QPointF(cx + 2, lid_y - 2.5), QPointF(cx + 2, lid_y))
        # can body: tapered trapezoid
        top_y = lid_y + 1.5
        bot_y = cy + 7
        p.drawLine(QPointF(cx - 5, top_y), QPointF(cx - 4, bot_y))
        p.drawLine(QPointF(cx - 4, bot_y), QPointF(cx + 4, bot_y))
        p.drawLine(QPointF(cx + 4, bot_y), QPointF(cx + 5, top_y))
        # vertical lines inside
        for dx in (-1.5, 1.5):
            p.drawLine(QPointF(cx + dx, top_y + 2), QPointF(cx + dx, bot_y - 1.5))
        p.end()


class _AddSiblingButton(_TintedButton):
    """Add-sibling icon: small rectangle with a + below it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setToolTip("Add sibling")

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_hover_bg(p)
        col = QColor("#aaaaaa") if not self.underMouse() else QColor("#666666")
        pen = QPen(col, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2, self.height() / 2
        # small rectangle (existing item)
        rw, rh = 8, 4
        p.drawRoundedRect(QRectF(cx - rw, cy - 6, rw * 2, rh), 1.5, 1.5)
        # plus sign below
        plus_y = cy + 4
        arm = 3.5
        p.drawLine(QPointF(cx - arm, plus_y), QPointF(cx + arm, plus_y))
        p.drawLine(QPointF(cx, plus_y - arm), QPointF(cx, plus_y + arm))
        p.end()


# ---------------------------------------------------------------------------
# Options row (toggled by C)
# ---------------------------------------------------------------------------

class _OptionsRow(QWidget):
    state_selected = Signal(int)
    add_sibling = Signal()
    delete_item = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(BTN_SIZE + 16 + SPACING, 4, 0, 6)
        self._layout.setSpacing(4)

    def rebuild(self, checklist: Checklist, current_state: int):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for st in sorted(checklist.states, key=lambda s: s.number):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            active = st.number == current_state
            border = "2px solid #333" if active else "1px solid #ddd"
            bg = "#f0f0f0" if active else "transparent"
            btn.setStyleSheet(
                "QPushButton { background: " + bg + "; border: " + border
                + "; border-radius: 5px; }"
                " QPushButton:hover { background: #e8e8e8; }"
            )
            btn.clicked.connect(lambda checked, n=st.number: self.state_selected.emit(n))
            btn._sym = st.symbol
            btn._col = st.color
            btn.paintEvent = lambda ev, b=btn: self._paint_state_btn(b, ev)
            self._layout.addWidget(btn)

        self._layout.addStretch()

        sib_btn = _AddSiblingButton()
        sib_btn.clicked.connect(self.add_sibling.emit)
        self._layout.addWidget(sib_btn)

        del_btn = _DeleteButton()
        del_btn.clicked.connect(self.delete_item.emit)
        self._layout.addWidget(del_btn)

    @staticmethod
    def _paint_state_btn(btn, ev):
        QPushButton.paintEvent(btn, ev)
        p = QPainter(btn)
        draw_symbol(p, QRectF(btn.rect()), btn._sym, btn._col, 18)
        p.end()


# ---------------------------------------------------------------------------
# Main item card widget
# ---------------------------------------------------------------------------

class ChecklistItemWidget(QFrame):
    changed = Signal()
    enter_pressed = Signal(object)
    delete_requested = Signal(object)
    add_child_requested = Signal(object)

    def __init__(self, item_id: str, text: str, state_number: int,
                 collapsed: bool, checklist: Checklist, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.state_number = state_number
        self._collapsed = collapsed
        self._checklist = checklist
        self._border_color = "#888"
        self._fill_color = "#fafafa"
        self._drop_zone: str | None = None
        self._options_open = False
        self._last_click_time: float = 0
        self._enter_armed = False

        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setFrameShape(QFrame.Shape.NoFrame)

        main = QVBoxLayout(self)
        main.setContentsMargins(10, 6, 6, 6)
        main.setSpacing(0)

        # ---- header row: A  B  text  D  C  E ----
        header = QHBoxLayout()
        header.setSpacing(SPACING)

        # A - drag grip
        self._grip = _DragGrip(self)
        self._grip.drag_requested.connect(self._start_drag)
        header.addWidget(self._grip, 0, Qt.AlignmentFlag.AlignTop)

        # B - indicator
        self._indicator = _IndicatorButton(self)
        self._indicator.clicked.connect(self._on_indicator_click)
        self._indicator.long_pressed.connect(self._on_indicator_long)
        header.addWidget(self._indicator, 0, Qt.AlignmentFlag.AlignTop)

        # Text
        self._text = _AutoTextEdit(text)
        self._text.text_changed_signal.connect(lambda: self.changed.emit())
        self._text.enter_pressed.connect(lambda: self.enter_pressed.emit(self))
        header.addWidget(self._text, 1)

        # D - collapse (before C now)
        self._collapse_btn = _CollapseButton(self)
        self._collapse_btn.clicked.connect(self._toggle_collapsed)
        header.addWidget(self._collapse_btn, 0, Qt.AlignmentFlag.AlignTop)

        # C - options toggle
        self._opt_toggle = _OptionsToggle(self)
        self._opt_toggle.clicked.connect(self._toggle_options)
        header.addWidget(self._opt_toggle, 0, Qt.AlignmentFlag.AlignTop)

        # E - add child
        self._add_btn = _AddChildButton(self)
        self._add_btn.clicked.connect(self._on_add_child_click)
        header.addWidget(self._add_btn, 0, Qt.AlignmentFlag.AlignTop)

        main.addLayout(header)

        # ---- options row --------------------------------------------------
        self._opts_row = _OptionsRow(self)
        self._opts_row.state_selected.connect(self._set_state)
        self._opts_row.add_sibling.connect(lambda: self.enter_pressed.emit(self))
        self._opts_row.delete_item.connect(lambda: self.delete_requested.emit(self))
        self._opts_row.setVisible(False)
        main.addWidget(self._opts_row)

        # ---- children container -------------------------------------------
        self._children_widget = QWidget()
        self._children_layout = QVBoxLayout(self._children_widget)
        self._children_layout.setContentsMargins(20, 6, 0, 0)
        self._children_layout.setSpacing(6)
        self._children_widget.setVisible(False)
        main.addWidget(self._children_widget)

        self._apply_state()
        self._sync_collapse()

    # -- public API --------------------------------------------------------

    @property
    def children_layout(self) -> QVBoxLayout:
        return self._children_layout

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def text(self) -> str:
        return self._text.toPlainText()

    def focus_text(self, select_all=False):
        self._text.setFocus()
        if select_all:
            self._text.selectAll()

    def set_checklist_ref(self, cl: Checklist):
        self._checklist = cl

    def child_count(self) -> int:
        c = 0
        for i in range(self._children_layout.count()):
            if isinstance(self._children_layout.itemAt(i).widget(), ChecklistItemWidget):
                c += 1
        return c

    def update_collapse_visibility(self):
        has = self.child_count() > 0
        self._collapse_btn.set_state(not self._collapsed, has)
        if not has:
            self._collapsed = False
            self._children_widget.setVisible(False)
        else:
            self._children_widget.setVisible(not self._collapsed)

    # -- state / colors ----------------------------------------------------

    def _apply_state(self):
        st = self._checklist.state_by_number(self.state_number) if self._checklist else None
        color = st.color if st else "#888888"
        symbol = st.symbol if st else "empty"
        self._border_color = color
        self._fill_color = blend_with_bg(color, 0.08)
        self._indicator.set_indicator(symbol, color)
        self._grip.set_item_color(self._fill_color)
        self._collapse_btn.set_item_color(self._fill_color)
        self._opt_toggle.set_item_color(self._fill_color)
        self._add_btn.set_item_color(self._fill_color)
        self.update()

    def refresh_colors(self):
        self._apply_state()
        for i in range(self._children_layout.count()):
            w = self._children_layout.itemAt(i).widget()
            if isinstance(w, ChecklistItemWidget):
                w.set_checklist_ref(self._checklist)
                w.refresh_colors()

    def _set_state(self, number: int):
        self.state_number = number
        self._apply_state()
        if self._options_open:
            self._opts_row.rebuild(self._checklist, self.state_number)
        self.changed.emit()

    # -- indicator click behavior ------------------------------------------

    def _on_indicator_click(self):
        if not self._checklist:
            return
        if self.state_number == -1:
            return

        now = time.monotonic()
        elapsed = now - self._last_click_time
        self._last_click_time = now

        if elapsed > 1.0:
            target = self._checklist.smart_click_target(self.state_number)
            self._set_state(target)
        else:
            nxt = self._checklist.next_checkbox_state(self.state_number)
            self._set_state(nxt.number)

    def _on_indicator_long(self):
        if not self._checklist:
            return
        if self.state_number == -1:
            self._set_state(0)
        else:
            self._set_state(-1)

    # -- options row -------------------------------------------------------

    def _toggle_options(self):
        self._options_open = not self._options_open
        if self._options_open and self._checklist:
            self._opts_row.rebuild(self._checklist, self.state_number)
        self._opts_row.setVisible(self._options_open)

    # -- add child ---------------------------------------------------------

    def _on_add_child_click(self):
        if self._collapsed and self.child_count() > 0:
            self._collapsed = False
            self._sync_collapse()
            self.changed.emit()
        self.add_child_requested.emit(self)

    # -- collapse / expand -------------------------------------------------

    def _toggle_collapsed(self):
        self._collapsed = not self._collapsed
        self._sync_collapse()
        self.changed.emit()

    def _sync_collapse(self):
        has = self.child_count() > 0
        self._collapse_btn.set_state(not self._collapsed, has)
        self._children_widget.setVisible(not self._collapsed)

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
            p.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 6, 6)
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
        ratio = event.position().y() / max(self.height(), 1)
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

    # -- keyboard on item frame --------------------------------------------

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key.Key_Return and not ev.modifiers() and self._enter_armed:
            self._enter_armed = False
            self.enter_pressed.emit(self)
            return
        self._enter_armed = False
        super().keyPressEvent(ev)

    def focusOutEvent(self, ev):
        self._enter_armed = False
        super().focusOutEvent(ev)

    # -- context menu ------------------------------------------------------

    def contextMenuEvent(self, event):
        self._toggle_options()


# ---------------------------------------------------------------------------
# Add Item card  — mirrors item card styling exactly, click anywhere to add
# ---------------------------------------------------------------------------

class AddItemCard(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._border_color = "#bbbbbb"
        self._fill_color = blend_with_bg("#bbbbbb", 0.08)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(SPACING)

        # Grip-width spacer (no drag handle, but same visual indent)
        spacer = QWidget()
        spacer.setFixedSize(GRIP_W, BTN_SIZE)
        spacer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(spacer, 0, Qt.AlignmentFlag.AlignTop)

        # Plus icon — same size as indicator (BTN_SIZE square)
        self._icon = QWidget()
        self._icon.setFixedSize(BTN_SIZE, BTN_SIZE)
        self._icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._icon.paintEvent = self._paint_icon
        layout.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignTop)

        self._label = QLabel("Add Item")
        self._label.setStyleSheet(
            "QLabel { color: #333333; font-size: 13px; background: transparent; }"
        )
        layout.addWidget(self._label, 1)

    def update_from_checklist(self, checklist):
        """Sync border/fill to match state -1 of this checklist."""
        st = checklist.state_by_number(-1) if checklist else None
        color = st.color if st else "#bbbbbb"
        self._border_color = color
        self._fill_color = blend_with_bg(color, 0.08)
        self.update()

    # -- painting ----------------------------------------------------------

    def _paint_icon(self, ev):
        p = QPainter(self._icon)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Use same color logic as grip: darker version of fill
        c = QColor(self._fill_color)
        col = QColor(max(c.red()-50,0), max(c.green()-50,0), max(c.blue()-50,0))
        p.setPen(QPen(col, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        cx, cy = self._icon.width() / 2, self._icon.height() / 2
        arm = 6
        p.drawLine(QPointF(cx - arm, cy), QPointF(cx + arm, cy))
        p.drawLine(QPointF(cx, cy - arm), QPointF(cx, cy + arm))
        p.end()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(self._border_color), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 8, 8)
        p.end()

    # -- interaction -------------------------------------------------------

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
