from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .item_widget import BTN_SIZE, GRIP_W, SPACING, _DragGrip, _OptionsToggle
from .theme import ACCENT, blend_with_bg

MIME_SIDEBAR = "application/x-checklist-sidebar"
_COLOR = "#bbbbbb"
_FILL = blend_with_bg(_COLOR, 0.08)
_ACTIVE_COLOR = "#888888"


# ---------------------------------------------------------------------------
# Individual checklist card in the sidebar
# ---------------------------------------------------------------------------

class SidebarListCard(QFrame):
    selected = Signal(object)                   # emits self
    delete_requested = Signal(object)           # emits self
    rename_requested = Signal(object, str)      # emits self, new_name
    # for brand-new cards (no backing file yet)
    new_committed = Signal(object, str)         # emits self, name
    new_cancelled = Signal(object)              # emits self

    def __init__(self, path: Path, name: str, parent=None, is_new: bool = False):
        super().__init__(parent)
        self._path = path
        self._name = name
        self._active = False
        self._is_new = is_new
        self._options_open = False
        self._drop_zone: str | None = None

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAcceptDrops(True)

        main = QVBoxLayout(self)
        main.setContentsMargins(10, 6, 6, 6)
        main.setSpacing(0)

        # ---- header: grip | name label | opts toggle ----
        header = QHBoxLayout()
        header.setSpacing(SPACING)

        self._grip = _DragGrip(self)
        self._grip.drag_requested.connect(self._start_drag)
        self._grip.set_item_color(_FILL)
        header.addWidget(self._grip, 0, Qt.AlignmentFlag.AlignTop)

        self._label = QLabel(name if not is_new else "")
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._label.setStyleSheet(
            "QLabel { color: #333333; font-size: 13px; background: transparent; }"
        )
        header.addWidget(self._label, 1)

        self._opt_toggle = _OptionsToggle(self)
        self._opt_toggle.set_item_color(_FILL)
        self._opt_toggle.clicked.connect(self._toggle_options)
        header.addWidget(self._opt_toggle, 0, Qt.AlignmentFlag.AlignTop)

        main.addLayout(header)

        # ---- options row ----
        self._opts_widget = QWidget()
        opts_lay = QHBoxLayout(self._opts_widget)
        opts_lay.setContentsMargins(GRIP_W + SPACING, 4, 6, 6)
        opts_lay.setSpacing(6)

        self._name_edit = QLineEdit(name)
        self._name_edit.setPlaceholderText("Checklist name…")
        self._name_edit.setStyleSheet(
            "QLineEdit { background: #fff; border: 1px solid #ddd; border-radius: 4px;"
            " padding: 3px 6px; color: #333; font-size: 12px; }"
            " QLineEdit:focus { border-color: #aaa; }"
        )
        self._name_edit.returnPressed.connect(self._commit)
        opts_lay.addWidget(self._name_edit, 1)

        self._del_btn = QPushButton("Delete")
        self._del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._del_btn.setStyleSheet(
            "QPushButton { background: #f5f5f5; border: 1px solid #ddd;"
            " border-radius: 4px; padding: 3px 10px; color: #c44; font-size: 11px; }"
            " QPushButton:hover { background: #fee; border-color: #c88; }"
        )
        self._del_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        self._del_btn.setVisible(not is_new)
        opts_lay.addWidget(self._del_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setStyleSheet(
            "QPushButton { background: #f5f5f5; border: 1px solid #ddd;"
            " border-radius: 4px; padding: 3px 10px; color: #888; font-size: 11px; }"
            " QPushButton:hover { background: #eee; }"
        )
        self._cancel_btn.clicked.connect(lambda: self.new_cancelled.emit(self))
        self._cancel_btn.setVisible(is_new)
        opts_lay.addWidget(self._cancel_btn)

        self._opts_widget.setVisible(is_new)
        main.addWidget(self._opts_widget)

        if is_new:
            self._options_open = True
            QTimer.singleShot(50, self._focus_edit)

    def _focus_edit(self):
        self._name_edit.setFocus()
        self._name_edit.selectAll()

    # -- public API --------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    @property
    def name(self) -> str:
        return self._name

    def set_path(self, path: Path):
        self._path = path

    def set_name(self, name: str):
        self._name = name
        self._label.setText(name)
        self._name_edit.setText(name)

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def finalize_new(self, path: Path, name: str):
        """Convert a pending new card into a real card after file is created."""
        self._is_new = False
        self._path = path
        self.set_name(name)
        self._del_btn.setVisible(True)
        self._cancel_btn.setVisible(False)
        self._options_open = False
        self._opts_widget.setVisible(False)

    # -- options -----------------------------------------------------------

    def _toggle_options(self):
        self._options_open = not self._options_open
        if self._options_open:
            self._name_edit.setText(self._name)
            QTimer.singleShot(50, self._focus_edit)
        self._opts_widget.setVisible(self._options_open)

    def _commit(self):
        new_name = self._name_edit.text().strip()
        if self._is_new:
            if new_name:
                self.new_committed.emit(self, new_name)
            else:
                self.new_cancelled.emit(self)
        else:
            if new_name and new_name != self._name:
                self.rename_requested.emit(self, new_name)
            self._options_open = False
            self._opts_widget.setVisible(False)

    # -- painting ----------------------------------------------------------

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        p.fillPath(path, QColor(_FILL))
        border = QColor(_ACTIVE_COLOR) if self._active else QColor(_COLOR)
        pen_w = 2.5 if self._active else 2.0
        p.setPen(QPen(border, pen_w))
        p.drawRoundedRect(rect, 8, 8)

        if self._drop_zone == "before":
            p.setPen(QPen(QColor(ACCENT), 2.5))
            p.drawLine(QPointF(8, 1.5), QPointF(self.width() - 8, 1.5))
        elif self._drop_zone == "after":
            p.setPen(QPen(QColor(ACCENT), 2.5))
            y = self.height() - 1.5
            p.drawLine(QPointF(8, y), QPointF(self.width() - 8, y))
        p.end()

    # -- interaction -------------------------------------------------------

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self)
        super().mousePressEvent(ev)

    def contextMenuEvent(self, ev):
        self._toggle_options()

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key.Key_Escape:
            if self._is_new:
                self.new_cancelled.emit(self)
            else:
                self._options_open = False
                self._opts_widget.setVisible(False)
        else:
            super().keyPressEvent(ev)

    # -- drag & drop -------------------------------------------------------

    def _start_drag(self):
        if self._is_new:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_SIDEBAR, str(self._path).encode())
        drag.setMimeData(mime)
        pix = self.grab()
        if pix.width() > 300:
            pix = pix.scaledToWidth(300, Qt.TransformationMode.SmoothTransformation)
        drag.setPixmap(pix)
        drag.setHotSpot(self._grip.mapTo(self, self._grip.rect().center()))
        drag.exec(Qt.DropAction.MoveAction)

    def _src_path(self, event) -> str | None:
        md = event.mimeData()
        if md and md.hasFormat(MIME_SIDEBAR):
            return md.data(MIME_SIDEBAR).data().decode()
        return None

    def dragEnterEvent(self, event):
        src = self._src_path(event)
        if src and src != str(self._path):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        src = self._src_path(event)
        if not src or src == str(self._path):
            return
        ratio = event.position().y() / max(self.height(), 1)
        self._drop_zone = "before" if ratio < 0.5 else "after"
        self.update()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._drop_zone = None
        self.update()

    def dropEvent(self, event):
        src = self._src_path(event)
        zone = self._drop_zone
        self._drop_zone = None
        self.update()
        if src and zone:
            event.acceptProposedAction()
            w = self.parent()
            while w:
                if isinstance(w, SidebarView):
                    w.handle_drop(Path(src), self._path, zone == "before")
                    return
                w = w.parent()


