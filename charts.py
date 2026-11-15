"""Виджет графика скорости на QtCharts."""

from __future__ import annotations

import math
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Optional, Sequence

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDate, QDateTime, QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRubberBand,
    QVBoxLayout,
    QWidget,
)

from database import Measurement
from i18n import tr


def _ratio(value: float, start: float, size: float) -> float:
    """Доля (0..1) положения value внутри отрезка [start, start + size]."""
    if size <= 0:
        return 0.5
    return min(1.0, max(0.0, (value - start) / size))


class _ZoomChartView(QChartView):
    """График с масштабированием колесом, рамкой и панорамированием."""

    def __init__(self, chart: QChart, owner: "INetChart") -> None:
        super().__init__(chart)
        self._owner = owner
        self._rubber = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
        self._origin = QPoint()
        self._panning = False
        self._pan_last = QPoint()
        self.setToolTip(tr("chart.controls"))

    # -------------------------------------------------------------- события
    def wheelEvent(self, event) -> None:  # noqa: N802 - метод Qt
        delta = event.angleDelta().y()
        if delta:
            self._owner.zoom_at(event.position(), 0.8 if delta > 0 else 1.25)
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - метод Qt
        button = event.button()
        if button == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._start_pan(event.position().toPoint())
            else:
                self._origin = event.position().toPoint()
                self._rubber.setGeometry(QRect(self._origin, QSize()))
                self._rubber.show()
            event.accept()
            return
        if button == Qt.MouseButton.MiddleButton:
            self._start_pan(event.position().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - метод Qt
        if self._panning:
            position = event.position().toPoint()
            self._owner.pan_by(
                position.x() - self._pan_last.x(),
                position.y() - self._pan_last.y(),
            )
            self._pan_last = position
            event.accept()
            return
        if self._rubber.isVisible():
            self._rubber.setGeometry(
                QRect(self._origin, event.position().toPoint()).normalized()
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - метод Qt
        if self._panning and event.button() in (
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
        ):
            self._stop_pan()
            event.accept()
            return
        if self._rubber.isVisible() and event.button() == Qt.MouseButton.LeftButton:
            area = QRectF(self._rubber.geometry())
            self._rubber.hide()
            self._owner.zoom_to_rect(area)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - метод Qt
        self._owner.reset_zoom()
        event.accept()

    # -------------------------------------------------------------- панорама
    def _start_pan(self, position: QPoint) -> None:
        self._panning = True
        self._pan_last = position
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _stop_pan(self) -> None:
        self._panning = False
        self.unsetCursor()


CHART_THEMES: dict[str, dict[str, object]] = {
    "dark": {
        "chart_theme": QChart.ChartTheme.ChartThemeDark,
        "download": QColor("#38bdf8"),
        "upload": QColor("#f59e0b"),
        "grid": QColor("#243247"),
        "label": QColor("#94a3b8"),
        "title": QColor("#e2e8f0"),
    },
    "light": {
        "chart_theme": QChart.ChartTheme.ChartThemeLight,
        "download": QColor("#0284c7"),
        "upload": QColor("#ea580c"),
        "grid": QColor("#dbe3ef"),
        "label": QColor("#5b6b82"),
        "title": QColor("#0b1220"),
    },
}


def _nice_upper_bound(value: float, ticks: int = 5) -> float:
    """Округляет верхнюю границу оси Y до «красивого» числа."""
    if value <= 0:
        return 10.0
    padded = value * 1.05
    raw_step = padded / ticks
    magnitude = 10 ** math.floor(math.log10(raw_step))
    step = 10.0 * magnitude
    for multiplier in (1.0, 2.0, 2.5, 5.0, 10.0):
        candidate = multiplier * magnitude
        if candidate >= raw_step:
            step = candidate
            break
    return math.ceil(padded / step) * step


class INetChart(QWidget):
    """График Download/Upload по времени с пресетами и произвольным диапазоном дат."""

    range_changed = Signal()

    RANGES: tuple[tuple[str, object], ...] = (
        ("range.24h", timedelta(hours=24)),
        ("range.7d", timedelta(days=7)),
        ("range.30d", timedelta(days=30)),
        ("range.all", None),
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._normalizing = False
        self._show_download = True
        self._show_upload = True
        self._zoomed = False
        self._auto_y = True
        self._has_data = False
        self._full_x: Optional[tuple[float, float]] = None
        self._full_y: tuple[float, float] = (0.0, 100.0)
        self._build_ui()
        self.apply_theme("dark")

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 0)
        header.setSpacing(8)

        self._title_label = QLabel(tr("chart.title"))
        self._title_label.setObjectName("sectionTitle")

        self._period_label = QLabel(tr("chart.period"))
        self._period_label.setObjectName("muted")

        self.range_combo = QComboBox()
        for key, delta in self.RANGES:
            self.range_combo.addItem(tr(key), delta)
        self.range_combo.addItem(tr("range.custom"), "custom")
        self.range_combo.currentIndexChanged.connect(self._on_range_changed)

        self._custom_widget = QWidget()
        custom_layout = QHBoxLayout(self._custom_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(6)

        today = QDate.currentDate()
        self.from_edit = QDateEdit(today.addDays(-6))
        self.from_edit.setCalendarPopup(True)
        self.from_edit.setDisplayFormat("dd.MM.yyyy")
        self.from_edit.setMinimumWidth(112)
        self.to_edit = QDateEdit(today)
        self.to_edit.setCalendarPopup(True)
        self.to_edit.setDisplayFormat("dd.MM.yyyy")
        self.to_edit.setMinimumWidth(112)

        self.from_edit.dateChanged.connect(self._on_dates_changed)
        self.to_edit.dateChanged.connect(self._on_dates_changed)

        from_label = QLabel(tr("chart.from"))
        from_label.setObjectName("muted")
        to_label = QLabel(tr("chart.to"))
        to_label.setObjectName("muted")

        self._from_label = from_label
        self._to_label = to_label

        custom_layout.addWidget(from_label)
        custom_layout.addWidget(self.from_edit)
        custom_layout.addWidget(to_label)
        custom_layout.addWidget(self.to_edit)
        self._custom_widget.setVisible(False)

        header.addWidget(self._title_label)
        self.zoom_reset_button = QPushButton(tr("chart.reset_zoom"))
        self.zoom_reset_button.setVisible(False)
        self.zoom_reset_button.setToolTip(tr("chart.reset_zoom_tooltip"))
        self.zoom_reset_button.clicked.connect(self.reset_zoom)
        header.addWidget(self.zoom_reset_button)
        header.addStretch(1)
        header.addWidget(self._period_label)
        header.addWidget(self.range_combo)
        header.addWidget(self._custom_widget)

        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.setPlotAreaBackgroundVisible(False)
        self._chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        self._chart.legend().hide()

        self._download = QLineSeries()
        self._download.setName("Download")
        self._upload = QLineSeries()
        self._upload.setName("Upload")
        self._chart.addSeries(self._download)
        self._chart.addSeries(self._upload)

        self._axis_x = QDateTimeAxis()
        self._axis_x.setTickCount(6)
        self._axis_x.setFormat("dd.MM HH:mm")
        self._axis_x.setLineVisible(False)

        self._axis_y = QValueAxis()
        self._axis_y.setTickCount(5)
        self._axis_y.setLabelFormat("%.0f")
        self._axis_y.setLineVisible(False)
        self._axis_y.setRange(0, 100)

        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)
        for series in (self._download, self._upload):
            series.attachAxis(self._axis_x)
            series.attachAxis(self._axis_y)

        self._view = _ZoomChartView(self._chart, self)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setFrameShape(QFrame.Shape.NoFrame)
        self._view.setMinimumHeight(260)
        self._view.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self._view, 1)

    # ------------------------------------------------------------------ язык
    def retranslate(self) -> None:
        """Обновляет подписи графика на текущем языке интерфейса."""
        self._title_label.setText(tr("chart.title"))
        self._period_label.setText(tr("chart.period"))
        self._from_label.setText(tr("chart.from"))
        self._to_label.setText(tr("chart.to"))
        for index, (key, _delta) in enumerate(self.RANGES):
            self.range_combo.setItemText(index, tr(key))
        self.range_combo.setItemText(self.range_combo.count() - 1, tr("range.custom"))
        self.zoom_reset_button.setText(tr("chart.reset_zoom"))
        self.zoom_reset_button.setToolTip(tr("chart.reset_zoom_tooltip"))
        self._view.setToolTip(tr("chart.controls"))
        self._chart.setTitle("" if self._has_data else tr("chart.no_data"))

    # ------------------------------------------------------------------ тема
    def apply_theme(self, theme: str) -> None:
        colors = CHART_THEMES.get(theme, CHART_THEMES["dark"])
        self._chart.setTheme(colors["chart_theme"])  # type: ignore[arg-type]
        self._chart.setBackgroundVisible(False)
        self._chart.setPlotAreaBackgroundVisible(False)
        self._chart.setTitleBrush(QBrush(colors["title"]))  # type: ignore[arg-type]
        self._chart.legend().hide()

        self._download.setPen(QPen(colors["download"], 2))  # type: ignore[arg-type]
        self._upload.setPen(QPen(colors["upload"], 2))  # type: ignore[arg-type]

        for axis, color in ((self._axis_x, "label"), (self._axis_y, "label")):
            axis.setLabelsColor(colors[color])  # type: ignore[arg-type]
            axis.setGridLineColor(colors["grid"])  # type: ignore[arg-type]
            axis.setLineVisible(False)

    # ------------------------------------------------------------------ диапазон
    def selected_interval(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """Возвращает (начало, конец) выбранного периода в локальном времени."""
        data = self.range_combo.currentData()
        if data == "custom":
            start_date = self.from_edit.date().toPython()
            end_date = self.to_edit.date().toPython()
            start = datetime.combine(start_date, dt_time.min).astimezone()
            end = datetime.combine(end_date, dt_time.max).astimezone()
            return start, end
        if data is None:
            return None, None
        return datetime.now(timezone.utc) - data, None  # type: ignore[operator]

    def range_index(self) -> int:
        return self.range_combo.currentIndex()

    def set_range_index(self, index: int) -> None:
        if 0 <= index < self.range_combo.count():
            self.range_combo.setCurrentIndex(index)

    def custom_dates_iso(self) -> tuple[str, str]:
        return (
            self.from_edit.date().toString(Qt.DateFormat.ISODate),
            self.to_edit.date().toString(Qt.DateFormat.ISODate),
        )

    def set_custom_dates_iso(self, start: str, end: str) -> None:
        start_date = QDate.fromString(start, Qt.DateFormat.ISODate)
        end_date = QDate.fromString(end, Qt.DateFormat.ISODate)
        if not start_date.isValid() or not end_date.isValid():
            return
        self._normalizing = True
        self.from_edit.setDate(start_date)
        self.to_edit.setDate(end_date)
        self._normalizing = False

    def _on_range_changed(self, _index: int) -> None:
        custom = self.range_combo.currentData() == "custom"
        self._custom_widget.setVisible(custom)
        if custom:
            self._normalize_dates(self.from_edit)
        self._auto_y = True
        self._set_zoomed(False)
        self.range_changed.emit()

    def _on_dates_changed(self) -> None:
        if self._normalizing or self.range_combo.currentData() != "custom":
            return
        self._normalize_dates(self.sender())
        self._auto_y = True
        self._set_zoomed(False)
        self.range_changed.emit()

    def _normalize_dates(self, changed_widget: object) -> None:
        if self.from_edit.date() <= self.to_edit.date():
            return
        self._normalizing = True
        if changed_widget is self.to_edit:
            self.from_edit.setDate(self.to_edit.date())
        else:
            self.to_edit.setDate(self.from_edit.date())
        self._normalizing = False

    # ------------------------------------------------------------------ масштаб
    def is_zoomed(self) -> bool:
        return self._zoomed

    def _set_zoomed(self, value: bool) -> None:
        self._zoomed = value
        button = getattr(self, "zoom_reset_button", None)
        if button is not None:
            button.setVisible(value)

    def reset_zoom(self) -> None:
        """Возвращает графику полный диапазон выбранного периода."""
        if self._full_x is None:
            return
        self._auto_y = True
        self._set_zoomed(False)
        self._apply_axis_ranges(
            self._full_x[0], self._full_x[1], self._full_y[0], self._full_y[1]
        )

    def zoom_at(self, position: QPointF, factor: float) -> None:
        """Масштабирует время вокруг курсора (factor < 1 — ближе)."""
        plot = self._plot_rect_in_view()
        if plot.isEmpty() or self._full_x is None:
            return
        rx = _ratio(position.x(), plot.left(), plot.width())
        x0, x1 = self._x_range()
        y0, y1 = self._y_range()
        anchor = x0 + rx * (x1 - x0)
        new_span = (x1 - x0) * factor
        self._set_ranges(
            anchor - rx * new_span,
            anchor + (1.0 - rx) * new_span,
            y0,
            y1,
            autofit_y=self._auto_y,
        )

    def zoom_to_rect(self, area: QRectF) -> None:
        """Приближает область, выделенную мышью (координаты вьюпорта)."""
        plot = self._plot_rect_in_view()
        if plot.isEmpty() or self._full_x is None:
            return
        target = plot.intersected(area)
        if target.width() < 8 or target.height() < 8:
            return
        x0, x1 = self._x_range()
        y0, y1 = self._y_range()
        left = _ratio(target.left(), plot.left(), plot.width())
        right = _ratio(target.right(), plot.left(), plot.width())
        bottom = 1.0 - _ratio(target.bottom(), plot.top(), plot.height())
        top = 1.0 - _ratio(target.top(), plot.top(), plot.height())
        self._auto_y = False
        self._set_ranges(
            x0 + left * (x1 - x0),
            x0 + right * (x1 - x0),
            y0 + bottom * (y1 - y0),
            y0 + top * (y1 - y0),
        )

    def pan_by(self, dx: float, dy: float) -> None:
        """Сдвигает видимую область по времени на dx пикселей."""
        if not self._zoomed or self._full_x is None:
            return
        plot = self._plot_rect_in_view()
        if plot.isEmpty():
            return
        x0, x1 = self._x_range()
        y0, y1 = self._y_range()
        shift_x = -dx * (x1 - x0) / plot.width()
        self._set_ranges(
            x0 + shift_x, x1 + shift_x, y0, y1, autofit_y=self._auto_y
        )

    def _set_ranges(
        self, x0: float, x1: float, y0: float, y1: float, autofit_y: bool = False
    ) -> None:
        """Применяет диапазоны с ограничением по полному диапазону данных."""
        if self._full_x is None:
            return
        fx0, fx1 = self._full_x
        fy0, fy1 = self._full_y
        full_x = max(fx1 - fx0, 1000.0)
        full_y = max(fy1 - fy0, 0.1)

        x_span = min(max(x1 - x0, self._min_x_span()), full_x)
        x0 = min(max(x0, fx0), fx1 - x_span)

        if autofit_y:
            fit = self._fit_y_for_span(x0, x0 + x_span)
            if fit is not None:
                y0, y1 = fit

        y_span = min(max(y1 - y0, self._min_y_span()), full_y)
        y0 = min(max(y0, fy0), fy1 - y_span)

        self._apply_axis_ranges(x0, x0 + x_span, y0, y0 + y_span)
        zoomed = not (x_span >= full_x * 0.999 and y_span >= full_y * 0.999)
        if not zoomed:
            self._auto_y = True
        self._set_zoomed(zoomed)

    def _fit_y_for_span(self, x0: float, x1: float) -> Optional[tuple[float, float]]:
        """Подбирает ось Y по данным, попавшим в видимый интервал времени."""
        values: list[float] = []
        for series, enabled in (
            (self._download, self._show_download),
            (self._upload, self._show_upload),
        ):
            if not enabled:
                continue
            for index in range(series.count()):
                point = series.at(index)
                if x0 <= point.x() <= x1:
                    values.append(point.y())
        if not values:
            return None
        return 0.0, _nice_upper_bound(max(values))

    def _min_x_span(self) -> float:
        if self._full_x is None:
            return 60_000.0
        return max(30_000.0, (self._full_x[1] - self._full_x[0]) / 1000)

    def _min_y_span(self) -> float:
        return max((self._full_y[1] - self._full_y[0]) / 200, 0.1)

    def _x_range(self) -> tuple[float, float]:
        return (
            float(self._axis_x.min().toMSecsSinceEpoch()),
            float(self._axis_x.max().toMSecsSinceEpoch()),
        )

    def _y_range(self) -> tuple[float, float]:
        return float(self._axis_y.min()), float(self._axis_y.max())

    def _plot_rect_in_view(self) -> QRectF:
        plot = self._chart.plotArea()
        if plot.isEmpty():
            return QRectF()
        top_left = self._view.mapFromScene(self._chart.mapToScene(plot.topLeft()))
        bottom_right = self._view.mapFromScene(
            self._chart.mapToScene(plot.bottomRight())
        )
        return QRectF(QPointF(top_left), QPointF(bottom_right)).normalized()

    def _apply_axis_ranges(
        self, x0: float, x1: float, y0: float, y1: float
    ) -> None:
        self._axis_x.setRange(
            QDateTime.fromMSecsSinceEpoch(int(x0)),
            QDateTime.fromMSecsSinceEpoch(int(x1)),
        )
        span_days = (x1 - x0) / 86_400_000
        if span_days <= 0.25:
            self._axis_x.setFormat("HH:mm")
        elif span_days <= 3:
            self._axis_x.setFormat("dd.MM HH:mm")
        else:
            self._axis_x.setFormat("dd.MM")
        self._axis_x.setTickCount(6 if span_days <= 2 else 8)

        self._axis_y.setRange(y0, y1)
        y_span = y1 - y0
        if y_span < 2:
            self._axis_y.setLabelFormat("%.2f")
        elif y_span < 10:
            self._axis_y.setLabelFormat("%.1f")
        else:
            self._axis_y.setLabelFormat("%.0f")

    # ------------------------------------------------------------------ данные
    def set_series_visible(self, download: bool, upload: bool) -> None:
        """Показывает только выбранные линии (Download/Upload)."""
        self._show_download = download
        self._show_upload = upload
        self._apply_series_visibility()

    def _apply_series_visibility(self) -> None:
        has_data = self._download.count() > 0 or self._upload.count() > 0
        for series, enabled in (
            (self._download, self._show_download),
            (self._upload, self._show_upload),
        ):
            visible = enabled and has_data
            series.setVisible(visible)
            for marker in self._chart.legend().markers(series):
                marker.setVisible(visible)

    def set_measurements(self, measurements: Sequence[Measurement]) -> None:
        self._download.clear()
        self._upload.clear()

        x_values: list[float] = []
        max_y = 0.0
        for measurement in measurements:
            if not measurement.succeeded:
                continue
            x = measurement.measured_at.timestamp() * 1000.0
            x_values.append(x)
            if measurement.download_mbps is not None:
                self._download.append(x, measurement.download_mbps)
                max_y = max(max_y, measurement.download_mbps)
            if measurement.upload_mbps is not None:
                self._upload.append(x, measurement.upload_mbps)
                max_y = max(max_y, measurement.upload_mbps)

        if not x_values:
            self._apply_series_visibility()
            self._has_data = False
            self._chart.setTitle(tr("chart.no_data"))
            self._full_x = None
            self._full_y = (0.0, 100.0)
            self._auto_y = True
            self._set_zoomed(False)
            now = QDateTime.currentDateTime()
            self._axis_x.setRange(now.addSecs(-3600), now)
            self._axis_x.setFormat("dd.MM HH:mm")
            self._axis_x.setTickCount(6)
            self._axis_y.setRange(0, 100)
            self._axis_y.setLabelFormat("%.0f")
            return

        self._apply_series_visibility()
        self._has_data = True
        self._chart.setTitle("")

        # Точки рисуем только на небольших выборках — иначе график тормозит.
        show_points = len(x_values) <= 120
        self._download.setPointsVisible(show_points)
        self._upload.setPointsVisible(show_points)

        now_ms = QDateTime.currentDateTime().toMSecsSinceEpoch()
        x_min = min(x_values)
        x_max = max(max(x_values), now_ms)
        if x_max - x_min < 60_000:
            x_min = x_max - 60_000

        top = _nice_upper_bound(max_y)
        self._full_x = (float(x_min), float(x_max))
        self._full_y = (0.0, top)

        if self._zoomed:
            # Данные обновились — сохраняем текущий масштаб в новых границах.
            x0, x1 = self._x_range()
            y0, y1 = self._y_range()
            self._set_ranges(x0, x1, y0, y1)
        else:
            self._apply_axis_ranges(x_min, x_max, 0.0, top)
