# iNetLog — internet speed monitor

**iNetLog** is a lightweight Windows app that keeps an eye on your connection quality:
it measures speed and latency on a schedule, stores the history and shows it on clear,
interactive charts. No installation — just one portable executable.

*Русская версия: [README.ru.md](README.ru.md).*

## Features

* **Scheduled measurements** of Download, Upload and Ping — every 1 to 60 minutes.
  You can also run a test at any time.
* **Local history** that survives restarts. Failed attempts are recorded too, so you can
  see when and why the connection dropped.
* **Speed charts** for the last 24 hours, 7 days, 30 days, all time, or any custom date
  range. Show only the series you need — Download, Upload, or both.
* **Chart zoom**: mouse wheel zooms the time axis, drag a box to zoom into an area,
  drag to pan, double-click to reset. The speed axis adjusts automatically.
* **Period summary**: current values, average and maximum, plus a table of recent
  measurements with server and ISP details.
* **Light and dark themes** — switch from the View menu or with the sun/moon button.
* **English and Russian UI** — English by default; change the language on the fly from
  the View menu or with the flag button, no restart needed.
* **Export history** to CSV and Excel — handy for reports and spreadsheet analysis.
* **Run at Windows startup** — the app starts minimized and keeps logging in the background.
* **Portable** — all data stays next to the program, so the folder can be moved freely.

## Quick start

Download `iNetLog.exe` from the Releases page and run it — no installation required. The
first measurement starts automatically a couple of seconds after launch; after that it
follows the selected interval.

You can minimize the app and leave it running: measurements continue on schedule, and the
window is there whenever you want to check the results.

## Running from source

Python 3.10–3.13 is required.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

## Where data is stored

| File | Contents |
| --- | --- |
| `inetlog.db` | measurement history |
| `inetlog.ini` | settings: theme, language, interval, period, chart visibility |

Both files are created next to `iNetLog.exe`. If that folder is not writable, they are
saved to `%APPDATA%\iNetLog` instead.

## Export and keyboard shortcuts

| Action | How to invoke |
| --- | --- |
| Export to CSV | File → Export to CSV…, `Ctrl+E` |
| Export to Excel | File → Export to Excel…, `Ctrl+Shift+E` |
| Measure now | Data → Measure now, `Ctrl+R` |
| Show/hide charts | View → Show charts, `Ctrl+G` |
| Reset chart zoom | View → Reset chart zoom, `Ctrl+0` |
| Quit | `Ctrl+Q` |

Export always includes the full measurement history, regardless of the period selected on
the chart. The Excel file comes with a formatted header, filters and errors highlighted in red.

## Autostart

Enable Data → Run at Windows startup. No administrator rights are needed, and the window
starts minimized. If you move the app to another folder, enable autostart again so the path
is updated.

## Good to know

* A speed test uses the whole available bandwidth — close torrents and streams for accurate
  results.
* The interface never freezes during a test: measurements run in the background.
* Measurement times are based on the computer's local clock.

## License

[MIT](LICENSE)