# ---------------------------------------------------------------------------
# Add List card
# ---------------------------------------------------------------------------

class AddListCard(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(SPACING)

        spacer = QWidget()
        spacer.setFixedSize(GRIP_W, BTN_SIZE)
        spacer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(spacer, 0, Qt.AlignmentFlag.AlignTop)

        self._icon = QWidget()
        self._icon.setFixedSize(BTN_SIZE, BTN_SIZE)
        self._icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._icon.paintEvent = self._paint_icon
        layout.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignTop)

        label = QLabel("Add List")
        label.setStyleSheet(
            "QLabel { color: #333333; font-size: 13px; background: transparent; }"
        )
        layout.addWidget(label, 1)

    def _paint_icon(self, ev):
        p = QPainter(self._icon)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(_COLOR), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        cx, cy = self._icon.width() / 2, self._icon.height() / 2
        arm = 6
        p.drawLine(QPointF(cx - arm, cy), QPointF(cx + arm, cy))
        p.drawLine(QPointF(cx, cy - arm), QPointF(cx, cy + arm))
        p.end()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(_COLOR), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 8, 8)
        p.end()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


# ---------------------------------------------------------------------------
# Sidebar scroll view — holds all cards + add-list card
# ---------------------------------------------------------------------------

class SidebarView(QScrollArea):
    checklist_selected = Signal(object)         # Path
    checklist_deleted = Signal(object)          # Path
    checklist_renamed = Signal(object, str)     # Path, new_name
    pending_committed = Signal(object, str)     # card, name  (new card committed)
    add_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            "QScrollArea { background: transparent; }"
            " QScrollBar:vertical { background: #f0f0f0; width: 6px; margin: 0; }"
            " QScrollBar::handle:vertical { background: #d0d0d0; min-height: 20px;"
            " border-radius: 3px; }"
            " QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        self._content = QWidget()
        self._content.setStyleSheet("QWidget { background: transparent; }")
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(6)
        self.setWidget(self._content)

        self._add_card = AddListCard()
        self._add_card.clicked.connect(self.add_requested.emit)
        self._layout.addWidget(self._add_card)
        self._layout.addStretch()

        self._cards: list[SidebarListCard] = []
        self._active_path: Path | None = None

    # -- public API --------------------------------------------------------

    def load_paths(self, paths: list[Path], active_path: Path | None = None):
        for card in self._cards:
            self._layout.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self._cards = []
        for p in paths:
            self._make_card(p)
        self.set_active(active_path)

    def add_path(self, p: Path, name: str) -> SidebarListCard:
        return self._make_card(p, name)

    def start_new_card(self) -> SidebarListCard:
        """Insert a pending card with empty name field ready for typing."""
        card = SidebarListCard(Path("__pending__"), "", self._content, is_new=True)
        card.new_committed.connect(self._on_new_committed)
        card.new_cancelled.connect(self._on_new_cancelled)
        insert_idx = self._layout.indexOf(self._add_card)
        self._layout.insertWidget(insert_idx, card)
        self._cards.append(card)
        return card

    def remove_path(self, path: Path):
        for card in self._cards:
            if card.path == path:
                self._cards.remove(card)
                self._layout.removeWidget(card)
                card.setParent(None)
                card.deleteLater()
                break

    def update_name(self, path: Path, name: str):
        for card in self._cards:
            if card.path == path:
                card.set_name(name)
                break

    def set_active(self, path: Path | None):
        self._active_path = path
        for card in self._cards:
            card.set_active(card.path == path)

    def handle_drop(self, src_path: Path, target_path: Path, above: bool):
        src_card = next((c for c in self._cards if c.path == src_path), None)
        target_card = next((c for c in self._cards if c.path == target_path), None)
        if not src_card or not target_card or src_card is target_card:
            return
        self._cards.remove(src_card)
        target_idx = self._cards.index(target_card)
        if not above:
            target_idx += 1
        self._cards.insert(target_idx, src_card)
        for card in self._cards:
            self._layout.removeWidget(card)
        insert_base = self._layout.indexOf(self._add_card)
        for i, card in enumerate(self._cards):
            self._layout.insertWidget(insert_base + i, card)

    # -- internal ----------------------------------------------------------

    def _make_card(self, p: Path, name: str = "") -> SidebarListCard:
        if not name:
            try:
                from .xml_io import load_checklist
                name = load_checklist(p).name
            except Exception:
                name = p.stem
        card = SidebarListCard(p, name, self._content)
        card.selected.connect(self._on_selected)
        card.delete_requested.connect(self._on_delete)
        card.rename_requested.connect(self._on_rename)
        insert_idx = self._layout.indexOf(self._add_card)
        self._layout.insertWidget(insert_idx, card)
        self._cards.append(card)
        return card

    def _on_selected(self, card: SidebarListCard):
        self.set_active(card.path)
        self.checklist_selected.emit(card.path)

    def _on_delete(self, card: SidebarListCard):
        self.checklist_deleted.emit(card.path)

    def _on_rename(self, card: SidebarListCard, new_name: str):
        self.checklist_renamed.emit(card.path, new_name)

    def _on_new_committed(self, card: SidebarListCard, name: str):
        self.pending_committed.emit(card, name)

    def _on_new_cancelled(self, card: SidebarListCard):
        self._cards.remove(card)
        self._layout.removeWidget(card)
        card.setParent(None)
        card.deleteLater()
