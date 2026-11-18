"""把網址列文字解讀成要開啟的網址，或是搜尋。"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote_plus

_HOST = re.compile(
    r"^(localhost|(\d{1,3}\.){3}\d{1,3}|\[[0-9a-fA-F:]+\]|[^\s/]+\.[^\s/]+)(:\d+)?$"
)


def interpret(text: str) -> str | None:
    """回傳要開啟的網址。空字串與 about:blank 代表新分頁。"""
    text = text.strip().strip("\"'").replace("\u3000", " ").strip()
    if not text or text.lower() == "about:blank":
        return None
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "file://")):
        return text
    if text.startswith("//"):
        return "https:" + text
    # 本機路徑可能含空白，要先於「有空白就搜尋」判斷。
    if re.match(r"^[a-zA-Z]:[\\/]", text) or text.startswith("\\\\"):
        try:
            return Path(text).as_uri()
        except (OSError, ValueError):
            return None
    if " " in text:
        return _search(text)

    host = text.split("/", 1)[0]
    if _HOST.match(host):
        scheme = "http" if host.startswith(("localhost", "127.")) or re.match(
            r"^(\d{1,3}\.){3}\d{1,3}(:\d+)?$", host
        ) else "https"
        return f"{scheme}://{text}"
    return _search(text)


def _search(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}&hl=zh-TW"
