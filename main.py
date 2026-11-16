"""iNetLog — GUI-монитор скорости интернета (PySide6 + SQLite + QtCharts).

Раз в N минут (по умолчанию 5) выполняет замер Download/Upload/Ping,
сохраняет результат в SQLite и показывает график истории.
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from string import Template
from typing import Optional, Sequence

try:
    import winreg
except ImportError:  # pragma: no cover - приложение ориентировано на Windows
    winreg = None  # type: ignore[assignment]

from PySide6.QtCore import QSettings, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QBrush,
    QColor,
    QDesktopServices,
    QIcon,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from charts import INetChart
from database import INetDatabase, Measurement
from flags import flag_icon
from i18n import DEFAULT_LANGUAGE, language, language_name, set_language, tr
from inettester import INetTestThread
from ui_icons import theme_icon

APP_NAME = "iNetLog"
APP_VERSION = "2.7"
GITHUB_URL = "https://github.com/btrf/iNetLog"

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_STARTUP_VALUE = APP_NAME
_STARTUP_FLAG = "--minimized"


def resource_path(relative: str) -> Path:
    """Путь к ресурсу внутри onefile-сборки или рядом с исходниками."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative

_THEME_COLORS: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0b1220",
        "panel": "#141b24",
        "border": "#223044",
        "text": "#e2e8f0",
        "text_strong": "#f8fafc",
        "muted": "#94a3b8",
        "btn": "#1c2635",
        "btn_border": "#2c3b52",
        "btn_hover": "#243146",
        "btn_pressed": "#16202e",
        "accent": "#0ea5e9",
        "accent_hover": "#38bdf8",
        "accent_disabled": "#1e3a4d",
        "accent_text": "#04121f",
        "disabled": "#64748b",
        "header_bg": "#182130",
        "alt_row": "#111823",
        "grid": "#1c2635",
        "selection_bg": "#1e3a5f",
        "selection_text": "#e2e8f0",
        "error": "#f87171",
        "highlight": "#38bdf8",
    },
    "light": {
        "bg": "#eef2f8",
        "panel": "#ffffff",
        "border": "#d7deea",
        "text": "#1e293b",
        "text_strong": "#0b1220",
        "muted": "#5b6b82",
        "btn": "#f3f6fb",
        "btn_border": "#cfd8e6",
        "btn_hover": "#e6edf7",
        "btn_pressed": "#dbe5f2",
        "accent": "#0284c7",
        "accent_hover": "#0ea5e9",
        "accent_disabled": "#bae6fd",
        "accent_text": "#ffffff",
        "disabled": "#9aa8ba",
        "header_bg": "#f1f5fa",
        "alt_row": "#f8fafc",
        "grid": "#e2e8f0",
        "selection_bg": "#dbeafe",
        "selection_text": "#0b1220",
        "error": "#dc2626",
        "highlight": "#0284c7",
    },
}

_CARD_COLORS: dict[str, dict[str, str]] = {
    "dark": {
        "download": "#38bdf8",
        "upload": "#f59e0b",
        "ping": "#a78bfa",
        "tariff": "#ef4444",
    },
    "light": {
        "download": "#0284c7",
        "upload": "#d97706",
        "ping": "#7c3aed",
        "tariff": "#dc2626",
    },
}

