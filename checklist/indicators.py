"""Custom-painted indicator symbols for checklist states."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen


def draw_symbol(p: QPainter, rect: QRectF, symbol: str, color: str, size: float = 16) -> None:
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(color)
    cx, cy = rect.center().x(), rect.center().y()

    if symbol == "bullet":
        r = size * 0.15
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(QPointF(cx, cy), r, r)

    elif symbol == "empty":
        s = size * 0.85
        box = QRectF(cx - s / 2, cy - s / 2, s, s)
        p.setPen(QPen(c, 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(box, 3, 3)

    elif symbol == "check":
        s = size * 0.85
        box = QRectF(cx - s / 2, cy - s / 2, s, s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(box, 3, 3)
        path = QPainterPath()
        path.moveTo(box.left() + s * 0.20, cy)
        path.lineTo(box.left() + s * 0.40, cy + s * 0.22)
        path.lineTo(box.left() + s * 0.78, cy - s * 0.22)
        p.setPen(QPen(QColor("#ffffff"), 1.8, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    elif symbol == "clock":
        r = size * 0.38
        p.setPen(QPen(c, 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.drawLine(QPointF(cx, cy), QPointF(cx, cy - r * 0.55))
        p.drawLine(QPointF(cx, cy), QPointF(cx + r * 0.45, cy))

    elif symbol == "minus":
        s = size * 0.85
        box = QRectF(cx - s / 2, cy - s / 2, s, s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(box, 3, 3)
        p.setPen(QPen(QColor("#ffffff"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(box.left() + s * 0.22, cy),
                    QPointF(box.right() - s * 0.22, cy))

    elif symbol == "square":
        s = size * 0.85
        box = QRectF(cx - s / 2, cy - s / 2, s, s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(box, 3, 3)

    elif symbol == "x":
        s = size * 0.85
        box = QRectF(cx - s / 2, cy - s / 2, s, s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(box, 3, 3)
        p.setPen(QPen(QColor("#ffffff"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        m = s * 0.25
        p.drawLine(QPointF(box.left() + m, box.top() + m),
                    QPointF(box.right() - m, box.bottom() - m))
        p.drawLine(QPointF(box.right() - m, box.top() + m),
                    QPointF(box.left() + m, box.bottom() - m))

    elif symbol == "star":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        import math
        r_outer = size * 0.42
        r_inner = r_outer * 0.45
        path = QPainterPath()
        for i in range(10):
            r = r_outer if i % 2 == 0 else r_inner
            angle = math.pi / 2 + i * math.pi / 5
            px = cx + r * math.cos(angle)
            py = cy - r * math.sin(angle)
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)
        path.closeSubpath()
        p.drawPath(path)

    elif symbol == "exclaim":
        s = size * 0.85
        box = QRectF(cx - s / 2, cy - s / 2, s, s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(box, 3, 3)
        p.setPen(QPen(QColor("#ffffff"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(cx, box.top() + s * 0.18),
                    QPointF(cx, box.bottom() - s * 0.38))
        p.drawPoint(QPointF(cx, box.bottom() - s * 0.20))

    elif symbol == "question":
        p.setPen(QPen(c, 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = size * 0.38
        p.drawEllipse(QPointF(cx, cy), r, r)
        font = p.font()
        font.setPixelSize(int(size * 0.4))
        font.setBold(True)
        p.setFont(font)
        p.setPen(c)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "?")

    else:
        font = p.font()
        font.setPixelSize(int(size * 0.55))
        p.setFont(font)
        p.setPen(c)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, symbol[:2])

    p.restore()
