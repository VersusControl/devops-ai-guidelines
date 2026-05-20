"""
Cross-source correlation tools.

Three @tool functions that turn the analysis package into capabilities
the agent can invoke:

- fetch_all_logs       -- merged chronological view of every source
- build_incident_timeline -- correlated timeline with cross-source clusters
- find_correlated_events  -- events near a specific anchor across sources
"""
from langchain_core.tools import tool

from ..analysis import LogAggregator, Correlator, build_timeline
from ..sources import format_entries


# Shared instances. Aggregator is stateless aside from configuration;
# correlator is created per-call so window_seconds can vary.
_aggregator = LogAggregator()


@tool
def fetch_all_logs(
    query: str = "",
    minutes: int = 30,
    limit_per_source: int = 50,
) -> str:
    """
    Pull logs from every configured source in parallel and return a single
    chronological list.

    Use this when you want one merged view of what happened across all
    systems -- without having to call each source separately.

    Args:
        query:            Optional substring/query passed to every source.
        minutes:          Time window (default 30 minutes).
        limit_per_source: Max entries per source (default 50).

    Returns:
        Formatted text block of all entries sorted oldest-first.
    """
    entries = _aggregator.fetch(query, minutes, limit_per_source)
    header = (
        f"Merged log timeline (last {minutes}m, query={query or 'none'}, "
        f"limit_per_source={limit_per_source})"
    )
    return format_entries(entries, header)


@tool
def build_incident_timeline(
    query: str = "",
    minutes: int = 30,
    window_seconds: int = 60,
    limit_per_source: int = 50,
) -> str:
    """
    Build a correlated timeline that highlights events happening across
    multiple sources within the same time window.

    Use this to find the moments where systems were failing together --
    the strongest signal for cross-system incidents. Cross-source clusters
    are expanded fully; single-source clusters are compressed to a summary
    so the agent can focus on the correlations.

    Args:
        query:            Optional substring passed to every source.
        minutes:          Time window (default 30 minutes).
        window_seconds:   How close two events must be to count as one cluster
                          (default 60 seconds).
        limit_per_source: Max entries per source (default 50).

    Returns:
        Text timeline with cross-source clusters marked.
    """
    entries = _aggregator.fetch(query, minutes, limit_per_source)
    return build_timeline(entries, window_seconds=window_seconds)


@tool
def find_correlated_events(
    anchor_text: str,
    window_seconds: int = 120,
    minutes: int = 30,
    limit_per_source: int = 50,
) -> str:
    """
    Find events from any source that happened close in time to a specific
    log line.

    Use this when you've already found a suspicious entry (an error, a
    deployment marker, a circuit-breaker trip) and want to know what else
    was happening in the rest of the stack at the same moment.

    Args:
        anchor_text:      Substring used to identify the anchor entry.
                          The first matching entry is the anchor; events
                          within +/- window_seconds of it are returned.
        window_seconds:   Half-width of the time window (default 120s).
        minutes:          How far back to pull entries (default 30 minutes).
        limit_per_source: Max entries per source (default 50).

    Returns:
        Text block listing the anchor and surrounding events.
    """
    entries = _aggregator.fetch("", minutes, limit_per_source)
    if not entries:
        return "No log entries available to correlate."

    needle = anchor_text.lower()
    anchor = next((e for e in entries if needle in e.message.lower()), None)
    if anchor is None:
        return f"No anchor entry matching '{anchor_text}' in the last {minutes}m."

    correlator = Correlator(window_seconds=window_seconds)
    nearby = correlator.around(entries, anchor)

    lines = [
        f"Anchor: {anchor.short()}",
        f"Window: +/- {window_seconds}s",
        f"Surrounding events: {len(nearby)}",
        "",
    ]
    for e in sorted(nearby, key=lambda x: x.timestamp):
        lines.append(f"  {e.short()}")
    return "\n".join(lines)


def get_correlation_tools() -> list:
    """Return the correlation tools."""
    return [
        fetch_all_logs,
        build_incident_timeline,
        find_correlated_events,
    ]
