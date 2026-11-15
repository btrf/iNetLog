"""Флаги языков (RU/GB), нарисованные программно — без внешних картинок."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

FLAG_RATIO = 1.5  # ширина : высота


def flag_pixmap(code: str, height: int = 15) -> QPixmap:
    """Возвращает pixmap флага нужного языка с прозрачными углами."""
    code = "ru" if code == "ru" else "en"
    width = max(2, round(height * FLAG_RATIO))
    dpr = 2.0
    pixmap = QPixmap(round(width * dpr), round(height * dpr))
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    rect = QRectF(0.0, 0.0, float(width), float(height))
    clip = QPainterPath()
    clip.addRoundedRect(rect, 2.0, 2.0)
    painter.setClipPath(clip)

    if code == "ru":
        _draw_russia(painter, rect)
    else:
        _draw_uk(painter, rect)

    painter.setClipping(False)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(15, 23, 42, 90), 1.0))
    painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 2.0, 2.0)
    painter.end()
    return pixmap


def flag_icon(code: str, height: int = 15) -> QIcon:
    """Иконка флага для кнопки или пункта меню."""
    return QIcon(flag_pixmap(code, height))


def _draw_russia(painter: QPainter, rect: QRectF) -> None:
    height = rect.height() / 3.0
    painter.fillRect(rect, QColor("#ffffff"))
    painter.fillRect(
        QRectF(rect.left(), rect.top() + height, rect.width(), height),
        QColor("#0039a6"),
    )
    painter.fillRect(
        QRectF(rect.left(), rect.top() + 2 * height, rect.width(), height),
        QColor("#d52b1e"),
    )


def _draw_uk(painter: QPainter, rect: QRectF) -> None:
    width, height = rect.width(), rect.height()
    painter.fillRect(rect, QColor("#012169"))

    # Белые диагонали.
    painter.setPen(
        QPen(
            QColor("#ffffff"),
            height * 0.30,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.SquareCap,
        )
    )
    painter.drawLine(rect.topLeft(), rect.bottomRight())
    painter.drawLine(rect.bottomLeft(), rect.topRight())

    # Красные диагонали (упрощённо, без контр-смещения).
    painter.setPen(
        QPen(
            QColor("#c8102e"),
            height * 0.12,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.SquareCap,
        )
    )
    painter.drawLine(rect.topLeft(), rect.bottomRight())
    painter.drawLine(rect.bottomLeft(), rect.topRight())

    # Белый крест.
    painter.fillRect(
        QRectF(rect.left(), rect.top() + height * 2 / 5, width, height / 5),
        QColor("#ffffff"),
    )
    painter.fillRect(
        QRectF(rect.left() + width / 2 - height / 6, rect.top(), height / 3, height),
        QColor("#ffffff"),
    )

    # Красный крест.
    painter.fillRect(
        QRectF(rect.left(), rect.top() + height * 0.4, width, height * 0.2),
        QColor("#c8102e"),
    )
    painter.fillRect(
        QRectF(rect.left() + width / 2 - height / 10, rect.top(), height / 5, height),
        QColor("#c8102e"),
    )
