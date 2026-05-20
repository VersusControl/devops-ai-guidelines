"""
Log aggregator.

Fetches logs from every configured source in parallel and returns one
chronologically-sorted list of LogEntry records.

The aggregator does not interpret the logs -- it just hands the LLM a
unified timeline to reason about.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from ..config import Config
from ..sources import (
    CloudWatchSource,
    ElasticsearchSource,
    KubernetesSource,
    LogEntry,
    LogSource,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------
class LogAggregator:
    """
    Pulls logs from multiple sources in parallel and merges them.

    Each source is given the same query and time window. The aggregator
    returns one list sorted by timestamp ascending (oldest first), which
    is what the agent expects for chronological reasoning.
    """

    def __init__(self, sources: Optional[list[tuple[LogSource, str]]] = None):
        # Each entry is (source, default_target). The default target tells
        # the source what to query when the caller does not specify one --
        # log group name for CloudWatch, index for Elasticsearch, etc.
        if sources is None:
            self.sources = [
                (CloudWatchSource(),    Config.CLOUDWATCH_DEFAULT_LOG_GROUP),
                (ElasticsearchSource(), Config.ELASTICSEARCH_DEFAULT_INDEX),
                # Kubernetes is intentionally excluded by default -- it
                # needs a specific pod name, not a sensible cluster-wide
                # default. Callers add it explicitly when relevant.
            ]
        else:
            self.sources = sources

    # ------------------------------------------------------------------
    def fetch(
        self,
        query: str = "",
        minutes: int = 30,
        limit_per_source: int = 50,
        targets: Optional[dict[str, str]] = None,
    ) -> list[LogEntry]:
        """
        Fetch logs from every configured source in parallel.

        Args:
            query:            Optional substring/query passed to every source.
            minutes:          Time window for every source.
            limit_per_source: Max entries pulled from each source.
            targets:          Optional override map {source_name: target}.
                              Lets callers point an ES query at a different
                              index, or add a Kubernetes pod ad-hoc.

        Returns:
            Single list sorted by timestamp ascending (oldest first).
        """
        targets = targets or {}
        jobs: list[tuple[LogSource, str]] = []
        for src, default_target in self.sources:
            target = targets.get(src.name, default_target)
            if not target:
                continue
            jobs.append((src, target))

        entries: list[LogEntry] = []
        if not jobs:
            return entries

        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {
                pool.submit(_safe_fetch, src, target, query or None, minutes, limit_per_source):
                    (src.name, target)
                for src, target in jobs
            }
            for fut in as_completed(futures):
                name, target = futures[fut]
                try:
                    entries.extend(fut.result())
                except Exception as e:                                  # noqa: BLE001
                    logger.warning("Aggregator: %s/%s failed: %s", name, target, e)

        entries.sort(key=lambda e: e.timestamp)
        return entries


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------
def fetch_all(
    query: str = "",
    minutes: int = 30,
    limit_per_source: int = 50,
    targets: Optional[dict[str, str]] = None,
) -> list[LogEntry]:
    """Shortcut for callers that don't need their own aggregator instance."""
    return LogAggregator().fetch(query, minutes, limit_per_source, targets)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_fetch(
    source: LogSource,
    target: str,
    query: Optional[str],
    minutes: int,
    limit: int,
) -> list[LogEntry]:
    """
    Wrapper that converts source errors into empty lists.

    We don't want one slow/broken source to break the whole timeline.
    The source-level fetch already falls back to placeholder data on
    most failures; this is the last line of defence.
    """
    try:
        return source.fetch(target, query, minutes, limit)
    except Exception as e:                                              # noqa: BLE001
        logger.warning("Source %s failed: %s", source.name, e)
        return []