_STYLE_TEMPLATE = Template(
    """
QMainWindow, QWidget#central { background: $bg; }
QWidget { color: $text; font-size: 13px; }
QMessageBox { background: $panel; }
QMessageBox QLabel { color: $text; }
QMessageBox QPushButton { min-width: 80px; }
QLabel#appTitle { font-size: 22px; font-weight: 600; color: $text_strong; }
QLabel#appSubtitle { color: $muted; }
QLabel#sectionTitle { font-size: 14px; font-weight: 600; color: $text_strong; }
QLabel#muted { color: $muted; }
QLabel#statusLabel { color: $muted; }
QFrame#card { background: $panel; border: 1px solid $border; border-radius: 10px; }
QLabel#cardTitle { color: $muted; font-size: 11px; font-weight: 600; }
QLabel#cardValue { font-size: 24px; font-weight: 600; }
QLabel#cardSubtitle { color: $muted; font-size: 11px; }
QPushButton { background: $btn; border: 1px solid $btn_border; border-radius: 6px; padding: 6px 14px; color: $text; }
QPushButton:hover { background: $btn_hover; }
QPushButton:pressed { background: $btn_pressed; }
QPushButton:disabled { color: $disabled; border-color: $border; }
QPushButton#primary { background: $accent; border-color: $accent; color: $accent_text; font-weight: 600; }
QPushButton#primary:hover { background: $accent_hover; }
QPushButton#primary:disabled { background: $accent_disabled; border-color: $accent_disabled; color: $disabled; }
QPushButton#langButton { padding: 3px 7px; font-size: 12px; font-weight: 700; }
QPushButton#langButton:hover { border-color: $accent; }
QPushButton#themeButton { padding: 3px 6px; }
QPushButton#themeButton:hover { border-color: $accent; }
QComboBox, QDateEdit, QDoubleSpinBox { background: $btn; border: 1px solid $btn_border; border-radius: 6px; padding: 5px 10px; min-width: 90px; color: $text; }
QComboBox:hover, QDateEdit:hover, QDoubleSpinBox:hover { border-color: $accent; }
QComboBox QAbstractItemView { background: $panel; border: 1px solid $border; selection-background-color: $accent; selection-color: $accent_text; outline: none; }
QComboBox::drop-down, QDateEdit::drop-down { border: none; width: 18px; }
QCalendarWidget QWidget { background: $panel; color: $text; }
QCalendarWidget QAbstractItemView { background: $panel; color: $text; selection-background-color: $accent; selection-color: $accent_text; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: $header_bg; }
QTableWidget { background: $panel; alternate-background-color: $alt_row; border: 1px solid $border; border-radius: 8px; gridline-color: $grid; }
QHeaderView::section { background: $header_bg; color: $muted; border: none; padding: 6px; font-weight: 600; }
QTableWidget::item { padding: 4px; }
QTableWidget::item:selected { background: $selection_bg; color: $selection_text; }
QProgressBar { background: $btn; border: none; border-radius: 3px; }
QProgressBar::chunk { background: $accent; border-radius: 3px; }
QStatusBar { color: $muted; background: $bg; }
QMenuBar { background: $bg; color: $text; }
QMenuBar::item:selected { background: $btn; }
QMenu { background: $panel; border: 1px solid $border; color: $text; }
QMenu::item { padding: 6px 24px; }
QMenu::item:selected { background: $btn_hover; }
QToolTip { background: $panel; color: $text; border: 1px solid $border; }
QScrollBar:vertical { background: $bg; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: $btn_border; border-radius: 5px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
)

STYLES = {name: _STYLE_TEMPLATE.substitute(**colors) for name, colors in _THEME_COLORS.items()}

def export_headers() -> tuple[str, ...]:
    """Заголовки экспорта на текущем языке интерфейса."""
    return (
        tr("export.time"),
        tr("export.download"),
        tr("export.upload"),
        tr("export.ping"),
        tr("export.server"),
        tr("export.isp"),
        tr("export.backend"),
        tr("export.error"),
    )


def _export_values(measurement: Measurement) -> list[object]:
    return [
        measurement.local_time.strftime("%Y-%m-%d %H:%M:%S"),
        measurement.download_mbps,
        measurement.upload_mbps,
        measurement.ping_ms,
        measurement.server,
        measurement.isp,
        measurement.backend,
        measurement.error or "",
    ]


def write_csv(path: str, measurements: Sequence[Measurement]) -> int:
    """Сохраняет замеры в CSV (UTF-8 с BOM, разделитель «;»). Возвращает число строк."""
    headers = export_headers()
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(headers)
        for measurement in measurements:
            writer.writerow(_export_values(measurement))
    return len(measurements)


def write_excel(path: str, measurements: Sequence[Measurement]) -> int:
    """Сохраняет замеры в .xlsx с шапкой, фильтром и числовыми форматами."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = tr("export.sheet")
    sheet.append(export_headers())

    for measurement in measurements:
        sheet.append(
            [
                measurement.local_time.replace(tzinfo=None),
                measurement.download_mbps,
                measurement.upload_mbps,
                measurement.ping_ms,
                measurement.server or "",
                measurement.isp or "",
                measurement.backend or "",
                measurement.error or "",
            ]
        )

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", start_color="0EA5E9", end_color="0EA5E9")
    for cell in sheet[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    error_font = Font(color="DC2626")
    for row_index, measurement in enumerate(measurements, start=2):
        sheet.cell(row=row_index, column=1).number_format = "dd.mm.yyyy hh:mm:ss"
        for column in (2, 3):
            sheet.cell(row=row_index, column=column).number_format = "0.00"
        sheet.cell(row=row_index, column=4).number_format = "0.0"
        if measurement.error:
            for cell in sheet[row_index]:
                cell.font = error_font

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:H{max(1, len(measurements) + 1)}"
    for index, width in enumerate((20, 18, 18, 10, 30, 24, 16, 60), start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    workbook.save(path)
    return len(measurements)


class StatCard(QFrame):
    """Карточка с текущим значением и статистикой."""

    def __init__(self, title: str, unit: str, color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._unit = unit

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        title_label = QLabel(title.upper())
        title_label.setObjectName("cardTitle")

        self.value_label = QLabel("—")
        self.value_label.setObjectName("cardValue")
        self.set_color(color)

        self.subtitle_label = QLabel(tr("card.no_data"))
        self.subtitle_label.setObjectName("cardSubtitle")
        self.subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)

    def set_color(self, color: str) -> None:
        self.value_label.setStyleSheet(f"color: {color};")

    def set_unit(self, unit: str) -> None:
        """Меняет единицу измерения (при смене языка интерфейса)."""
        self._unit = unit

    def set_metric(self, value: Optional[float], subtitle: str) -> None:
        self.value_label.setText("—" if value is None else f"{value:.2f} {self._unit}")
        self.subtitle_label.setText(subtitle)


class MainWindow(QMainWindow):
    INTERVALS = (1, 5, 10, 15, 30, 60)

    def __init__(self, db_path: Path) -> None:
        super().__init__()
        self.resize(1100, 820)

        self.db = INetDatabase(db_path)
        self._settings = QSettings(str(db_path.with_name("inetlog.ini")), QSettings.Format.IniFormat)
        set_language(self._settings.value("language", DEFAULT_LANGUAGE))
        self.setWindowTitle(f"{APP_NAME} — {tr('app.title_suffix')}")
        self._thread: Optional[INetTestThread] = None
        self._measuring = False
        self._paused = False
        self._next_run: Optional[datetime] = None
        self._alert: Optional[str] = None
        self._theme = "dark"
        self._last_started_at: Optional[datetime] = None

        self._build_ui()
        self._build_menu()

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._update_status)
        self._tick_timer.start()

        self._test_timer = QTimer(self)
        self._test_timer.setSingleShot(True)
        self._test_timer.timeout.connect(self.start_measurement)

        self._restore_settings()
        self.refresh()
        self._schedule_next()
        self._update_controls()
        self._update_status()

        # Первый замер — почти сразу после запуска, чтобы график не был пустым.
        self._first_timer = QTimer(self)
        self._first_timer.setSingleShot(True)
        self._first_timer.timeout.connect(self.start_measurement)
        self._first_timer.start(2500)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 10)
        root.setSpacing(14)

        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        self._subtitle_label = QLabel(tr("app.subtitle"))
        self._subtitle_label.setObjectName("appSubtitle")

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(2)
        titles.addWidget(title)
        titles.addWidget(self._subtitle_label)

        self.theme_button = QPushButton()
        self.theme_button.setObjectName("themeButton")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.theme_button.setFixedSize(36, 30)
        self.theme_button.setIconSize(QSize(18, 18))
        self.theme_button.clicked.connect(self._toggle_theme)
        self._update_theme_button()

        self.language_button = QPushButton()
        self.language_button.setObjectName("langButton")
        self.language_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.language_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.language_button.setFixedHeight(30)
        self.language_button.setIconSize(QSize(22, 15))
        self.language_button.clicked.connect(self._toggle_language)
        self._update_language_button()

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        header.addLayout(titles, 1)
        header.addWidget(
            self.theme_button,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )
        header.addWidget(
            self.language_button,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )
        root.addLayout(header)

        root.addLayout(self._build_controls())

        cards = QHBoxLayout()
        cards.setSpacing(12)
        colors = _CARD_COLORS["dark"]
        self.download_card = StatCard("Download", tr("unit.mbps"), colors["download"])
        self.upload_card = StatCard("Upload", tr("unit.mbps"), colors["upload"])
        self.ping_card = StatCard("Ping", tr("unit.ms"), colors["ping"])
        for card in (self.download_card, self.upload_card, self.ping_card):
            cards.addWidget(card, 1)
        root.addLayout(cards)

        self.chart = INetChart()
        self.chart.range_changed.connect(self.refresh)
        root.addWidget(self.chart, 1)

        self.download_toggle = QPushButton("Download")
        self.download_toggle.setCheckable(True)
        self.download_toggle.setChecked(True)
        self.download_toggle.setToolTip(tr("series.download_tooltip"))
        self.download_toggle.toggled.connect(self._on_series_toggled)

        self.upload_toggle = QPushButton("Upload")
        self.upload_toggle.setCheckable(True)
        self.upload_toggle.setChecked(True)
        self.upload_toggle.setToolTip(tr("series.upload_tooltip"))
        self.upload_toggle.toggled.connect(self._on_series_toggled)

        self.tariff_toggle = QPushButton(tr("series.tariff"))
        self.tariff_toggle.setCheckable(True)
        self.tariff_toggle.setChecked(True)
        self.tariff_toggle.setToolTip(tr("series.tariff_tooltip"))
        self.tariff_toggle.toggled.connect(self._on_tariff_changed)

        self.tariff_spin = QDoubleSpinBox()
        self.tariff_spin.setDecimals(1)
        self.tariff_spin.setRange(0.1, 10_000.0)
        self.tariff_spin.setSingleStep(1.0)
        self.tariff_spin.setValue(5.0)
        self.tariff_spin.setSuffix(f" {tr('unit.mbps')}")
        self.tariff_spin.setToolTip(tr("series.tariff_value_tooltip"))
        self.tariff_spin.setKeyboardTracking(False)
        self.tariff_spin.valueChanged.connect(self._on_tariff_changed)

        self.series_controls = QWidget()
        series_row = QHBoxLayout(self.series_controls)
        series_row.setContentsMargins(0, 0, 0, 0)
        series_row.setSpacing(8)
        series_row.addStretch(1)
        series_row.addWidget(self.download_toggle)
        series_row.addWidget(self.upload_toggle)
        series_row.addSpacing(12)
        series_row.addWidget(self.tariff_toggle)
        series_row.addWidget(self.tariff_spin)
        series_row.addStretch(1)
        root.addWidget(self.series_controls)

        self._table_container = self._build_table()
        root.addWidget(self._table_container)
        self._root_layout = root

        self.statusBar().showMessage(tr("status.data", path=self.db.path))

    def _build_controls(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self._interval_label = QLabel(tr("interval.label"))
        self._interval_label.setObjectName("muted")
        self.interval_combo = QComboBox()
        for minutes in self.INTERVALS:
            self.interval_combo.addItem(self._interval_text(minutes), minutes)
        self.interval_combo.currentIndexChanged.connect(self._on_interval_changed)

        self.measure_button = QPushButton(tr("button.measure"))
        self.measure_button.setObjectName("primary")
        self.measure_button.clicked.connect(self.start_measurement)

        self.pause_button = QPushButton(tr("button.pause"))
        self.pause_button.clicked.connect(self.toggle_pause)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedSize(110, 6)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)

        self.status_label = QLabel(tr("status.waiting"))
        self.status_label.setObjectName("statusLabel")

        row.addWidget(self._interval_label)
        row.addWidget(self.interval_combo)
        row.addWidget(self.measure_button)
        row.addWidget(self.pause_button)
        row.addSpacing(12)
        row.addWidget(self.progress)
        row.addWidget(self.status_label, 1)
        return row

    def _build_table(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._table_title = QLabel(tr("table.title"))
        self._table_title.setObjectName("sectionTitle")

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(self._table_headers())
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            item = self.table.horizontalHeaderItem(column)
            if item is not None:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.table.setMinimumHeight(170)
        self.table.setMaximumHeight(230)

        layout.addWidget(self._table_title)
        layout.addWidget(self.table)
        return container

    def _build_menu(self) -> None:
        self._file_menu = self.menuBar().addMenu(tr("menu.file"))

        self._export_csv_action = QAction(tr("action.export_csv"), self)
        self._export_csv_action.setShortcut(QKeySequence("Ctrl+E"))
        self._export_csv_action.triggered.connect(self.export_csv)
        self._file_menu.addAction(self._export_csv_action)

        self._export_excel_action = QAction(tr("action.export_excel"), self)
        self._export_excel_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self._export_excel_action.triggered.connect(self.export_excel)
        self._file_menu.addAction(self._export_excel_action)

        self._file_menu.addSeparator()
        self._quit_action = QAction(tr("action.quit"), self)
        self._quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self._quit_action.triggered.connect(self.close)
        self._file_menu.addAction(self._quit_action)

        self._data_menu = self.menuBar().addMenu(tr("menu.data"))

        self._measure_action = QAction(tr("action.measure"), self)
        self._measure_action.setShortcut(QKeySequence("Ctrl+R"))
        self._measure_action.triggered.connect(self.start_measurement)
        self._data_menu.addAction(self._measure_action)

        self._data_menu.addSeparator()

        self._open_folder_action = QAction(tr("action.open_folder"), self)
        self._open_folder_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.db.path.parent)))
        )
        self._data_menu.addAction(self._open_folder_action)

        self._clear_history_action = QAction(tr("action.clear_history"), self)
        self._clear_history_action.triggered.connect(self.clear_history)
        self._data_menu.addAction(self._clear_history_action)

        self._data_menu.addSeparator()

        self._startup_action = QAction(tr("action.autostart"), self)
        self._startup_action.setCheckable(True)
        self._startup_action.setToolTip(
            tr("action.autostart_tooltip", run_key=_RUN_KEY, value=_STARTUP_VALUE)
        )
        if winreg is None:
            self._startup_action.setEnabled(False)
            self._startup_action.setToolTip(tr("action.autostart_windows_only"))
        else:
            self._startup_action.setChecked(is_startup_enabled())
        self._startup_action.toggled.connect(self._on_startup_toggled)
        self._data_menu.addAction(self._startup_action)

        self._view_menu = self.menuBar().addMenu(tr("menu.view"))
        self._show_chart_action = QAction(tr("action.show_chart"), self)
        self._show_chart_action.setCheckable(True)
        self._show_chart_action.setChecked(True)
        self._show_chart_action.setShortcut(QKeySequence("Ctrl+G"))
        self._show_chart_action.setToolTip(tr("action.show_chart_tooltip"))
        self._show_chart_action.toggled.connect(self._on_show_chart_toggled)
        self._view_menu.addAction(self._show_chart_action)

        self._reset_zoom_action = QAction(tr("action.reset_zoom"), self)
        self._reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        self._reset_zoom_action.setToolTip(tr("action.reset_zoom_tooltip"))
        self._reset_zoom_action.triggered.connect(self._reset_chart_zoom)
        self._view_menu.addAction(self._reset_zoom_action)

        self._view_menu.addSeparator()

        self._theme_menu = self._view_menu.addMenu(tr("menu.theme"))
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        self._theme_actions: dict[str, QAction] = {}
        for theme in ("dark", "light"):
            action = QAction(tr(f"theme.{theme}"), self)
            action.setCheckable(True)
            action.setChecked(theme == self._theme)
            action.triggered.connect(
                lambda _checked=False, value=theme: self._on_theme_selected(value)
            )
            self._theme_group.addAction(action)
            self._theme_menu.addAction(action)
            self._theme_actions[theme] = action

        self._language_menu = self._view_menu.addMenu(tr("menu.language"))
        self._language_group = QActionGroup(self)
        self._language_group.setExclusive(True)
        self._language_actions: dict[str, QAction] = {}
        for code in ("en", "ru"):
            action = QAction(flag_icon(code), language_name(code), self)
            action.setCheckable(True)
            action.setChecked(code == language())
            action.triggered.connect(
                lambda _checked=False, value=code: self._on_language_selected(value)
            )
            self._language_group.addAction(action)
            self._language_menu.addAction(action)
            self._language_actions[code] = action

        self._help_menu = self.menuBar().addMenu(tr("menu.help"))
        self._about_action = QAction(tr("action.about"), self)
        self._about_action.triggered.connect(self.show_about)
        self._help_menu.addAction(self._about_action)

    # ------------------------------------------------------------------ язык
    def retranslate(self) -> None:
        """Обновляет все подписи интерфейса на текущем языке."""
        self.setWindowTitle(f"{APP_NAME} — {tr('app.title_suffix')}")
        self._subtitle_label.setText(tr("app.subtitle"))
        self._interval_label.setText(tr("interval.label"))
        for index, minutes in enumerate(self.INTERVALS):
            self.interval_combo.setItemText(index, self._interval_text(minutes))
        self.measure_button.setText(tr("button.measure"))
        self._update_controls()

        self.download_card.set_unit(tr("unit.mbps"))
        self.upload_card.set_unit(tr("unit.mbps"))
        self.ping_card.set_unit(tr("unit.ms"))
        self.download_toggle.setToolTip(tr("series.download_tooltip"))
        self.upload_toggle.setToolTip(tr("series.upload_tooltip"))
        self.tariff_toggle.setText(tr("series.tariff"))
        self.tariff_toggle.setToolTip(tr("series.tariff_tooltip"))
        self.tariff_spin.setSuffix(f" {tr('unit.mbps')}")
        self.tariff_spin.setToolTip(tr("series.tariff_value_tooltip"))

        self._table_title.setText(tr("table.title"))
        self.table.setHorizontalHeaderLabels(self._table_headers())

        self._file_menu.setTitle(tr("menu.file"))
        self._data_menu.setTitle(tr("menu.data"))
        self._view_menu.setTitle(tr("menu.view"))
        self._help_menu.setTitle(tr("menu.help"))
        self._theme_menu.setTitle(tr("menu.theme"))
        self._language_menu.setTitle(tr("menu.language"))

        self._export_csv_action.setText(tr("action.export_csv"))
        self._export_excel_action.setText(tr("action.export_excel"))
        self._quit_action.setText(tr("action.quit"))
        self._measure_action.setText(tr("action.measure"))
        self._open_folder_action.setText(tr("action.open_folder"))
        self._clear_history_action.setText(tr("action.clear_history"))
        self._startup_action.setText(tr("action.autostart"))
        self._startup_action.setToolTip(
            tr("action.autostart_windows_only")
            if winreg is None
            else tr("action.autostart_tooltip", run_key=_RUN_KEY, value=_STARTUP_VALUE)
        )
        self._show_chart_action.setText(tr("action.show_chart"))
        self._show_chart_action.setToolTip(tr("action.show_chart_tooltip"))
        self._reset_zoom_action.setText(tr("action.reset_zoom"))
        self._reset_zoom_action.setToolTip(tr("action.reset_zoom_tooltip"))
        self._about_action.setText(tr("action.about"))
        for theme, action in self._theme_actions.items():
            action.setText(tr(f"theme.{theme}"))

        self.chart.retranslate()
        self._sync_language_actions()
        self._update_language_button()
        self._update_theme_button()
        self.statusBar().showMessage(tr("status.data", path=self.db.path))
        self.refresh()
        self._update_status()

    def _on_language_selected(self, code: str) -> None:
        if code == language():
            self._sync_language_actions()
            return
        set_language(code)
        self._settings.setValue("language", language())
        self.retranslate()
        key = "status.language_ru" if language() == "ru" else "status.language_en"
        self.statusBar().showMessage(tr(key), 5000)

    def _toggle_language(self) -> None:
        self._on_language_selected("ru" if language() == "en" else "en")

    def _sync_language_actions(self) -> None:
        for code, action in getattr(self, "_language_actions", {}).items():
            action.blockSignals(True)
            action.setChecked(code == language())
            action.blockSignals(False)

    def _update_language_button(self) -> None:
        code = language()
        self.language_button.setText("RU" if code == "ru" else "EN")
        self.language_button.setIcon(flag_icon(code))
        self.language_button.setIconSize(QSize(22, 15))
        self.language_button.setToolTip(
            tr("lang.switch_to_ru") if code == "en" else tr("lang.switch_to_en")
        )

    # ------------------------------------------------------------------ кнопка темы
    def _toggle_theme(self) -> None:
        target = "light" if self._theme == "dark" else "dark"
        self._on_theme_selected(target)
        key = "status.theme_light" if self._theme == "light" else "status.theme_dark"
        self.statusBar().showMessage(tr(key), 4000)

    def _update_theme_button(self) -> None:
        if not hasattr(self, "theme_button"):
            return
        target = "light" if self._theme == "dark" else "dark"
        self.theme_button.setIcon(theme_icon(self._theme))
        self.theme_button.setIconSize(QSize(18, 18))
        self.theme_button.setToolTip(
            tr("theme.switch_to_light")
            if target == "light"
            else tr("theme.switch_to_dark")
        )

    # ------------------------------------------------------------------ автозапуск
    def _on_startup_toggled(self, checked: bool) -> None:
        action = self._startup_action
        action.blockSignals(True)
        try:
            set_startup_enabled(checked)
            if is_startup_enabled() != checked:
                raise OSError(tr("msg.autostart_registry"))
        except (OSError, RuntimeError) as exc:
            action.setChecked(not checked)
            action.blockSignals(False)
            verb = tr("verb.enable") if checked else tr("verb.disable")
            QMessageBox.warning(
                self,
                tr("msg.autostart_title"),
                tr("msg.autostart_failed", verb=verb, error=exc),
            )
            return
        action.blockSignals(False)

        if checked:
            self.statusBar().showMessage(tr("status.autostart_on"), 8000)
        else:
            self.statusBar().showMessage(tr("status.autostart_off"), 8000)

    # ------------------------------------------------------------------ графики
    def _on_show_chart_toggled(self, checked: bool) -> None:
        self._set_chart_visible(checked)
        self.statusBar().showMessage(
            tr("status.charts_shown") if checked else tr("status.charts_hidden"), 4000
        )

    def _reset_chart_zoom(self) -> None:
        self.chart.reset_zoom()
        self.statusBar().showMessage(tr("status.zoom_reset"), 4000)

    def _set_chart_visible(self, visible: bool) -> None:
        """Скрывает или показывает область графиков и растягивает таблицу."""
        self.chart.setVisible(visible)
        self.series_controls.setVisible(visible)
        if visible:
            self.table.setMaximumHeight(230)
            self._root_layout.setStretchFactor(self.chart, 1)
            self._root_layout.setStretchFactor(self._table_container, 0)
        else:
            self.table.setMaximumHeight(16_777_215)
            self._root_layout.setStretchFactor(self.chart, 0)
            self._root_layout.setStretchFactor(self._table_container, 1)

    def _on_series_toggled(self, _checked: bool) -> None:
        self.chart.set_series_visible(
            self.download_toggle.isChecked(),
            self.upload_toggle.isChecked(),
        )

    def _on_tariff_changed(self, _value: object) -> None:
        """Включает/выключает линию тарифа и обновляет её скорость."""
        visible = self.tariff_toggle.isChecked()
        mbps = self.tariff_spin.value()
        self.chart.set_tariff(mbps, visible)
        self._settings.setValue("tariff_visible", visible)
        self._settings.setValue("tariff_mbps", mbps)

    # ------------------------------------------------------------------ тема
    def _apply_theme(self, theme: str) -> None:
        self._theme = theme if theme in STYLES else "dark"
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(STYLES[self._theme])
        self.chart.apply_theme(self._theme)

        colors = _CARD_COLORS[self._theme]
        self.download_card.set_color(colors["download"])
        self.upload_card.set_color(colors["upload"])
        self.ping_card.set_color(colors["ping"])

        theme_colors = _THEME_COLORS[self._theme]
        for button, accent in (
            (self.download_toggle, colors["download"]),
            (self.upload_toggle, colors["upload"]),
            (self.tariff_toggle, colors["tariff"]),
        ):
            button.setStyleSheet(
                f"QPushButton {{ background: {theme_colors['btn']}; color: {theme_colors['text']}; "
                f"border: 1px solid {theme_colors['btn_border']}; border-radius: 6px; "
                f"padding: 5px 12px; }}"
                f"QPushButton:hover {{ background: {theme_colors['btn_hover']}; }}"
                f"QPushButton:checked {{ background: {accent}; border-color: {accent}; "
                f"color: #ffffff; font-weight: 600; }}"
            )

        for name, action in getattr(self, "_theme_actions", {}).items():
            action.blockSignals(True)
            action.setChecked(name == self._theme)
            action.blockSignals(False)
        self._update_theme_button()
        self._update_status()

    def _on_theme_selected(self, theme: str) -> None:
        if theme == self._theme:
            return
        self._apply_theme(theme)
        self._settings.setValue("theme", theme)
        self.refresh()

    # ------------------------------------------------------------------ настройки
    def _restore_settings(self) -> None:
        theme = str(self._settings.value("theme", "dark"))
        if theme not in STYLES:
            theme = "dark"
        self._apply_theme(theme)

        minutes = self._as_int(self._settings.value("interval_minutes", 5), 5)
        index = self.interval_combo.findData(minutes)
        if index >= 0:
            self.interval_combo.setCurrentIndex(index)

        range_from = self._settings.value("range_from")
        range_to = self._settings.value("range_to")
        if range_from and range_to:
            self.chart.set_custom_dates_iso(str(range_from), str(range_to))

        range_index = self._as_int(self._settings.value("range_index", 0), 0)
        self.chart.set_range_index(range_index)

        geometry = self._settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

        show_chart = self._settings.value("show_chart", True, type=bool)
        self._show_chart_action.blockSignals(True)
        self._show_chart_action.setChecked(show_chart)
        self._show_chart_action.blockSignals(False)
        self._set_chart_visible(show_chart)

        show_download = self._settings.value("show_download", True, type=bool)
        show_upload = self._settings.value("show_upload", True, type=bool)
        for button, value in (
            (self.download_toggle, show_download),
            (self.upload_toggle, show_upload),
        ):
            button.blockSignals(True)
            button.setChecked(value)
            button.blockSignals(False)
        self.chart.set_series_visible(show_download, show_upload)

        tariff_mbps = self._as_float(self._settings.value("tariff_mbps", 5.0), 5.0)
        tariff_visible = self._settings.value("tariff_visible", True, type=bool)
        self.tariff_spin.blockSignals(True)
        self.tariff_spin.setValue(tariff_mbps)
        self.tariff_spin.blockSignals(False)
        tariff_mbps = self.tariff_spin.value()
        self.tariff_toggle.blockSignals(True)
        self.tariff_toggle.setChecked(tariff_visible)
        self.tariff_toggle.blockSignals(False)
        self.chart.set_tariff(tariff_mbps, tariff_visible)

    def _save_settings(self) -> None:
        self._settings.setValue("interval_minutes", self._interval_minutes())
        self._settings.setValue("range_index", self.chart.range_index())
        self._settings.setValue("theme", self._theme)
        self._settings.setValue("language", language())
        self._settings.setValue("show_chart", self._show_chart_action.isChecked())
        self._settings.setValue("show_download", self.download_toggle.isChecked())
        self._settings.setValue("show_upload", self.upload_toggle.isChecked())
        self._settings.setValue("tariff_visible", self.tariff_toggle.isChecked())
        self._settings.setValue("tariff_mbps", self.tariff_spin.value())
        range_from, range_to = self.chart.custom_dates_iso()
        self._settings.setValue("range_from", range_from)
        self._settings.setValue("range_to", range_to)
        self._settings.setValue("geometry", self.saveGeometry())

    @staticmethod
    def _as_int(value: object, default: int) -> int:
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_float(value: object, default: float) -> float:
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    def _interval_minutes(self) -> int:
        minutes = self.interval_combo.currentData()
        return int(minutes) if minutes else 5

    @staticmethod
    def _interval_text(minutes: int) -> str:
        if minutes == 1:
            return tr("interval.every_minute")
        return tr("interval.every_n", minutes=minutes)

    @staticmethod
    def _table_headers() -> list[str]:
        return [
            tr("table.time"),
            tr("table.download"),
            tr("table.upload"),
            tr("table.ping"),
            tr("table.server"),
        ]

    def _on_interval_changed(self, _index: int) -> None:
        if not hasattr(self, "_test_timer"):
            return
        self._settings.setValue("interval_minutes", self._interval_minutes())
        if not self._paused and not self._measuring:
            self._schedule_next()
            self._update_status()

    # ------------------------------------------------------------------ измерения
    def start_measurement(self) -> None:
        if self._measuring:
            return
        if self._thread is not None and self._thread.isRunning():
            return

        # Защита от случайного «дребезга» кнопки/повторных сигналов.
        now = datetime.now()
        if self._last_started_at is not None and (now - self._last_started_at).total_seconds() < 3:
            return
        self._last_started_at = now

        self._test_timer.stop()
        self._first_timer.stop()
        self._next_run = None
        self._alert = None
        self._measuring = True
        self._update_controls()
        self._update_status()

        self._thread = INetTestThread(self)
        self._thread.result_ready.connect(self._handle_result)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def _handle_result(self, result: dict) -> None:
        measurement = self.db.add(result)
        if measurement.error:
            self._alert = measurement.error
        self.refresh()
        self._update_status()

    def _on_thread_finished(self) -> None:
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.deleteLater()

        self._measuring = False
        self._update_controls()
        if not self._paused:
            self._schedule_next()
        self._update_status()

    def toggle_pause(self) -> None:
        if self._measuring:
            return
        self._paused = not self._paused
        if self._paused:
            self._test_timer.stop()
            self._next_run = None
        else:
            self._schedule_next()
        self._update_controls()
        self._update_status()

    def _schedule_next(self) -> None:
        self._next_run = datetime.now() + timedelta(minutes=self._interval_minutes())
        self._test_timer.start(self._interval_minutes() * 60 * 1000)

    # ------------------------------------------------------------------ отрисовка
    def refresh(self) -> None:
        since, until = self.chart.selected_interval()
        rows = self.db.measurements(since, until)
        self.chart.set_measurements(rows)
        self._update_cards(rows)
        self._update_table(self.db.recent(30))

    def _update_cards(self, rows: Sequence[Measurement]) -> None:
        successful = [m for m in rows if m.succeeded]
        latest = self.db.last_successful()

        def values(attr: str) -> list[float]:
            return [float(getattr(m, attr)) for m in successful if getattr(m, attr) is not None]

        downloads = values("download_mbps")
        uploads = values("upload_mbps")
        pings = values("ping_ms")

        def subtitle(numbers: list[float]) -> str:
            if not numbers:
                return tr("card.period_no_data")
            average = sum(numbers) / len(numbers)
            return tr(
                "card.subtitle",
                avg=f"{average:.1f}",
                max=f"{max(numbers):.1f}",
                count=len(numbers),
            )

        self.download_card.set_metric(
            latest.download_mbps if latest else None, subtitle(downloads)
        )
        self.upload_card.set_metric(latest.upload_mbps if latest else None, subtitle(uploads))
        self.ping_card.set_metric(latest.ping_ms if latest else None, subtitle(pings))

    def _update_table(self, rows: Sequence[Measurement]) -> None:
        error_color = QBrush(QColor(_THEME_COLORS[self._theme]["error"]))
        self.table.setRowCount(len(rows))
        for row_index, measurement in enumerate(rows):
            download = (
                f"{measurement.download_mbps:.2f}"
                if measurement.download_mbps is not None
                else "—"
            )
            upload = (
                f"{measurement.upload_mbps:.2f}" if measurement.upload_mbps is not None else "—"
            )
            ping = f"{measurement.ping_ms:.1f}" if measurement.ping_ms is not None else "—"

            if measurement.error:
                note = measurement.error
            else:
                note = " · ".join(part for part in (measurement.server, measurement.isp) if part) or "—"

            cells = [
                measurement.local_time.strftime("%d.%m.%Y %H:%M:%S"),
                download,
                upload,
                ping,
                note,
            ]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column in (1, 2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if measurement.error:
                    item.setForeground(error_color)
                item.setToolTip(text)
                self.table.setItem(row_index, column, item)

    def _update_controls(self) -> None:
        self.measure_button.setEnabled(not self._measuring)
        self.pause_button.setEnabled(not self._measuring)
        self.pause_button.setText(tr("button.resume") if self._paused else tr("button.pause"))
        self.progress.setVisible(self._measuring)

    def _update_status(self) -> None:
        colors = _THEME_COLORS[self._theme]
        if self._measuring:
            self.status_label.setText(tr("status.measuring"))
            self.status_label.setStyleSheet(f"color: {colors['highlight']};")
            return

        parts: list[str] = []
        if self._alert:
            alert = tr("status.error", error=self._alert)
            if len(alert) > 140:
                alert = alert[:137] + "…"
            parts.append(alert)

        if self._paused:
            parts.append(tr("status.paused"))
        elif self._next_run is not None:
            remaining = max(0, int((self._next_run - datetime.now()).total_seconds()))
            parts.append(
                tr("status.next", mm=f"{remaining // 60:02d}", ss=f"{remaining % 60:02d}")
            )

        self.status_label.setText(" · ".join(parts) if parts else tr("status.waiting"))
        color = colors["error"] if self._alert else colors["muted"]
        self.status_label.setStyleSheet(f"color: {color};")

    # ------------------------------------------------------------------ действия меню
    def export_csv(self) -> None:
        default_path = Path.home() / "inetlog.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dialog.export_csv"), str(default_path), "CSV (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"

        rows = self.db.measurements()
        try:
            count = write_csv(path, rows)
        except OSError as exc:
            QMessageBox.critical(self, tr("dialog.export_error"), str(exc))
            return

        self.statusBar().showMessage(
            tr("status.exported", count=count, path=path), 8000
        )

    def export_excel(self) -> None:
        default_path = Path.home() / "inetlog.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dialog.export_excel"), str(default_path), "Excel (*.xlsx)"
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        rows = self.db.measurements()
        try:
            count = write_excel(path, rows)
        except ImportError:
            QMessageBox.critical(
                self,
                tr("dialog.export_error"),
                tr("msg.openpyxl_missing"),
            )
            return
        except OSError as exc:
            QMessageBox.critical(self, tr("dialog.export_error"), str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - ошибки openpyxl бывают разными
            QMessageBox.critical(
                self, tr("dialog.export_error"), str(exc) or exc.__class__.__name__
            )
            return

        self.statusBar().showMessage(
            tr("status.exported", count=count, path=path), 8000
        )

    def clear_history(self) -> None:
        answer = QMessageBox.question(
            self,
            tr("dialog.clear_title"),
            tr("dialog.clear_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.db.clear()
        self._alert = None
        self.refresh()
        self._update_status()
        self.statusBar().showMessage(tr("status.cleared"), 5000)

    def show_about(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(tr("about.title"))
        box.setIconPixmap(self.windowIcon().pixmap(64, 64))
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(
            tr(
                "about.body",
                name=APP_NAME,
                version=APP_VERSION,
                tagline=tr("about.tagline"),
                path=self.db.path,
                github=GITHUB_URL,
            )
        )
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.setDefaultButton(QMessageBox.StandardButton.Ok)
        label = box.findChild(QLabel, "qt_msgbox_label")
        if label is not None:
            label.setOpenExternalLinks(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        box.exec()

    # ------------------------------------------------------------------ закрытие
    def closeEvent(self, event) -> None:  # noqa: N802 - метод Qt
        self._save_settings()
        self._test_timer.stop()
        self._first_timer.stop()
        self._tick_timer.stop()

        thread = self._thread
        if thread is not None and thread.isRunning():
            thread.wait(3000)
            if thread.isRunning():
                thread.terminate()
                thread.wait(1000)

        self.db.close()
        super().closeEvent(event)


def startup_command() -> str:
    """Команда автозапуска: приложение стартует свёрнутым (флаг ``--minimized``)."""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" {_STARTUP_FLAG}'

    interpreter = Path(sys.executable).resolve()
    pythonw = interpreter.with_name("pythonw.exe")
    if pythonw.exists():
        interpreter = pythonw
    script = Path(__file__).resolve()
    return f'"{interpreter}" "{script}" {_STARTUP_FLAG}'


def start_minimized(argv: Optional[Sequence[str]] = None) -> bool:
    """Запущено ли приложение с флагом автозапуска (свёрнутое окно)."""
    args = sys.argv[1:] if argv is None else list(argv)
    return _STARTUP_FLAG in args


def is_startup_enabled() -> bool:
    """Есть ли запись автозапуска iNetLog в HKCU\\...\\Run."""
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, _STARTUP_VALUE)
    except OSError:
        return False
    return bool(str(value).strip())


def set_startup_enabled(enabled: bool) -> None:
    """Добавляет или удаляет запись автозапуска. При ошибке реестра бросает OSError."""
    if winreg is None:
        raise RuntimeError(tr("msg.autostart_windows_only"))

    if enabled:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, _STARTUP_VALUE, 0, winreg.REG_SZ, startup_command())
        return

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _STARTUP_VALUE)
    except FileNotFoundError:
        # Раздела или значения уже нет — результат тот же, что нам нужен.
        pass


def app_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def data_directory() -> Path:
    """Папка рядом с exe/скриптом (портативный режим), иначе %APPDATA%\\iNetLog."""
    candidate = app_directory()
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".inetlog-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return candidate
    except OSError:
        pass

    fallback = Path(os.environ.get("APPDATA") or Path.home()) / APP_NAME
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def database_path() -> Path:
    return data_directory() / "inetlog.db"


def main() -> int:
    def log_exception(exc_type, exc, tb) -> None:
        import traceback

        try:
            text = "".join(traceback.format_exception(exc_type, exc, tb))
            (data_directory() / "inetlog-error.log").write_text(text, encoding="utf-8")
        except OSError:
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = log_exception

    app = QApplication(sys.argv)
    app.setOrganizationName(APP_NAME)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(resource_path("icons/inetlog.ico"))))

    window = MainWindow(database_path())
    if start_minimized():
        window.showMinimized()
    else:
        window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
