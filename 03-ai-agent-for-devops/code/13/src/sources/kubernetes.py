"""
Kubernetes pod logs connector.

Uses the official `kubernetes` client when kubeconfig is available;
otherwise returns deterministic placeholder data.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from .base import LogEntry, LogSource


_LEVEL_RE = re.compile(r"\b(ERROR|WARN(?:ING)?|INFO|DEBUG|FATAL)\b", re.IGNORECASE)
_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)")


def _guess_level(line: str) -> str:
    m = _LEVEL_RE.search(line)
    if not m:
        return "UNKNOWN"
    lvl = m.group(1).upper()
    return "WARN" if lvl == "WARNING" else lvl


class KubernetesSource(LogSource):
    """Kubernetes pod logs. `target` is the pod name."""

    name = "kubernetes"

    def __init__(
        self,
        namespace: Optional[str] = None,
        kubeconfig: Optional[str] = None,
        context: Optional[str] = None,
    ):
        self.namespace = namespace or os.getenv("K8S_DEFAULT_NAMESPACE", "production")
        self.kubeconfig = kubeconfig or os.getenv("K8S_KUBECONFIG", "")
        self.context = context or os.getenv("K8S_CONTEXT", "")

    # ------------------------------------------------------------------
    def is_configured(self) -> bool:
        if self.kubeconfig and os.path.exists(self.kubeconfig):
            return True
        # Common default location
        default = os.path.expanduser("~/.kube/config")
        return os.path.exists(default)

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
        pod_name: str,
        query: Optional[str],
        minutes: int,
        limit: int,
    ) -> list[LogEntry]:
        from kubernetes import client, config as kube_config

        if self.kubeconfig:
            kube_config.load_kube_config(
                config_file=self.kubeconfig,
                context=self.context or None,
            )
        else:
            kube_config.load_kube_config(context=self.context or None)

        v1 = client.CoreV1Api()
        raw = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=self.namespace,
            since_seconds=minutes * 60,
            tail_lines=limit * 4,   # over-fetch then filter
            timestamps=True,
        )

        entries: list[LogEntry] = []
        for line in raw.splitlines():
            if query and query.lower() not in line.lower():
                continue
            m = _TS_RE.match(line)
            if m:
                ts_str = m.group(1).rstrip("Z")
                try:
                    ts = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
                except ValueError:
                    ts = datetime.now(timezone.utc)
                message = line[m.end():].strip()
            else:
                ts = datetime.now(timezone.utc)
                message = line.strip()

            entries.append(LogEntry(
                timestamp=ts,
                source=self.name,
                service=pod_name,
                level=_guess_level(message),
                message=message[:300],
                raw=line[:1000],
                metadata={"namespace": self.namespace},
            ))
        return entries[-limit:]

    # ------------------------------------------------------------------
    def _placeholder(
        self,
        pod_name: str,
        query: Optional[str],
        minutes: int,
        limit: int,
        note: str = "",
    ) -> list[LogEntry]:
        now = datetime.now(timezone.utc)
        samples = [
            ("INFO",  "Spring Boot started in 8.241 seconds"),
            ("INFO",  "Hikari pool initialised with size=20"),
            ("WARN",  "Connection acquisition took 2.3s"),
            ("ERROR", "java.sql.SQLException: HikariPool-1 - Connection is not available"),
            ("ERROR", "Caused by: com.mysql.cj.jdbc.exceptions.CommunicationsException"),
            ("INFO",  "Returning HTTP 503 for /api/orders"),
        ]
        if query:
            samples = [s for s in samples if query.lower() in s[1].lower()] or samples

        entries: list[LogEntry] = []
        for i, (lvl, msg) in enumerate(samples[:limit]):
            entries.append(LogEntry(
                timestamp=now - timedelta(minutes=minutes - i),
                source=self.name,
                service=pod_name,
                level=lvl,
                message=msg,
                raw=msg,
                metadata={
                    "namespace": self.namespace,
                    "placeholder": True,
                    **({"note": note} if note else {}),
                },
            ))
        return entries
