"""
Correlator.

Groups log entries into time-window clusters and identifies clusters that
span multiple sources. These cross-source clusters are the events most
worth investigating: the moment when "something happened" in more than
one system at the same time.

The correlator is intentionally simple. It does not score, rank, or
infer causality -- it just builds the timeline that lets the LLM do that
reasoning in the prompt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from ..sources import LogEntry


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@dataclass
class Cluster:
    """A group of entries that happened within a time window."""
    start: datetime
    end: datetime
    entries: list[LogEntry] = field(default_factory=list)

    @property
    def sources(self) -> set[str]:
        return {e.source for e in self.entries}

    @property
    def services(self) -> set[str]:
        return {e.service for e in self.entries}

    @property
    def is_cross_source(self) -> bool:
        return len(self.sources) >= 2

    @property
    def has_errors(self) -> bool:
        return any(e.level in ("ERROR", "FATAL") for e in self.entries)

    def level_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self.entries:
            counts[e.level] = counts.get(e.level, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Correlator
# ---------------------------------------------------------------------------
class Correlator:
    """Bucket entries into time-window clusters."""

    def __init__(self, window_seconds: int = 60):
        self.window = timedelta(seconds=window_seconds)

    # ------------------------------------------------------------------
    def cluster(self, entries: list[LogEntry]) -> list[Cluster]:
        """
        Greedy time-window clustering.

        Walk entries in chronological order. Start a new cluster every
        time the gap from the previous entry exceeds the window.
        """
        if not entries:
            return []

        ordered = sorted(entries, key=lambda e: e.timestamp)
        clusters: list[Cluster] = []
        current = Cluster(start=ordered[0].timestamp, end=ordered[0].timestamp)
        current.entries.append(ordered[0])

        for entry in ordered[1:]:
            if entry.timestamp - current.end <= self.window:
                current.entries.append(entry)
                current.end = entry.timestamp
            else:
                clusters.append(current)
                current = Cluster(start=entry.timestamp, end=entry.timestamp)
                current.entries.append(entry)

        clusters.append(current)
        return clusters

    # ------------------------------------------------------------------
    def cross_source(self, entries: list[LogEntry]) -> list[Cluster]:
        """Return only clusters that touch more than one source."""
        return [c for c in self.cluster(entries) if c.is_cross_source]

    # ------------------------------------------------------------------
    def around(
        self,
        entries: list[LogEntry],
        anchor: LogEntry,
        window_seconds: Optional[int] = None,
    ) -> list[LogEntry]:
        """
        Return all entries within `window_seconds` of an anchor entry.

        Used to answer "what else was happening at the same time as this
        specific error?".
        """
        delta = timedelta(seconds=window_seconds) if window_seconds else self.window
        lo, hi = anchor.timestamp - delta, anchor.timestamp + delta
        return [
            e for e in entries
            if lo <= e.timestamp <= hi and e is not anchor
        ]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def build_timeline(
    entries: list[LogEntry],
    window_seconds: int = 60,
    highlight_cross_source: bool = True,
) -> str:
    """
    Render a chronological text timeline with cross-source clusters marked.

    Format:

        TIMELINE (last 30m, 47 entries across 3 sources)

        --- 14:30:55 - 14:31:08 (cross-source: cloudwatch + kubernetes, 6 entries, ERROR=4) ---
        [14:30:55] [kubernetes/backend-orders-7d4f8b9c5] WARN: Connection acquisition took 2.3s
        [14:31:01] [kubernetes/backend-orders-7d4f8b9c5] ERROR: HikariPool-1 ...
        [14:31:02] [cloudwatch/orders-prod]              ERROR: Connection is not available
        ...

        --- 14:33:10 (single-source: kubernetes, 1 entry) ---
        [14:33:10] [kubernetes/backend-orders] INFO: Health check OK
    """
    if not entries:
        return "(no log entries to correlate)"

    correlator = Correlator(window_seconds=window_seconds)
    clusters = correlator.cluster(entries)

    sources = sorted({e.source for e in entries})
    header = (
        f"TIMELINE ({len(entries)} entries across "
        f"{len(sources)} source{'s' if len(sources) != 1 else ''}: {', '.join(sources)})"
    )

    lines: list[str] = [header, ""]
    for c in clusters:
        kind = "cross-source" if c.is_cross_source else "single-source"
        if highlight_cross_source and not c.is_cross_source:
            # Compress single-source clusters: show count + first/last entry
            lines.append(_cluster_header(c, kind))
            lines.append(f"  {c.entries[0].short()}")
            if len(c.entries) > 2:
                lines.append(f"  ... ({len(c.entries) - 2} more entries)")
            if len(c.entries) > 1:
                lines.append(f"  {c.entries[-1].short()}")
            lines.append("")
            continue

        lines.append(_cluster_header(c, kind))
        for e in c.entries:
            lines.append(f"  {e.short()}")
        lines.append("")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _cluster_header(c: Cluster, kind: str) -> str:
    start = c.start.strftime("%H:%M:%S")
    end = c.end.strftime("%H:%M:%S")
    span = start if start == end else f"{start} - {end}"
    counts = c.level_counts()
    levels = " ".join(f"{lvl}={n}" for lvl, n in sorted(counts.items()))
    sources = "+".join(sorted(c.sources))
    return (
        f"--- {span} ({kind}: {sources}, "
        f"{len(c.entries)} entr{'ies' if len(c.entries) != 1 else 'y'}, {levels}) ---"
    )
