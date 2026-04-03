"""
Incident Store — Long-term memory for resolved incidents.

Stores structured incident summaries in a single JSON file.
When a new conversation starts, relevant past incidents can be
retrieved and injected into the agent's system prompt so it
has institutional knowledge about recurring problems.
"""
import json
from pathlib import Path
from datetime import datetime


class IncidentStore:
    """
    File-backed incident memory.

    Each incident is a dict with:
        id, timestamp, severity, summary, root_cause,
        affected_systems, resolution, session_id
    """

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.storage_dir / "incidents.json"
        self._incidents: list[dict] = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            return []

    def _save(self) -> None:
        self._path.write_text(
            json.dumps(self._incidents, indent=2, default=str),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add(
        self,
        summary: str,
        severity: str = "P1",
        root_cause: str = "",
        affected_systems: str = "",
        resolution: str = "",
        session_id: str = "",
    ) -> dict:
        """Save a new incident summary and return it."""
        incident = {
            "id": len(self._incidents) + 1,
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "summary": summary,
            "root_cause": root_cause,
            "affected_systems": affected_systems,
            "resolution": resolution,
            "session_id": session_id,
        }
        self._incidents.append(incident)
        self._save()
        return incident

    def get_all(self) -> list[dict]:
        """Return all stored incidents (newest first)."""
        return list(reversed(self._incidents))

    def get_recent(self, n: int = 5) -> list[dict]:
        """Return the N most recent incidents."""
        return list(reversed(self._incidents[-n:]))

    def search(self, query: str) -> list[dict]:
        """
        Simple keyword search across incident fields.
        Returns incidents whose summary, root_cause, or affected_systems
        contain the query string (case-insensitive).
        """
        q = query.lower()
        results = []
        for inc in self._incidents:
            searchable = " ".join([
                inc.get("summary", ""),
                inc.get("root_cause", ""),
                inc.get("affected_systems", ""),
                inc.get("resolution", ""),
            ]).lower()
            if q in searchable:
                results.append(inc)
        return list(reversed(results))

    def count(self) -> int:
        return len(self._incidents)

    def format_for_prompt(self, incidents: list[dict]) -> str:
        """
        Format a list of incidents into a text block suitable for
        injection into the system prompt.
        """
        if not incidents:
            return ""

        lines = ["PAST INCIDENTS (from long-term memory):\n"]
        for inc in incidents:
            lines.append(
                f"- [{inc['severity']}] {inc['summary']} "
                f"({inc['timestamp'][:10]})"
            )
            if inc.get("root_cause"):
                lines.append(f"  Root cause: {inc['root_cause']}")
            if inc.get("resolution"):
                lines.append(f"  Resolution: {inc['resolution']}")
            lines.append("")

        lines.append(
            "Use this history to identify recurring patterns. "
            "If the current issue matches a past incident, reference it."
        )
        return "\n".join(lines)

    def clear(self) -> None:
        """Delete all incidents."""
        self._incidents = []
        self._save()
