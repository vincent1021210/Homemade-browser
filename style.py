"""視窗外觀。紙色工具列，網頁區保持淺底。"""


def stylesheet() -> str:
    return """
    QWidget {
        color: #221e18;
        font-size: 13px;
    }
    QMainWindow, QTabWidget::pane {
        background: #f7f4ee;
        border: none;
    }
    QTabBar {
        background: #e7e1d6;
    }
    QTabBar::tab {
        background: transparent;
        color: #5e574c;
        padding: 8px 28px 8px 12px;
        margin: 6px 2px 0 2px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        min-width: 90px;
        max-width: 220px;
    }
    QTabBar::tab:selected {
        background: #f7f4ee;
        color: #221e18;
    }
    QTabBar::tab:hover:!selected {
        background: #efeae0;
    }
    QWidget#toolbar, QWidget#bookmarkBar, QWidget#findBar, QWidget#statusBar {
        background: #f7f4ee;
    }
    QWidget#toolbar {
        border-bottom: 1px solid #e4ddd0;
    }
    QPushButton#iconButton, QPushButton#textButton {
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 0;
    }
    QPushButton#iconButton {
        font-family: "Segoe UI Symbol";
        font-size: 15px;
    }
    QPushButton#iconButton:hover, QPushButton#textButton:hover,
    QPushButton#linkButton:hover, QPushButton#bookmarkButton:hover {
        background: #e6e0d4;
    }
    QPushButton#iconButton:pressed, QPushButton#textButton:pressed,
    QPushButton#linkButton:pressed, QPushButton#bookmarkButton:pressed {
        background: #d9d2c4;
    }
    QPushButton#iconButton:disabled {
        color: #b7b0a4;
    }
    QPushButton#iconButton[bookmarked="true"] {
        color: #9a5b12;
    }
    QFrame#addressBar {
        background: #ffffff;
        border: 1px solid #d9d2c5;
        border-radius: 8px;
    }
    QFrame#addressBar[focused="true"] {
        border: 1px solid #1f6f66;
    }
    QLineEdit#addressEdit, QLineEdit#findEdit, QLineEdit#homeSearch {
        border: none;
        background: transparent;
        selection-background-color: #cfe3df;
        selection-color: #143f3b;
    }
    QLineEdit#homeSearch {
        background: #ffffff;
        border: 1px solid #d9d2c5;
        border-radius: 10px;
        padding: 0 16px;
        font-size: 16px;
    }
    QLineEdit#homeSearch:focus {
        border: 1px solid #1f6f66;
    }
    QWidget#newTab {
        background: #f7f4ee;
    }
    QLabel#wordmark {
        font-size: 40px;
        font-weight: 600;
        color: #1f6f66;
        background: transparent;
    }
    QLabel#subtitle, QLabel#hint, QLabel#statusText, QLabel#zoomText {
        color: #6f675c;
        background: transparent;
    }
    QLabel#sectionTitle {
        color: #6f675c;
        background: transparent;
        font-size: 12px;
    }
    QLabel#secure {
        color: #1f6f66;
        background: transparent;
        font-size: 12px;
    }
    QLabel#insecure {
        color: #9a5b12;
        background: transparent;
        font-size: 12px;
    }
    QPushButton#linkButton, QPushButton#bookmarkButton, QPushButton#recentButton {
        background: #ffffff;
        border: 1px solid #e4ddd0;
        border-radius: 8px;
        padding: 8px 12px;
        text-align: left;
    }
    QProgressBar {
        border: none;
        background: transparent;
        max-height: 3px;
        min-height: 3px;
    }
    QProgressBar::chunk {
        background: #1f6f66;
    }
    QMenu {
        background: #fffdf8;
        border: 1px solid #ddd6c8;
        padding: 4px;
    }
    QMenu::item {
        padding: 7px 28px 7px 14px;
        border-radius: 5px;
    }
    QMenu::item:selected {
        background: #e5f0ee;
        color: #143f3b;
    }
    QToolTip {
        background: #221e18;
        color: #f7f4ee;
        border: none;
        padding: 4px 8px;
    }
    QScrollBar:horizontal {
        height: 8px;
        background: transparent;
    }
    QScrollBar::handle:horizontal {
        background: #d0c8ba;
        border-radius: 4px;
        min-width: 24px;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        width: 0;
        height: 0;
    }
    """
