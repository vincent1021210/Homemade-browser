"""Qt WebEngine 的設定、下載與網站權限。"""

from __future__ import annotations

import os
import re
from pathlib import Path

from PySide6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

PERMISSIONS = {
    "Geolocation": "取得你的位置",
    "MediaAudioCapture": "使用麥克風",
    "MediaVideoCapture": "使用攝影機",
    "MediaAudioVideoCapture": "使用攝影機與麥克風",
    "DesktopVideoCapture": "擷取你的畫面",
    "DesktopAudioVideoCapture": "擷取你的畫面與音訊",
    "Notifications": "顯示通知",
    "MouseLock": "鎖定滑鼠游標",
    "ClipboardReadWrite": "讀取剪貼簿",
    "LocalFontsAccess": "使用這台電腦的字型",
}


def runtime_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LocalBrowser"
    base.mkdir(parents=True, exist_ok=True)
    return base


def make_profile(parent) -> QWebEngineProfile:
    profile = QWebEngineProfile("LocalBrowser", parent)
    base = runtime_dir()
    storage = base / "storage"
    cache = base / "cache"
    storage.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    profile.setPersistentStoragePath(str(storage))
    profile.setCachePath(str(cache))
    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
    )
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
    profile.setHttpCacheMaximumSize(200 * 1024 * 1024)
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        profile.setDownloadPath(str(downloads))
    agent = re.sub(r"\s*QtWebEngine/\S+", "", profile.httpUserAgent())
    profile.setHttpUserAgent(agent)
    settings = profile.settings()
    for name in (
        "JavascriptEnabled",
        "LocalStorageEnabled",
        "PluginsEnabled",
        "FullScreenSupportEnabled",
        "ScrollAnimatorEnabled",
        "PdfViewerEnabled",
        "AutoLoadImages",
        "ErrorPageEnabled",
        "FocusOnNavigationEnabled",
        "JavascriptCanOpenWindows",
        "WebGLEnabled",
        "ScreenCaptureEnabled",
        "AutoLoadIconsForPage",
        "DnsPrefetchEnabled",
    ):
        attribute = getattr(QWebEngineSettings.WebAttribute, name, None)
        if attribute is not None:
            settings.setAttribute(attribute, True)
    return profile


def attach_downloads(profile: QWebEngineProfile) -> None:
    profile.downloadRequested.connect(_on_download)


def _on_download(request: QWebEngineDownloadRequest) -> None:
    name = request.suggestedFileName() or request.downloadFileName() or "下載檔案"
    folder = Path.home() / "Downloads"
    folder.mkdir(parents=True, exist_ok=True)
    parent = QApplication.activeWindow()
    chosen, _ = QFileDialog.getSaveFileName(parent, "儲存檔案", str(folder / name))
    if not chosen:
        request.cancel()
        return
    dest = Path(chosen)
    request.setDownloadDirectory(str(dest.parent))
    request.setDownloadFileName(dest.name)
    request.accept()

    def on_state(state) -> None:
        window = QApplication.activeWindow()
        tab = window.current_tab() if window is not None and hasattr(window, "current_tab") else None
        if tab is None:
            return
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            tab.set_status(f"已下載 {dest.name}")
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            tab.set_status("下載中斷")
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInProgress:
            tab.set_status(f"下載中 {dest.name}")

    request.stateChanged.connect(on_state)


def configure_page(page, host, on_fullscreen) -> None:
    page.fullScreenRequested.connect(lambda request: _fullscreen(request, on_fullscreen))
    page.permissionRequested.connect(lambda permission: _permission(host, permission))

    def on_crash(*_args) -> None:
        host.set_status("這個分頁停止回應，請重新載入")

    page.renderProcessTerminated.connect(on_crash)


def _fullscreen(request, on_fullscreen) -> None:
    enabled = request.toggleOn()
    request.accept()
    on_fullscreen(enabled)


def _permission(host, permission) -> None:
    if not permission.isValid():
        return
    kind = permission.permissionType().name
    action = PERMISSIONS.get(kind, "使用一項瀏覽器權限")
    origin = permission.origin().host() or permission.origin().toString()
    parent = host.window() if host is not None else None
    answer = QMessageBox.question(
        parent,
        "網站權限",
        f"{origin} 想要{action}。要允許嗎？",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer == QMessageBox.StandardButton.Yes:
        permission.grant()
    else:
        permission.deny()
