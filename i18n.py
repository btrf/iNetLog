"""Локализация интерфейса iNetLog: английский (по умолчанию) и русский."""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"
LANGUAGES: tuple[str, ...] = ("en", "ru")

# Ключ -> {"en": ..., "ru": ...}
_STRINGS: dict[str, dict[str, str]] = {
    # ------------------------------------------------------------------ окно
    "app.title_suffix": {
        "en": "internet speed monitor",
        "ru": "мониторинг скорости интернета",
    },
    "app.subtitle": {
        "en": "Scheduled speed tests, SQLite history and charts",
        "ru": "Замер скорости по расписанию, история в SQLite и графики",
    },
    # ------------------------------------------------------------- управление
    "interval.label": {"en": "Interval:", "ru": "Интервал:"},
    "interval.every_minute": {"en": "every minute", "ru": "каждую минуту"},
    "interval.every_n": {"en": "every {minutes} min", "ru": "каждые {minutes} мин"},
    "button.measure": {"en": "Measure now", "ru": "Измерить сейчас"},
    "button.pause": {"en": "Pause", "ru": "Пауза"},
    "button.resume": {"en": "Resume", "ru": "Продолжить"},
    # ----------------------------------------------------------------- статус
    "status.waiting": {"en": "Idle", "ru": "Ожидание"},
    "status.measuring": {"en": "Measuring speed…", "ru": "Идёт измерение скорости…"},
    "status.paused": {
        "en": "automatic tests paused",
        "ru": "автоматические измерения приостановлены",
    },
    "status.next": {
        "en": "next test in {mm}:{ss}",
        "ru": "следующее измерение через {mm}:{ss}",
    },
    "status.error": {"en": "Error: {error}", "ru": "Ошибка: {error}"},
    "status.data": {"en": "Data: {path}", "ru": "Данные: {path}"},
    "status.charts_shown": {"en": "Charts shown", "ru": "Графики показаны"},
    "status.charts_hidden": {"en": "Charts hidden", "ru": "Графики скрыты"},
    "status.zoom_reset": {"en": "Chart zoom reset", "ru": "Масштаб графика сброшен"},
    "status.autostart_on": {
        "en": "iNetLog will start when Windows starts",
        "ru": "iNetLog будет запускаться при входе в Windows",
    },
    "status.autostart_off": {
        "en": "iNetLog autostart disabled",
        "ru": "Автозапуск iNetLog отключён",
    },
    "status.exported": {
        "en": "Exported {count} records to {path}",
        "ru": "Экспортировано {count} записей в {path}",
    },
    "status.cleared": {
        "en": "Measurement history cleared",
        "ru": "История измерений очищена",
    },
    "status.language_en": {
        "en": "Interface language: English",
        "ru": "Язык интерфейса: английский",
    },
    "status.language_ru": {
        "en": "Interface language: Russian",
        "ru": "Язык интерфейса: русский",
    },
    # ---------------------------------------------------------------- единицы
    "unit.mbps": {"en": "Mbit/s", "ru": "Мбит/с"},
    "unit.ms": {"en": "ms", "ru": "мс"},
    # ---------------------------------------------------------------- карточки
    "card.no_data": {"en": "no data", "ru": "нет данных"},
    "card.period_no_data": {
        "en": "no data for the period",
        "ru": "нет данных за период",
    },
    "card.subtitle": {
        "en": "avg {avg} · max {max} · {count} tests",
        "ru": "сред. {avg} · макс {max} · {count} изм.",
    },
    # ----------------------------------------------------------------- таблица
    "table.title": {"en": "Recent measurements", "ru": "Последние измерения"},
    "table.time": {"en": "Time", "ru": "Время"},
    "table.download": {"en": "Download, Mbit/s", "ru": "Download, Мбит/с"},
    "table.upload": {"en": "Upload, Mbit/s", "ru": "Upload, Мбит/с"},
    "table.ping": {"en": "Ping, ms", "ru": "Ping, мс"},
    "table.server": {"en": "Server / note", "ru": "Сервер / примечание"},
    # -------------------------------------------------------------------- меню
    "menu.file": {"en": "File", "ru": "Файл"},
    "menu.data": {"en": "Data", "ru": "Данные"},
    "menu.view": {"en": "View", "ru": "Вид"},
    "menu.help": {"en": "Help", "ru": "Справка"},
    "menu.theme": {"en": "Theme", "ru": "Тема"},
    "menu.language": {"en": "Language", "ru": "Язык"},
    "action.export_csv": {"en": "Export to CSV…", "ru": "Экспорт в CSV…"},
    "action.export_excel": {"en": "Export to Excel…", "ru": "Экспорт в Excel…"},
    "action.quit": {"en": "Quit", "ru": "Выход"},
    "action.measure": {"en": "Measure now", "ru": "Измерить сейчас"},
    "action.open_folder": {
        "en": "Open data folder",
        "ru": "Открыть папку с данными",
    },
    "action.clear_history": {"en": "Clear history…", "ru": "Очистить историю…"},
    "action.autostart": {
        "en": "Run at Windows startup",
        "ru": "Запускать при старте Windows",
    },
    "action.autostart_tooltip": {
        "en": (
            "Autostart via registry key "
            "HKEY_CURRENT_USER\\{run_key} (value “{value}”)"
        ),
        "ru": (
            "Автозапуск через раздел реестра "
            "HKEY_CURRENT_USER\\{run_key} (значение «{value}»)"
        ),
    },
    "action.autostart_windows_only": {
        "en": "Autostart is available on Windows only",
        "ru": "Автозапуск доступен только в Windows",
    },
    "action.show_chart": {"en": "Show charts", "ru": "Показывать графики"},
    "action.show_chart_tooltip": {
        "en": "Hide or show the charts area",
        "ru": "Скрыть или показать область графиков",
    },
    "action.reset_zoom": {
        "en": "Reset chart zoom",
        "ru": "Сбросить масштаб графика",
    },
    "action.reset_zoom_tooltip": {
        "en": "Restore the full range of the selected period",
        "ru": "Вернуть графику полный диапазон выбранного периода",
    },
    "theme.dark": {"en": "Dark", "ru": "Тёмная"},
    "theme.light": {"en": "Light", "ru": "Светлая"},
    "theme.switch_to_light": {
        "en": "Switch to light theme",
        "ru": "Включить светлую тему",
    },
    "theme.switch_to_dark": {
        "en": "Switch to dark theme",
        "ru": "Включить тёмную тему",
    },
    "status.theme_light": {
        "en": "Light theme enabled",
        "ru": "Включена светлая тема",
    },
    "status.theme_dark": {
        "en": "Dark theme enabled",
        "ru": "Включена тёмная тема",
    },
    "action.about": {"en": "About", "ru": "О программе"},
    # --------------------------------------------------------------- сообщения
    "msg.autostart_title": {"en": "Autostart", "ru": "Автозапуск"},
    "msg.autostart_failed": {
        "en": "Could not {verb} autostart.\n\n{error}",
        "ru": "Не удалось {verb} автозапуск.\n\n{error}",
    },
    "verb.enable": {"en": "enable", "ru": "включить"},
    "verb.disable": {"en": "disable", "ru": "отключить"},
    "msg.autostart_registry": {
        "en": "The registry value did not change (access may be denied).",
        "ru": "Запись в реестре не изменилась (возможно, доступ запрещён).",
    },
    "msg.autostart_windows_only": {
        "en": "Autostart is supported on Windows only",
        "ru": "Автозапуск поддерживается только в Windows",
    },
    "dialog.export_csv": {"en": "Export measurements", "ru": "Экспорт измерений"},
    "dialog.export_excel": {"en": "Export to Excel", "ru": "Экспорт в Excel"},
    "dialog.export_error": {"en": "Export error", "ru": "Ошибка экспорта"},
    "msg.openpyxl_missing": {
        "en": (
            "The openpyxl package is not installed. "
            "Install it: pip install openpyxl"
        ),
        "ru": (
            "Не установлен пакет openpyxl. "
            "Установите его: pip install openpyxl"
        ),
    },
    "dialog.clear_title": {"en": "Clear history", "ru": "Очистить историю"},
    "dialog.clear_text": {
        "en": "Delete all saved measurements? This action cannot be undone.",
        "ru": "Удалить все сохранённые измерения? Это действие необратимо.",
    },
    "about.title": {"en": "About", "ru": "О программе"},
    "about.tagline": {
        "en": "Internet speed monitoring.",
        "ru": "Мониторинг скорости интернета.",
    },
    "about.body": {
        "en": (
            "<b>{name} {version}</b><br>{tagline}<br><br>"
            "Database: <code>{path}</code><br><br>"
            "Test backend: speedtest-cli (speedtest.net)."
        ),
        "ru": (
            "<b>{name} {version}</b><br>{tagline}<br><br>"
            "База данных: <code>{path}</code><br><br>"
            "Бэкенд замера: speedtest-cli (speedtest.net)."
        ),
    },
    # ------------------------------------------------------------------ экспорт
    "export.time": {"en": "Time (local)", "ru": "Время (локальное)"},
    "export.download": {"en": "Download, Mbit/s", "ru": "Download, Мбит/с"},
    "export.upload": {"en": "Upload, Mbit/s", "ru": "Upload, Мбит/с"},
    "export.ping": {"en": "Ping, ms", "ru": "Ping, мс"},
    "export.server": {"en": "Server", "ru": "Сервер"},
    "export.isp": {"en": "Provider", "ru": "Провайдер"},
    "export.backend": {"en": "Backend", "ru": "Бэкенд"},
    "export.error": {"en": "Error", "ru": "Ошибка"},
    "export.sheet": {"en": "Measurements", "ru": "Измерения"},
    # ------------------------------------------------------------------- график
    "chart.title": {"en": "Speed, Mbit/s", "ru": "Скорость, Мбит/с"},
    "chart.period": {"en": "Period:", "ru": "Период:"},
    "range.24h": {"en": "24 hours", "ru": "24 часа"},
    "range.7d": {"en": "7 days", "ru": "7 дней"},
    "range.30d": {"en": "30 days", "ru": "30 дней"},
    "range.all": {"en": "All time", "ru": "Всё время"},
    "range.custom": {"en": "Custom range", "ru": "Свой диапазон"},
    "chart.from": {"en": "from", "ru": "с"},
    "chart.to": {"en": "to", "ru": "по"},
    "chart.reset_zoom": {"en": "Reset zoom", "ru": "Сбросить масштаб"},
    "chart.reset_zoom_tooltip": {
        "en": "Restore the full range of the selected period (Ctrl+0)",
        "ru": "Вернуть полный диапазон выбранного периода (Ctrl+0)",
    },
    "chart.controls": {
        "en": (
            "Mouse wheel — zoom\n"
            "Left-drag a box — zoom into area\n"
            "Shift + drag — pan\n"
            "Double click — reset zoom"
        ),
        "ru": (
            "Колесо мыши — масштаб\n"
            "Рамка левой кнопкой — приблизить область\n"
            "Shift + перетаскивание — сдвиг\n"
            "Двойной клик — сбросить масштаб"
        ),
    },
    "chart.no_data": {
        "en": "No data for the selected period",
        "ru": "Нет данных за выбранный период",
    },
    # --------------------------------------------------------------- элементы
    "series.download_tooltip": {
        "en": "Show the Download line on the chart",
        "ru": "Показывать линию Download на графике",
    },
    "series.upload_tooltip": {
        "en": "Show the Upload line on the chart",
        "ru": "Показывать линию Upload на графике",
    },
    "lang.switch_to_en": {
        "en": "Switch to English",
        "ru": "Переключить на английский",
    },
    "lang.switch_to_ru": {
        "en": "Switch to Russian",
        "ru": "Переключить на русский",
    },
}

_language: str = DEFAULT_LANGUAGE


def language() -> str:
    """Текущий код языка интерфейса ("en" или "ru")."""
    return _language


def set_language(code: object) -> str:
    """Устанавливает язык интерфейса. Возвращает фактически выбранный код."""
    global _language
    value = str(code).strip().lower() if code is not None else DEFAULT_LANGUAGE
    _language = value if value in LANGUAGES else DEFAULT_LANGUAGE
    return _language


def language_name(code: str) -> str:
    """Название языка на нём самом (для меню «Язык»)."""
    return "Русский" if code == "ru" else "English"


def tr(key: str, **kwargs: object) -> str:
    """Строка по ключу для текущего языка с подстановкой {параметров}."""
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(_language) or entry.get(DEFAULT_LANGUAGE) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return text
