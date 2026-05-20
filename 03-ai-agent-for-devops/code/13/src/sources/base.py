"""
Base types for log sources.

LogEntry is the unified format every connector normalises into.
LogSource is the abstract base each connector implements.
format_entries renders a list of entries as text the LLM can read.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Unified log entry
# ---------------------------------------------------------------------------
@dataclass
class LogEntry:
    """
    A single normalised log line.

    Every connector converts its raw records into this shape so the agent
    sees the same structure regardless of where the log came from.
    """
    timestamp: datetime
    source: str                       # "cloudwatch" | "kubernetes" | "elasticsearch"
    service: str                      # log group / pod / index
    level: str                        # INFO | WARN | ERROR | UNKNOWN
    message: str                      # human-readable line
    raw: str = ""                     # original line/document (truncated)
    metadata: dict = field(default_factory=dict)

    def short(self) -> str:
        """One-line representation for prompt injection."""
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{ts}] [{self.source}/{self.service}] {self.level}: {self.message}"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------
class LogSource(ABC):
    """Abstract base for any log source connector."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if real credentials are available."""

    @abstractmethod
    def fetch(
        self,
        target: str,
        query: Optional[str] = None,
        minutes: int = 15,
        limit: int = 100,
    ) -> list[LogEntry]:
        """
        Fetch logs from this source.

        Args:
            target:  log group / pod name / index — interpretation is source-specific
            query:   optional substring or query language filter
            minutes: how far back to look
            limit:   maximum entries to return

        Returns:
            list of LogEntry, newest last.
        """


# ---------------------------------------------------------------------------
# Rendering helper
# ---------------------------------------------------------------------------
def format_entries(entries: list[LogEntry], header: str = "") -> str:
    """Render entries as a clean text block for the agent."""
    if not entries:
        return f"{header}\n(no matching log entries)" if header else "(no matching log entries)"

    lines: list[str] = []
    if header:
        lines.append(header)
        lines.append("")

    # Count by level so the agent gets a quick summary
    counts: dict[str, int] = {}
    for e in entries:
        counts[e.level] = counts.get(e.level, 0) + 1
    summary = " ".join(f"{lvl}={n}" for lvl, n in sorted(counts.items()))
    lines.append(f"{len(entries)} entries ({summary})")
    lines.append("")

    for e in entries:
        lines.append(e.short())

    return "\n".join(lines)
