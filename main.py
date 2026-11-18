"""啟動瀏覽器。

執行：
    雙擊「啟動瀏覽器.bat」
或：
    %LOCALAPPDATA%\\local-browser-venv\\Scripts\\python.exe main.py
"""

from __future__ import annotations

import ctypes
import faulthandler
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 旁邊有啟動批次檔時是原始碼；安裝版沒有這個檔，資料改放到使用者目錄。
SOURCE_TREE = (ROOT / "啟動瀏覽器.bat").is_file()
RUNTIME = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "LocalBrowser"
RUNTIME.mkdir(parents=True, exist_ok=True)
os.chdir(RUNTIME)
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--lang=zh-TW")

LOG = (ROOT / "error.log") if SOURCE_TREE else (RUNTIME / "error.log")
LIBRARY = (ROOT / "data" / "library.json") if SOURCE_TREE else (RUNTIME / "library.json")


def _report(title: str, text: str) -> None:
    try:
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    except OSError:
        pass
    try:
        ctypes.windll.user32.MessageBoxW(0, text[:1500], title, 0x10)
    except Exception:
        pass


try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Local.SelfMade.Browser")
except Exception:
    pass

try:
    from PySide6.QtCore import QLocale
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import QApplication
    from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401

    from engine import attach_downloads, make_profile
    from store import Store
    from style import stylesheet
    from window import BrowserWindow
except Exception:
    _report("瀏覽器無法啟動", "無法載入 Qt WebEngine。請重新安裝瀏覽器。\n\n" + traceback.format_exc())
    raise SystemExit(1)


def make_icon() -> QIcon:
    return QIcon(str(ROOT / "app-icon.png"))


def main() -> int:
    log = LOG.open("a", encoding="utf-8")
    faulthandler.enable(log)
    sys.excepthook = lambda etype, value, tb: _report(
        "瀏覽器發生錯誤",
        "".join(traceback.format_exception(etype, value, tb)),
    )
    QLocale.setDefault(QLocale(QLocale.Language.Chinese, QLocale.Country.Taiwan))
    app = QApplication(sys.argv)
    app.setApplicationName("LocalBrowser")
    app.setOrganizationName("LocalBrowser")
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft JhengHei UI", 10))
    app.setStyleSheet(stylesheet())
    icon = make_icon()
    app.setWindowIcon(icon)
    profile = make_profile(app)
    attach_downloads(profile)
    store = Store(LIBRARY)
    window = BrowserWindow(profile, store, restore=True)
    window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        _report("瀏覽器發生錯誤", traceback.format_exc())
        raise
