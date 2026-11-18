"""書籤、瀏覽紀錄與工作階段。存在專案裡的 JSON，不經過網頁引擎。"""

from __future__ import annotations

import json
import time
from pathlib import Path


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.listeners: list = []
        self.data = {
            "bookmarks": [],
            "history": [],
            "session": {"tabs": [], "index": 0},
            "geometry": None,
        }
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(saved, dict):
            self.data.update(saved)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def notify(self) -> None:
        for callback in list(self.listeners):
            callback()

    def bookmarks(self) -> list[dict]:
        return list(self.data.get("bookmarks") or [])

    def history(self) -> list[dict]:
        return list(self.data.get("history") or [])

    def is_bookmarked(self, url: str) -> bool:
        return any(item.get("url") == url for item in self.bookmarks())

    def add_bookmark(self, title: str, url: str) -> None:
        if not url:
            return
        items = [item for item in self.bookmarks() if item.get("url") != url]
        items.insert(0, {"title": title or url, "url": url})
        self.data["bookmarks"] = items
        self.save()
        self.notify()

    def remove_bookmark(self, url: str) -> None:
        self.data["bookmarks"] = [
            item for item in self.bookmarks() if item.get("url") != url
        ]
        self.save()
        self.notify()

    def add_history(self, title: str, url: str) -> None:
        if not url or url.startswith(("about:", "file:", "data:")):
            return
        items = [item for item in self.history() if item.get("url") != url]
        items.insert(
            0,
            {"title": title or url, "url": url, "visited": time.time()},
        )
        self.data["history"] = items[:400]
        self.save()

    def rename_history(self, url: str, title: str) -> None:
        if not url or not title:
            return
        for item in self.data.get("history") or []:
            if item.get("url") == url and item.get("title") != title:
                item["title"] = title
                self.save()
                return

    def clear_history(self) -> None:
        self.data["history"] = []
        self.save()

    def session(self) -> dict:
        session = self.data.get("session") or {}
        return {
            "tabs": list(session.get("tabs") or []),
            "index": int(session.get("index") or 0),
        }

    def set_session(self, tabs: list[str], index: int) -> None:
        self.data["session"] = {"tabs": tabs, "index": index}
        self.save()

    def geometry(self) -> dict | None:
        value = self.data.get("geometry")
        if isinstance(value, dict) and {"x", "y", "w", "h"} <= set(value):
            return value
        return None

    def set_geometry(self, x: int, y: int, w: int, h: int) -> None:
        self.data["geometry"] = {"x": x, "y": y, "w": w, "h": h}
        self.save()
