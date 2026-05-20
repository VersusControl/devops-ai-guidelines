"""
Log source connectors for the AI agent.

Each connector fetches logs from a real backend (CloudWatch, Kubernetes,
Elasticsearch) and returns a list of normalised LogEntry records.
Connectors fall back to placeholder mode when credentials are missing
so the agent can be demonstrated end-to-end without real infrastructure.
"""
from .base import LogEntry, LogSource, format_entries
from .cloudwatch import CloudWatchSource
from .kubernetes import KubernetesSource
from .elasticsearch import ElasticsearchSource

__all__ = [
    "LogEntry",
    "LogSource",
    "format_entries",
    "CloudWatchSource",
    "KubernetesSource",
    "ElasticsearchSource",
]
