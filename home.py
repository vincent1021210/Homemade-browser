"""新分頁。搜尋、常用網站與最近瀏覽都從這裡出發。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

SITES = (
    ("Google", "https://www.google.com/?hl=zh-TW"),
    ("YouTube", "https://www.youtube.com"),
    ("維基百科", "https://zh.wikipedia.org"),
    ("GitHub", "https://github.com"),
    ("iThome", "https://www.ithome.com.tw"),
    ("中央社", "https://www.cna.com.tw"),
)


class SiteButton(QPushButton):
    open_here = Signal(str)
    open_new = Signal(str)

    def __init__(self, title: str, url: str, object_name: str):
        super().__init__(title)
        self.url = url
        self.setObjectName(object_name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(url)
        self.clicked.connect(lambda *_args: self.open_here.emit(self.url))

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self.open_new.emit(self.url)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class NewTabPage(QWidget):
    open_url = Signal(str)
    open_new = Signal(str)

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.setObjectName("newTab")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("newTab")
        column = QVBoxLayout(content)
        column.setContentsMargins(32, 28, 32, 32)
        column.setSpacing(18)
        column.addStretch(1)

        block = QWidget()
        block.setMaximumWidth(720)
        block.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        body = QVBoxLayout(block)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(14)

        title = QLabel("瀏覽器")
        title.setObjectName("wordmark")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("分頁與書籤是這個程式畫的。網頁本體由 WebEngine 繪製。")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        self.search = QLineEdit()
        self.search.setObjectName("homeSearch")
        self.search.setPlaceholderText("搜尋或輸入網址")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(48)
        self.search.returnPressed.connect(self._submit)

        sites = QGridLayout()
        sites.setSpacing(8)
        for index, (name, url) in enumerate(SITES):
            button = SiteButton(name, url, "linkButton")
            button.open_here.connect(self.open_url.emit)
            button.open_new.connect(self.open_new.emit)
            sites.addWidget(button, index // 3, index % 3)

        self.recent_title = QLabel("最近瀏覽")
        self.recent_title.setObjectName("sectionTitle")
        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(6)

        hint = QLabel("網址列有空白，或不像網址時，會用 Google 搜尋。中鍵可在新分頁打開。")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        body.addWidget(title)
        body.addWidget(subtitle)
        body.addSpacing(8)
        body.addWidget(self.search)
        body.addSpacing(8)
        body.addLayout(sites)
        body.addSpacing(8)
        body.addWidget(self.recent_title)
        body.addLayout(self.recent_box)
        body.addWidget(hint)

        center = QHBoxLayout()
        center.addStretch(1)
        center.addWidget(block, 1)
        center.addStretch(1)
        column.addLayout(center)
        column.addStretch(2)

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.refresh()

    def _submit(self) -> None:
        text = self.search.text().strip()
        if text:
            self.open_url.emit(text)
            self.search.clear()

    def refresh(self) -> None:
        while self.recent_box.count():
            item = self.recent_box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        recent = self.store.history()[:6]
        self.recent_title.setVisible(bool(recent))
        for item in recent:
            button = SiteButton(item.get("title") or item["url"], item["url"], "recentButton")
            button.open_here.connect(self.open_url.emit)
            button.open_new.connect(self.open_new.emit)
            self.recent_box.addWidget(button)

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()
