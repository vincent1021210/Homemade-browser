"""一個分頁：工具列、新分頁，或是一塊 WebEngine 網頁。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QStringListModel, QTimer, QUrl, Signal
from PySide6.QtWidgets import (
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from engine import configure_page
from home import NewTabPage
from location import interpret


def repolish(widget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class AddressEdit(QLineEdit):
    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)


class AddressBar(QFrame):
    submitted = Signal(str)
    focused = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("addressBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 8, 0)
        layout.setSpacing(6)
        self.lock = QLabel()
        self.lock.hide()
        self.edit = AddressEdit()
        self.edit.setObjectName("addressEdit")
        self.edit.setPlaceholderText("搜尋或輸入網址")
        self.edit.setClearButtonEnabled(True)
        self.edit.returnPressed.connect(lambda: self.submitted.emit(self.edit.text()))
        self.edit.installEventFilter(self)
        layout.addWidget(self.lock)
        layout.addWidget(self.edit, 1)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.edit and event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self.setProperty("focused", event.type() == QEvent.Type.FocusIn)
            repolish(self)
            if event.type() == QEvent.Type.FocusIn:
                self.focused.emit()
        return super().eventFilter(obj, event)

    def set_text(self, text: str) -> None:
        if self.edit.text() != text:
            self.edit.setText(text)

    def set_security(self, kind: str) -> None:
        if kind == "secure":
            self.lock.setObjectName("secure")
            self.lock.setText("安全")
            self.lock.setToolTip("連線已加密")
            self.lock.show()
        elif kind == "insecure":
            self.lock.setObjectName("insecure")
            self.lock.setText("未加密")
            self.lock.setToolTip("連線未加密")
            self.lock.show()
        else:
            self.lock.hide()
            self.lock.setText("")
        repolish(self.lock)


class IconButton(QPushButton):
    def __init__(self, text: str, tip: str):
        super().__init__(text)
        self.setObjectName("iconButton")
        self.setToolTip(tip)
        self.setAccessibleName(tip.split("（")[0])
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(36, 36)


class BookmarkButton(QPushButton):
    open_here = Signal(str)
    open_new = Signal(str)
    remove_requested = Signal(str)

    def __init__(self, title: str, url: str):
        super().__init__()
        self.url = url
        self.setObjectName("bookmarkButton")
        self.setToolTip(f"{title}\n{url}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMaximumWidth(180)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setText(self.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, 160))
        self.clicked.connect(lambda *_args: self.open_here.emit(self.url))

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self.open_new.emit(self.url)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.addAction("開啟", lambda: self.open_here.emit(self.url))
        menu.addAction("在新分頁開啟", lambda: self.open_new.emit(self.url))
        menu.addAction("移除書籤", lambda: self.remove_requested.emit(self.url))
        point = event.globalPos() if hasattr(event, "globalPos") else event.globalPosition().toPoint()
        menu.exec(point)


class FindBar(QWidget):
    def __init__(self, tab: "BrowserTab"):
        super().__init__()
        self.tab = tab
        self.setObjectName("findBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        self.edit = QLineEdit()
        self.edit.setObjectName("findEdit")
        self.edit.setPlaceholderText("在頁面中尋找")
        self.edit.textChanged.connect(lambda text: tab.find(text))
        self.edit.returnPressed.connect(lambda: tab.find(self.edit.text()))
        previous = QPushButton("上一個")
        previous.setObjectName("textButton")
        nxt = QPushButton("下一個")
        nxt.setObjectName("textButton")
        close = QPushButton("關閉")
        close.setObjectName("textButton")
        previous.clicked.connect(lambda: tab.find(self.edit.text(), backward=True))
        nxt.clicked.connect(lambda: tab.find(self.edit.text()))
        close.clicked.connect(tab.hide_find)
        layout.addWidget(self.edit, 1)
        layout.addWidget(previous)
        layout.addWidget(nxt)
        layout.addWidget(close)


class BrowserPage(QWebEnginePage):
    def __init__(self, profile, tab: "BrowserTab"):
        super().__init__(profile, tab)
        self.tab = tab

    def createWindow(self, window_type):
        browser = self.tab.browser
        background = window_type == QWebEnginePage.WebWindowType.WebBrowserBackgroundTab
        if window_type == QWebEnginePage.WebWindowType.WebBrowserWindow:
            window = browser.spawn_window(show_home=False)
            tab = window.add_tab(for_popup=True)
            return tab.page
        tab = browser.add_tab(for_popup=True, background=background)
        return tab.page


class BrowserTab(QWidget):
    title_changed = Signal(str)
    icon_changed = Signal(object)

    def __init__(self, profile, store, browser):
        super().__init__()
        self.profile = profile
        self.store = store
        self.browser = browser
        self.showing_home = True
        self.want_home = True
        self.has_page = False
        self.loading = False
        self.ready = False
        self.progress_value = 0

        self.address = AddressBar()
        self.address.submitted.connect(self.navigate)
        self.address.focused.connect(self.refresh_completions)
        self.back_btn = IconButton("←", "上一頁（Alt+Left）")
        self.forward_btn = IconButton("→", "下一頁（Alt+Right）")
        self.reload_btn = IconButton("↻", "重新載入（F5）")
        self.home_btn = IconButton("⌂", "首頁")
        self.star = IconButton("☆", "加入書籤（Ctrl+D）")
        self.menu_btn = IconButton("⋯", "選單")
        self.back_btn.clicked.connect(self.back)
        self.forward_btn.clicked.connect(self.forward)
        self.reload_btn.clicked.connect(self.reload_or_stop)
        self.home_btn.clicked.connect(self.go_home)
        self.star.clicked.connect(self.toggle_bookmark)
        self.menu_btn.clicked.connect(lambda: self.browser.open_menu(self.menu_btn))

        self.toolbar = QWidget()
        self.toolbar.setObjectName("toolbar")
        tools = QHBoxLayout(self.toolbar)
        tools.setContentsMargins(8, 6, 8, 6)
        tools.setSpacing(2)
        for button in (self.back_btn, self.forward_btn, self.reload_btn, self.home_btn):
            tools.addWidget(button)
        tools.addSpacing(6)
        tools.addWidget(self.address, 1)
        tools.addSpacing(4)
        tools.addWidget(self.star)
        tools.addWidget(self.menu_btn)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.hide()

        self.bookmark_scroll = QScrollArea()
        self.bookmark_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.bookmark_scroll.setFixedHeight(42)
        self.bookmark_scroll.setWidgetResizable(False)
        self.bookmark_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.bookmark_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bookmark_host = QWidget()
        self.bookmark_host.setObjectName("bookmarkBar")
        self.bookmark_layout = QHBoxLayout(self.bookmark_host)
        self.bookmark_layout.setContentsMargins(8, 4, 8, 4)
        self.bookmark_layout.setSpacing(6)
        self.bookmark_scroll.setWidget(self.bookmark_host)

        self.home = NewTabPage(store)
        self.home.open_url.connect(self.navigate)
        self.home.open_new.connect(lambda url: self.browser.add_tab(url))
        self.view = QWebEngineView()
        self.page = BrowserPage(profile, self)
        self.view.setPage(self.page)
        configure_page(self.page, self, browser.set_immersive)
        self.view.installEventFilter(self)
        self.view.titleChanged.connect(self.on_title)
        self.view.urlChanged.connect(self.on_url_changed)
        self.view.iconChanged.connect(self.icon_changed.emit)
        self.view.loadStarted.connect(self.on_load_started)
        self.view.loadProgress.connect(self.on_load_progress)
        self.view.loadFinished.connect(self.on_load_finished)
        self.page.linkHovered.connect(self.on_hover)

        self.stack = QStackedWidget()
        self.home.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.view)
        self.stack.setCurrentWidget(self.home)

        self.find_bar = FindBar(self)
        self.find_bar.hide()

        self.status_bar = QWidget()
        self.status_bar.setObjectName("statusBar")
        self.status_bar.setFixedHeight(24)
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(10, 0, 10, 0)
        self.status = QLabel("就緒")
        self.status.setObjectName("statusText")
        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("zoomText")
        status_layout.addWidget(self.status, 1)
        status_layout.addWidget(self.zoom_label)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.toolbar)
        root.addWidget(self.progress)
        root.addWidget(self.bookmark_scroll)
        root.addWidget(self.stack, 1)
        root.addWidget(self.find_bar)
        root.addWidget(self.status_bar)

        self.completion_model = QStringListModel(self)
        self.completer = QCompleter(self.completion_model, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setMaxVisibleItems(8)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.address.edit.setCompleter(self.completer)
        self.completer.activated[str].connect(self.navigate)

        self.rebuild_bookmarks()
        self.store.listeners.append(self.rebuild_bookmarks)
        self.refresh_chrome()

    def cleanup(self) -> None:
        try:
            self.store.listeners.remove(self.rebuild_bookmarks)
        except ValueError:
            pass

    def eventFilter(self, obj, event) -> bool:
        if obj is self.view and event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                QTimer.singleShot(30, self.refresh_chrome)
        return super().eventFilter(obj, event)

    def set_chrome_visible(self, visible: bool) -> None:
        self.toolbar.setVisible(visible)
        self.bookmark_scroll.setVisible(visible and bool(self.store.bookmarks()))
        self.status_bar.setVisible(visible)
        self.progress.setVisible(visible and 0 < self.progress_value < 100 and not self.showing_home)
        if not visible:
            self.find_bar.hide()

    def show_page(self) -> None:
        self.showing_home = False
        self.stack.setCurrentWidget(self.view)

    def current_http_url(self) -> str:
        url = self.view.url()
        text = url.toString()
        if not url.isValid() or not text or text == "about:blank":
            return ""
        return text

    def session_url(self) -> str:
        if self.showing_home:
            return ""
        return self.current_http_url()

    def security(self) -> str:
        scheme = self.view.url().scheme().lower()
        if scheme == "https":
            return "secure"
        if scheme == "http":
            return "insecure"
        return "other"

    def can_back(self) -> bool:
        return not self.showing_home

    def can_forward(self) -> bool:
        if self.showing_home:
            return self.has_page
        return self.view.history().canGoForward()

    def navigate(self, text: str) -> None:
        target = interpret(text)
        if not target:
            self.go_home()
            return
        self.want_home = False
        self.has_page = True
        self.show_page()
        self.address.edit.clearFocus()
        if self.current_http_url() == target:
            self.view.reload()
        else:
            self.view.setUrl(QUrl(target))
        self.view.setFocus()
        self.refresh_chrome()
        self.browser.note_session()

    def go_home(self, focus: bool = True) -> None:
        self.want_home = True
        self.view.stop()
        self.showing_home = True
        self.loading = False
        self.progress_value = 0
        self.stack.setCurrentWidget(self.home)
        self.home.refresh()
        self.refresh_chrome()
        self._emit_title()
        if focus and self.browser.tabs.currentWidget() is self:
            self.home.focus_search()
        self.browser.note_session()

    def prepare_for_popup(self) -> None:
        self.want_home = False
        self.has_page = True
        self.show_page()
        self.refresh_chrome()

    def back(self) -> None:
        if self.showing_home:
            return
        if self.view.history().canGoBack():
            self.want_home = False
            self.view.back()
            return
        self.go_home()

    def forward(self) -> None:
        if self.showing_home and self.has_page:
            self.want_home = False
            self.show_page()
            self.refresh_chrome()
            self._emit_title()
            self.view.setFocus()
            self.browser.note_session()
            return
        if self.view.history().canGoForward():
            self.want_home = False
            self.view.forward()

    def stop(self) -> None:
        self.view.stop()
        self.loading = False
        self.progress_value = 0
        self.refresh_chrome()

    def reload(self) -> None:
        if self.showing_home:
            self.home.refresh()
            self.set_status("已更新新分頁")
            return
        self.want_home = False
        self.view.reload()

    def reload_or_stop(self) -> None:
        if self.loading and not self.showing_home:
            self.stop()
            return
        self.reload()

    def toggle_bookmark(self) -> None:
        url = self.current_http_url()
        if not url or self.showing_home:
            return
        if self.store.is_bookmarked(url):
            self.store.remove_bookmark(url)
            self.set_status("已移除書籤")
        else:
            self.store.add_bookmark(self.view.title() or url, url)
            self.set_status("已加入書籤")
        self.refresh_chrome()

    def zoom(self, delta: float | None) -> None:
        factor = 1.0 if delta is None else min(3.0, max(0.25, self.view.zoomFactor() + delta))
        self.view.setZoomFactor(factor)
        self.refresh_chrome()

    def find(self, text: str, backward: bool = False) -> None:
        flags = QWebEnginePage.FindFlag.FindBackward if backward else QWebEnginePage.FindFlag(0)
        self.page.findText(text, flags)

    def show_find(self) -> None:
        self.find_bar.show()
        self.find_bar.edit.setFocus()
        self.find_bar.edit.selectAll()
        if self.find_bar.edit.text():
            self.find(self.find_bar.edit.text())

    def hide_find(self) -> None:
        self.find_bar.hide()
        self.page.findText("")

    def set_status(self, text: str) -> None:
        self.status.setText(text or "就緒")

    def on_hover(self, url: str) -> None:
        self.set_status(url or "就緒")

    def on_load_started(self) -> None:
        if self.want_home:
            return
        self.loading = True
        self.ready = False
        self.progress_value = 0
        self.refresh_chrome()

    def on_load_progress(self, value: int) -> None:
        if self.showing_home:
            return
        self.progress_value = value
        self.loading = value < 100
        self.refresh_chrome()

    def on_load_finished(self, ok: bool) -> None:
        self.loading = False
        self.progress_value = 0
        if self.showing_home or self.want_home:
            self.refresh_chrome()
            return
        self.ready = bool(ok)
        if ok:
            self.store.add_history(self.view.title(), self.current_http_url())
            self.set_status("就緒")
        else:
            self.set_status("無法載入這個頁面")
        self.refresh_chrome()
        self._emit_title()

    def on_title(self, title: str) -> None:
        self._emit_title()
        if self.ready and not self.showing_home:
            self.store.rename_history(self.current_http_url(), title)

    def on_url_changed(self, url: QUrl) -> None:
        text = url.toString()
        if not self.want_home and text and text != "about:blank":
            self.has_page = True
            self.show_page()
        self.refresh_chrome()
        self.browser.note_session()

    def _emit_title(self) -> None:
        if self.showing_home:
            self.title_changed.emit("")
            return
        self.title_changed.emit(self.view.title() or "新分頁")

    def refresh_chrome(self) -> None:
        url = "" if self.showing_home else self.current_http_url()
        if not self.address.edit.hasFocus():
            self.address.set_text(url)
        self.address.set_security("home" if self.showing_home or not url else self.security())
        self.back_btn.setEnabled(self.can_back())
        self.forward_btn.setEnabled(self.can_forward())
        loading = self.loading and not self.showing_home
        self.reload_btn.setText("✕" if loading else "↻")
        self.reload_btn.setToolTip("停止" if loading else "重新載入（F5）")
        bookmarked = bool(url) and self.store.is_bookmarked(url)
        self.star.setEnabled(bool(url))
        self.star.setText("★" if bookmarked else "☆")
        self.star.setProperty("bookmarked", "true" if bookmarked else "false")
        self.star.setToolTip("移除書籤（Ctrl+D）" if bookmarked else "加入書籤（Ctrl+D）")
        repolish(self.star)
        active = (not self.showing_home) and 0 < self.progress_value < 100
        self.progress.setVisible(active)
        if active:
            self.progress.setValue(self.progress_value)
        self.zoom_label.setText(f"{int(round(self.view.zoomFactor() * 100))}%")

    def refresh_completions(self) -> None:
        seen: set[str] = set()
        urls: list[str] = []
        for item in self.store.bookmarks() + self.store.history():
            url = item.get("url") or ""
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
        self.completion_model.setStringList(urls[:200])

    def rebuild_bookmarks(self) -> None:
        while self.bookmark_layout.count():
            item = self.bookmark_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        marks = self.store.bookmarks()
        for mark in marks:
            button = BookmarkButton(mark.get("title") or mark["url"], mark["url"])
            button.open_here.connect(self.navigate)
            button.open_new.connect(lambda url: self.browser.add_tab(url))
            button.remove_requested.connect(self.store.remove_bookmark)
            self.bookmark_layout.addWidget(button)
        self.bookmark_layout.addStretch(1)
        self.bookmark_host.adjustSize()
        self.bookmark_host.resize(self.bookmark_host.sizeHint())
        self.bookmark_scroll.setVisible(bool(marks) and self.toolbar.isVisible())
