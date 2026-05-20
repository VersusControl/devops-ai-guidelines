"""
Chat Store — Persist conversation history to a JSON file.

Saves and loads the full message list so conversations survive
page refreshes and application restarts.
"""
import json
from pathlib import Path
from datetime import datetime


class ChatStore:
    """
    File-backed conversation store.

    Each session is saved as a JSON file containing the message list.
    Messages are the same dicts used by Streamlit session_state:
        {"role": "user"|"assistant", "content": str, "steps": [...]}
    """

    def __init__(self, storage_dir: str, session_id: str = "default"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self._path = self.storage_dir / f"session_{session_id}.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load(self) -> list:
        """Load messages from disk. Returns empty list if no file exists."""
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data.get("messages", [])
        except (json.JSONDecodeError, KeyError):
            return []

    def save(self, messages: list) -> None:
        """Write the full message list to disk."""
        data = {
            "session_id": self.session_id,
            "updated_at": datetime.now().isoformat(),
            "messages": messages,
        }
        self._path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )

    def clear(self) -> None:
        """Delete the session file."""
        if self._path.exists():
            self._path.unlink()

    def list_sessions(self) -> list[str]:
        """Return session IDs for all stored sessions."""
        sessions = []
        for f in sorted(self.storage_dir.glob("session_*.json")):
            sid = f.stem.removeprefix("session_")
            sessions.append(sid)
        return sessions
