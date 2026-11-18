"""視窗與分頁列。快捷鍵作用在目前這個分頁上。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from tab import BrowserTab

SHORTCUTS = (
    ("Ctrl+T", "新分頁"),
    ("Ctrl+N", "新視窗"),
    ("Ctrl+W", "關閉分頁"),
    ("Ctrl+L", "選取網址列"),
    ("Ctrl+D", "加入或移除書籤"),
    ("Ctrl+F", "在頁面中尋找"),
    ("Ctrl+Tab", "下一個分頁"),
    ("Ctrl+Shift+Tab", "上一個分頁"),
    ("Alt+←  /  Alt+→", "上一頁 / 下一頁"),
    ("F5", "重新載入"),
    ("Esc", "停止載入、關閉尋找，或離開全螢幕"),
    ("Ctrl+加號  /  Ctrl+減號", "放大 / 縮小"),
    ("Ctrl+0", "實際大小"),
)


class BrowserWindow(QMainWindow):
    windows: list["BrowserWindow"] = []

    def __init__(self, profile, store, restore: bool = True):
        super().__init__()
        self.profile = profile
        self.store = store
        self._restoring = False
        self._immersive = False
        BrowserWindow.windows.append(self)
        self.setWindowTitle("瀏覽器")
        self.setMinimumSize(880, 600)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_current_changed)
        self.tabs.tabBarDoubleClicked.connect(self._on_tab_double_click)
        self.tabs.tabBar().tabMoved.connect(lambda *_args: self.note_session())
        self.tabs.tabBar().installEventFilter(self)
        self.setCentralWidget(self.tabs)
        self._build_menu()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self.place()
        if restore:
            self.restore_session()

    def _act(self, text: str, slot, shortcut=None) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            keys = shortcut if isinstance(shortcut, (list, tuple)) else (shortcut,)
            action.setShortcuts([QKeySequence(key) for key in keys])
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.addAction(action)
        return action

    def _build_menu(self) -> None:
        self.menu = QMenu(self)
        self.menu.addAction(self._act("新分頁", self.add_blank, "Ctrl+T"))
        self.menu.addAction(self._act("新視窗", lambda: self.spawn_window(True), "Ctrl+N"))
        self.menu.addAction(self._act("關閉分頁", self.close_current, "Ctrl+W"))
        self.menu.addSeparator()
        self.menu.addAction(self._act("上一頁", self.go_back, "Alt+Left"))
        self.menu.addAction(self._act("下一頁", self.go_forward, "Alt+Right"))
        self.menu.addAction(self._act("重新載入", self.reload, "F5"))
        self.menu.addAction(self._act("首頁", self.go_home))
        self.menu.addSeparator()
        self.menu.addAction(self._act("選取網址列", self.focus_address, "Ctrl+L"))
        self.menu.addAction(self._act("加入或移除書籤", self.toggle_bookmark, "Ctrl+D"))
        self.menu.addAction(self._act("在頁面中尋找", self.show_find, "Ctrl+F"))
        self.menu.addSeparator()
        self.menu.addAction(self._act("放大", lambda: self.zoom(0.1), ("Ctrl++", "Ctrl+=")))
        self.menu.addAction(self._act("縮小", lambda: self.zoom(-0.1), "Ctrl+-"))
        self.menu.addAction(self._act("實際大小", lambda: self.zoom(None), "Ctrl+0"))
        self.menu.addSeparator()
        self.menu.addAction(self._act("下一個分頁", self.next_tab, "Ctrl+Tab"))
        self.menu.addAction(self._act("上一個分頁", self.prev_tab, "Ctrl+Shift+Tab"))
        self.menu.addSeparator()
        self.menu.addAction(self._act("清除瀏覽資料", self.clear_data))
        self.menu.addAction(self._act("鍵盤快捷鍵", self.show_shortcuts))
        self.menu.addAction(self._act("關於", self.show_about))

    def open_menu(self, anchor) -> None:
        self.menu.popup(anchor.mapToGlobal(QPoint(0, anchor.height())))

    def current_tab(self) -> BrowserTab | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, BrowserTab) else None

    def add_tab(self, url: str | None = None, for_popup: bool = False, background: bool = False) -> BrowserTab:
        tab = BrowserTab(self.profile, self.store, self)
        tab.title_changed.connect(lambda text, owner=tab: self._on_tab_title(owner, text))
        tab.icon_changed.connect(lambda icon, owner=tab: self._on_tab_icon(owner, icon))
        index = self.tabs.addTab(tab, "新分頁")
        self.tabs.setTabToolTip(index, "新分頁")
        if not background:
            self.tabs.setCurrentIndex(index)
        if url:
            tab.navigate(url)
        elif for_popup:
            tab.prepare_for_popup()
        else:
            tab.go_home(focus=not self._restoring)
        return tab

    def add_blank(self) -> None:
        self.add_tab()

    def spawn_window(self, show_home: bool = True) -> "BrowserWindow":
        window = BrowserWindow(self.profile, self.store, restore=False)
        if show_home:
            window.add_tab()
        window.show()
        window.raise_()
        window.activateWindow()
        return window

    def close_tab(self, index: int) -> None:
        if index < 0 or index >= self.tabs.count():
            return
        if self.tabs.count() <= 1:
            self.close()
            return
        tab = self.tabs.widget(index)
        if isinstance(tab, BrowserTab):
            tab.cleanup()
        self.tabs.removeTab(index)
        if tab is not None:
            tab.deleteLater()
        self.note_session()

    def close_current(self) -> None:
        self.close_tab(self.tabs.currentIndex())

    def next_tab(self) -> None:
        count = self.tabs.count()
        if count > 1:
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % count)

    def prev_tab(self) -> None:
        count = self.tabs.count()
        if count > 1:
            self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % count)

    def go_back(self) -> None:
        tab = self.current_tab()
        if tab:
            tab.back()

    def go_forward(self) -> None:
        tab = self.current_tab()
        if tab:
            tab.forward()

    def reload(self) -> None:
        tab = self.current_tab()
        if tab:
            tab.reload()

    def go_home(self) -> None:
        tab = self.current_tab()
        if tab:
            tab.go_home()

    def focus_address(self) -> None:
        tab = self.current_tab()
        if tab:
            tab.address.edit.setFocus()
            tab.address.edit.selectAll()

    def toggle_bookmark(self) -> None:
        tab = self.current_tab()
        if tab:
            tab.toggle_bookmark()

    def show_find(self) -> None:
        tab = self.current_tab()
        if tab:
            tab.show_find()

    def zoom(self, delta: float | None) -> None:
        tab = self.current_tab()
        if tab:
            tab.zoom(delta)

    def set_immersive(self, enabled: bool) -> None:
        self._immersive = enabled
        self.tabs.tabBar().setVisible(not enabled)
        tab = self.current_tab()
        if tab is not None:
            tab.set_chrome_visible(not enabled)
        if enabled:
            self.showFullScreen()
        elif self.isFullScreen():
            self.showNormal()

    def note_session(self) -> None:
        if self._restoring or len(BrowserWindow.windows) != 1:
            return
        tabs = []
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            tabs.append(widget.session_url() if isinstance(widget, BrowserTab) else "")
        self.store.set_session(tabs, max(0, self.tabs.currentIndex()))

    def restore_session(self) -> None:
        self._restoring = True
        session = self.store.session()
        tabs = [url for url in session.get("tabs") or [] if isinstance(url, str)]
        usable = tabs[:20]
        if not usable:
            self.add_tab()
        else:
            for url in usable:
                self.add_tab(url or None)
            index = session.get("index") or 0
            if isinstance(index, int) and 0 <= index < self.tabs.count():
                self.tabs.setCurrentIndex(index)
        self._restoring = False
        tab = self.current_tab()
        if tab and tab.showing_home:
            tab.home.focus_search()

    def place(self) -> None:
        geometry = self.store.geometry()
        if geometry and self._geometry_visible(geometry):
            self.setGeometry(
                int(geometry["x"]),
                int(geometry["y"]),
                int(geometry["w"]),
                int(geometry["h"]),
            )
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1200, 800)
            return
        area = screen.availableGeometry()
        self.resize(min(1280, max(880, area.width() - 80)), min(840, max(600, area.height() - 80)))
        frame = self.frameGeometry()
        frame.moveCenter(area.center())
        self.move(frame.topLeft())

    def _geometry_visible(self, geometry: dict) -> bool:
        from PySide6.QtCore import QRect

        rect = QRect(int(geometry["x"]), int(geometry["y"]), int(geometry["w"]), int(geometry["h"]))
        if rect.width() < 400 or rect.height() < 300:
            return False
        return any(screen.availableGeometry().intersects(rect) for screen in QApplication.screens())

    def _persist(self) -> None:
        tabs = []
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            tabs.append(widget.session_url() if isinstance(widget, BrowserTab) else "")
        self.store.set_session(tabs, max(0, self.tabs.currentIndex()))
        geometry = self.geometry()
        self.store.set_geometry(geometry.x(), geometry.y(), geometry.width(), geometry.height())

    def _on_tab_title(self, tab: BrowserTab, title: str) -> None:
        index = self.tabs.indexOf(tab)
        if index < 0:
            return
        label = (title or "").strip() or "新分頁"
        self.tabs.setTabText(index, label)
        self.tabs.setTabToolTip(index, label)
        if self.tabs.currentWidget() is tab:
            self.setWindowTitle("瀏覽器" if label == "新分頁" else f"{label} - 瀏覽器")

    def _on_tab_icon(self, tab: BrowserTab, icon) -> None:
        index = self.tabs.indexOf(tab)
        if index >= 0 and icon is not None:
            self.tabs.setTabIcon(index, icon)

    def _on_current_changed(self, _index: int) -> None:
        if self._immersive:
            tab = self.current_tab()
            if tab is not None:
                tab.page.triggerAction(QWebEnginePage.WebAction.ExitFullScreen)
            self.set_immersive(False)
        tab = self.current_tab()
        if tab is None:
            self.setWindowTitle("瀏覽器")
        else:
            self._on_tab_title(tab, "" if tab.showing_home else tab.view.title())
        self.note_session()

    def _on_tab_double_click(self, index: int) -> None:
        if index < 0:
            self.add_tab()

    def clear_data(self) -> None:
        answer = QMessageBox.question(
            self,
            "清除瀏覽資料",
            "要清除瀏覽紀錄、Cookie 與快取嗎？書籤會保留。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.store.clear_history()
        self.profile.cookieStore().deleteAllCookies()
        self.profile.clearHttpCache()
        tab = self.current_tab()
        if tab is not None:
            tab.home.refresh()
            tab.refresh_completions()
            tab.set_status("已清除瀏覽紀錄、Cookie 與快取")

    def show_shortcuts(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("鍵盤快捷鍵")
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        for keys, description in SHORTCUTS:
            label = QLabel(description)
            form.addRow(keys, label)
        layout.addLayout(form)
        row = QHBoxLayout()
        row.addStretch(1)
        close = QPushButton("關閉")
        close.clicked.connect(dialog.accept)
        row.addWidget(close)
        layout.addLayout(row)
        dialog.exec()

    def show_about(self) -> None:
        storage = self.profile.persistentStoragePath()
        library = str(self.store.path)
        QMessageBox.information(
            self,
            "關於",
            "這是一個自己寫的瀏覽器外殼。\n\n"
            "分頁、網址列、書籤、瀏覽紀錄與快捷鍵都在這個程式裡。\n"
            "網頁的下載、排版、JavaScript 與影片由 Qt WebEngine（Chromium）負責，"
            "所以可以打開現代網站。\n\n"
            f"網頁資料：\n{storage}\n\n"
            f"書籤與紀錄：\n{library}",
        )

    def _should_take_escape(self) -> bool:
        if self._immersive:
            return True
        tab = self.current_tab()
        if tab is None:
            return False
        if tab.find_bar.isVisible():
            return True
        if tab.address.edit.hasFocus() or tab.home.search.hasFocus():
            return True
        return tab.loading and not tab.showing_home

    def on_escape(self) -> None:
        tab = self.current_tab()
        if self._immersive:
            if tab is not None:
                tab.page.triggerAction(QWebEnginePage.WebAction.ExitFullScreen)
            self.set_immersive(False)
            return
        if tab is not None and tab.find_bar.isVisible():
            tab.hide_find()
            return
        if tab is not None and (tab.address.edit.hasFocus() or tab.home.search.hasFocus()):
            tab.address.edit.clearFocus()
            tab.home.search.clearFocus()
            if not tab.showing_home:
                tab.view.setFocus()
            return
        if tab is not None and tab.loading and not tab.showing_home:
            tab.stop()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.tabs.tabBar() and event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.MiddleButton:
                point = event.position().toPoint() if hasattr(event, "position") else event.pos()
                index = self.tabs.tabBar().tabAt(point)
                if index >= 0:
                    self.close_tab(index)
                    return True
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            window = obj.window() if isinstance(obj, QWidget) else None
            if window is self and self._should_take_escape():
                self.on_escape()
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event) -> None:
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        others = [window for window in BrowserWindow.windows if window is not self]
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            if isinstance(widget, BrowserTab):
                widget.cleanup()
        if not others:
            self._persist()
        if self in BrowserWindow.windows:
            BrowserWindow.windows.remove(self)
        super().closeEvent(event)
