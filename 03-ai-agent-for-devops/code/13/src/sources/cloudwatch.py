"""
AWS CloudWatch Logs connector.

Uses boto3 to query a log group with CloudWatch Logs Insights
when AWS credentials are available; otherwise returns a small
deterministic placeholder so the agent can be demonstrated locally.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from .base import LogEntry, LogSource


# Regex to guess a level from a free-form line
_LEVEL_RE = re.compile(r"\b(ERROR|WARN(?:ING)?|INFO|DEBUG|FATAL)\b", re.IGNORECASE)


def _guess_level(message: str) -> str:
    m = _LEVEL_RE.search(message)
    if not m:
        return "UNKNOWN"
    lvl = m.group(1).upper()
    return "WARN" if lvl == "WARNING" else lvl


class CloudWatchSource(LogSource):
    """CloudWatch Logs source. `target` is the log group name."""

    name = "cloudwatch"

    def __init__(self, region: Optional[str] = None):
        self.region = region or os.getenv("AWS_REGION", "us-east-1")

    # ------------------------------------------------------------------
    def is_configured(self) -> bool:
        return bool(
            os.getenv("AWS_ACCESS_KEY_ID")
            or os.getenv("AWS_PROFILE")
            or os.getenv("AWS_ROLE_ARN")
        )

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
            # Fall back to placeholder if the live call fails — keeps the
            # demo path working even when network/permissions break.
            return self._placeholder(
                target, query, minutes, limit,
                note=f"(live call failed: {e}; showing placeholder data)",
            )

    # ------------------------------------------------------------------
    # Live path
    # ------------------------------------------------------------------
    def _fetch_real(
        self,
        log_group: str,
        query: Optional[str],
        minutes: int,
        limit: int,
    ) -> list[LogEntry]:
        import boto3

        client = boto3.client("logs", region_name=self.region)
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=minutes)

        # Build a simple Insights query
        filter_clause = ""
        if query:
            safe = query.replace('"', '\\"')
            filter_clause = f'| filter @message like "{safe}" '
        insights = (
            f"fields @timestamp, @message "
            f"{filter_clause}"
            f"| sort @timestamp desc | limit {limit}"
        )

        start_resp = client.start_query(
            logGroupName=log_group,
            startTime=int(start.timestamp()),
            endTime=int(end.timestamp()),
            queryString=insights,
        )
        query_id = start_resp["queryId"]

        # Poll for completion (bounded)
        import time
        results = None
        for _ in range(20):
            r = client.get_query_results(queryId=query_id)
            if r["status"] in ("Complete", "Failed", "Cancelled"):
                results = r
                break
            time.sleep(0.5)
        if results is None or results["status"] != "Complete":
            raise RuntimeError(f"CloudWatch query did not complete: {results and results['status']}")

        entries: list[LogEntry] = []
        for row in results["results"]:
            ts_str = next((f["value"] for f in row if f["field"] == "@timestamp"), "")
            msg = next((f["value"] for f in row if f["field"] == "@message"), "")
            try:
                ts = datetime.fromisoformat(ts_str.replace(" ", "T"))
            except ValueError:
                ts = datetime.now(timezone.utc)
            entries.append(LogEntry(
                timestamp=ts,
                source=self.name,
                service=log_group,
                level=_guess_level(msg),
                message=msg.strip()[:300],
                raw=msg[:1000],
            ))
        entries.reverse()  # newest last
        return entries

    # ------------------------------------------------------------------
    # Placeholder path
    # ------------------------------------------------------------------
    def _placeholder(
        self,
        log_group: str,
        query: Optional[str],
        minutes: int,
        limit: int,
        note: str = "",
    ) -> list[LogEntry]:
        now = datetime.now(timezone.utc)
        samples = [
            ("INFO",  "Health check OK"),
            ("INFO",  "Processed 142 orders in last minute"),
            ("WARN",  "Slow query on orders table: 1840ms"),
            ("ERROR", "HikariPool-1 - Connection is not available, request timed out after 30000ms"),
            ("ERROR", "Too many connections: cannot open new connection to orders-db-prod"),
            ("WARN",  "Retrying database connection (attempt 2/3)"),
        ]
        if query:
            samples = [s for s in samples if query.lower() in s[1].lower()] or samples

        entries: list[LogEntry] = []
        for i, (lvl, msg) in enumerate(samples[:limit]):
            entries.append(LogEntry(
                timestamp=now - timedelta(minutes=minutes - i),
                source=self.name,
                service=log_group,
                level=lvl,
                message=msg,
                raw=msg,
                metadata={"placeholder": True, "note": note} if note else {"placeholder": True},
            ))
        return entries
