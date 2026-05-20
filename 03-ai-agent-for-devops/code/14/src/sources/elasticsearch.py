"""
Elasticsearch log source.

Uses the official `elasticsearch` client when ELASTICSEARCH_URL is set;
otherwise returns deterministic placeholder data.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from .base import LogEntry, LogSource


class ElasticsearchSource(LogSource):
    """Elasticsearch source. `target` is the index name (or pattern)."""

    name = "elasticsearch"

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.url = url or os.getenv("ELASTICSEARCH_URL", "")
        self.api_key = api_key or os.getenv("ELASTICSEARCH_API_KEY", "")
        self.username = username or os.getenv("ELASTICSEARCH_USER", "")
        self.password = password or os.getenv("ELASTICSEARCH_PASSWORD", "")

    # ------------------------------------------------------------------
    def is_configured(self) -> bool:
        return bool(self.url)

    # ------------------------------------------------------------------
    def fetch(
        self,
        target: str,
        query: Optional[str] = None,
        minutes: int = 15,
        limit: int = 100,
    ) -> list[LogEntry]:
        if not self.is_configured():
            return self._placeholder(target, query, minutes, limit)
        try:
            return self._fetch_real(target, query, minutes, limit)
        except Exception as e:                                          # noqa: BLE001
            return self._placeholder(
                target, query, minutes, limit,
                note=f"(live call failed: {e}; showing placeholder data)",
            )

    # ------------------------------------------------------------------
    def _fetch_real(
        self,
        index: str,
        query: Optional[str],
        minutes: int,
        limit: int,
    ) -> list[LogEntry]:
        from elasticsearch import Elasticsearch

        kwargs: dict = {"hosts": [self.url]}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        elif self.username and self.password:
            kwargs["basic_auth"] = (self.username, self.password)

        es = Elasticsearch(**kwargs)

        must: list[dict] = [{
            "range": {
                "@timestamp": {"gte": f"now-{minutes}m", "lte": "now"},
            },
        }]
        if query:
            must.append({
                "query_string": {
                    "query": query,
                    "default_field": "message",
                },
            })

        body = {
            "size": limit,
            "sort": [{"@timestamp": "desc"}],
            "query": {"bool": {"must": must}},
        }

        resp = es.search(index=index, body=body)
        hits = resp.get("hits", {}).get("hits", [])

        entries: list[LogEntry] = []
        for hit in hits:
            src = hit.get("_source", {})
            ts_str = src.get("@timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                ts = datetime.now(timezone.utc)
            message = (
                src.get("message")
                or src.get("msg")
                or src.get("log", "")
            )
            level = (src.get("level") or src.get("severity") or "UNKNOWN").upper()
            entries.append(LogEntry(
                timestamp=ts,
                source=self.name,
                service=src.get("service", index),
                level=level,
                message=str(message)[:300],
                raw=str(message)[:1000],
                metadata={"index": index, "doc_id": hit.get("_id")},
            ))
        entries.reverse()
        return entries

    # ------------------------------------------------------------------
    def _placeholder(
        self,
        index: str,
        query: Optional[str],
        minutes: int,
        limit: int,
        note: str = "",
    ) -> list[LogEntry]:
        now = datetime.now(timezone.utc)
        samples = [
            ("INFO",  "frontend",        "GET /api/orders 200 124ms"),
            ("INFO",  "frontend",        "GET /api/orders 200 132ms"),
            ("WARN",  "frontend",        "Slow response from backend: 2412ms"),
            ("ERROR", "frontend",        "GET /api/orders 503 30021ms"),
            ("ERROR", "backend-orders",  "Database connection failed after 3 retries"),
            ("INFO",  "redis-cache",     "EVICTED 412 keys due to maxmemory policy"),
        ]
        if query:
            q = query.lower()
            filtered = [s for s in samples if q in s[1].lower() or q in s[2].lower()]
            samples = filtered or samples

        entries: list[LogEntry] = []
        for i, (lvl, service, msg) in enumerate(samples[:limit]):
            entries.append(LogEntry(
                timestamp=now - timedelta(minutes=minutes - i),
                source=self.name,
                service=service,
                level=lvl,
                message=msg,
                raw=msg,
                metadata={
                    "index": index,
                    "placeholder": True,
                    **({"note": note} if note else {}),
                },
            ))
        return entries
