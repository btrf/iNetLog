"""Иконки интерфейса, нарисованные программно (без внешних файлов)."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def theme_icon(theme: str, size: int = 18) -> QIcon:
    """Иконка переключения темы: солнце для тёмной темы, луна для светлой."""
    dpr = 2.0
    pixmap = QPixmap(int(size * dpr), int(size * dpr))
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    if theme == "light":
        _draw_moon(painter, float(size))
    else:
        _draw_sun(painter, float(size))

    painter.end()
    return QIcon(pixmap)


def _draw_sun(painter: QPainter, size: float) -> None:
    color = QColor("#fbbf24")
    center = QPointF(size / 2.0, size / 2.0)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(center, size * 0.23, size * 0.23)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(
        QPen(
            color,
            max(1.0, size * 0.085),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
    )
    for step in range(8):
        angle = math.radians(step * 45.0)
        inner = size * 0.33
        outer = size * 0.45
        painter.drawLine(
            QPointF(
                center.x() + math.cos(angle) * inner,
                center.y() + math.sin(angle) * inner,
            ),
            QPointF(
                center.x() + math.cos(angle) * outer,
                center.y() + math.sin(angle) * outer,
            ),
        )


def _draw_moon(painter: QPainter, size: float) -> None:
    color = QColor("#475569")
    full = QPainterPath()
    full.addEllipse(QRectF(size * 0.16, size * 0.12, size * 0.66, size * 0.76))
    cutout = QPainterPath()
    cutout.addEllipse(QRectF(size * 0.34, size * 0.02, size * 0.66, size * 0.76))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPath(full.subtracted(cutout))
