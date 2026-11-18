import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from location import interpret
from store import Store


def test_interpret() -> None:
    assert interpret("") is None
    assert interpret("   ") is None
    assert interpret("about:blank") is None
    assert interpret("example.com") == "https://example.com"
    assert interpret("example.com/docs") == "https://example.com/docs"
    assert interpret("https://example.com/a") == "https://example.com/a"
    assert interpret("//example.com") == "https://example.com"
    assert interpret("localhost:8000") == "http://localhost:8000"
    assert interpret("localhost:8000/app") == "http://localhost:8000/app"
    assert interpret("127.0.0.1:3000") == "http://127.0.0.1:3000"
    assert interpret("192.168.0.8") == "http://192.168.0.8"
    query = interpret("瀏覽器 教學")
    assert query is not None and query.startswith("https://www.google.com/search?")
    assert "hl=zh-TW" in query
    path = Path(r"C:\temp\a file.html")
    assert interpret(r"C:\temp\a file.html") == path.as_uri()
    assert interpret('"https://example.com"') == "https://example.com"


def test_store() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "library.json"
        store = Store(path)
        store.add_bookmark("例子", "https://example.com")
        assert store.is_bookmarked("https://example.com")
        store.add_bookmark("例子 2", "https://example.com")
        assert len(store.bookmarks()) == 1
        assert store.bookmarks()[0]["title"] == "例子 2"
        store.add_history("Example", "https://example.com")
        store.add_history("Example 2", "https://example.com")
        assert len(store.history()) == 1
        assert store.history()[0]["title"] == "Example 2"
        store.rename_history("https://example.com", "新標題")
        assert store.history()[0]["title"] == "新標題"
        store.set_session(["https://example.com", ""], 1)
        store.set_geometry(10, 20, 800, 600)
        again = Store(path)
        assert again.session() == {"tabs": ["https://example.com", ""], "index": 1}
        assert again.geometry() == {"x": 10, "y": 20, "w": 800, "h": 600}
        again.remove_bookmark("https://example.com")
        assert not again.is_bookmarked("https://example.com")
        again.clear_history()
        assert again.history() == []


if __name__ == "__main__":
    test_interpret()
    test_store()
    print("ok")
