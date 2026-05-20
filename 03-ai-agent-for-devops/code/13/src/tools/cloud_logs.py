"""
Multi-source log tools.

Wraps the connectors in src/sources/ as LangChain tools that the agent
can call directly. Each tool fetches logs from one source, normalises
them into LogEntry records, and returns a formatted text block.
"""
from langchain_core.tools import tool

from ..sources import (
    CloudWatchSource,
    ElasticsearchSource,
    KubernetesSource,
    format_entries,
)


# Singletons — cheap to construct, safe to reuse
_cloudwatch = CloudWatchSource()
_kubernetes = KubernetesSource()
_elasticsearch = ElasticsearchSource()


@tool
def fetch_cloudwatch_logs(
    log_group: str,
    query: str = "",
    minutes: int = 15,
    limit: int = 50,
) -> str:
    """
    Fetch recent CloudWatch Logs from an AWS log group.

    Use this for application logs that are shipped to CloudWatch — typically
    EKS pods configured with the CloudWatch agent, Lambda functions, or RDS
    error logs.

    Args:
        log_group: Log group name (e.g. '/aws/eks/orders-prod/application').
        query:     Optional substring to filter on (case-insensitive).
        minutes:   How far back to look (default 15 minutes).
        limit:     Maximum entries to return (default 50).

    Returns:
        Formatted text block of matching log entries, newest last.
    """
    entries = _cloudwatch.fetch(log_group, query or None, minutes, limit)
    header = (
        f"CloudWatch log group: {log_group} "
        f"(last {minutes}m, query={query or 'none'})"
    )
    return format_entries(entries, header)


@tool
def fetch_kubernetes_pod_logs(
    pod_name: str,
    query: str = "",
    minutes: int = 15,
    limit: int = 100,
) -> str:
    """
    Fetch recent logs from a Kubernetes pod.

    Reads stdout/stderr via the Kubernetes API. Uses the default namespace
    from K8S_DEFAULT_NAMESPACE.

    Args:
        pod_name: Pod name (e.g. 'backend-orders-7d4f8b9c5-x2k9p').
        query:    Optional substring filter (case-insensitive).
        minutes:  How far back to look (default 15 minutes).
        limit:    Maximum entries to return (default 100).

    Returns:
        Formatted text block of matching log entries, newest last.
    """
    entries = _kubernetes.fetch(pod_name, query or None, minutes, limit)
    header = (
        f"Kubernetes pod: {pod_name} "
        f"(ns={_kubernetes.namespace}, last {minutes}m, query={query or 'none'})"
    )
    return format_entries(entries, header)


@tool
def search_elasticsearch(
    index: str,
    query: str = "",
    minutes: int = 15,
    limit: int = 50,
) -> str:
    """
    Search an Elasticsearch index for recent log entries.

    Use for centralised application logs indexed in Elasticsearch
    (or OpenSearch). The query is passed through as a query_string
    against the 'message' field.

    Args:
        index:   Index name or pattern (e.g. 'app-logs-*').
        query:   Elasticsearch query_string (e.g. 'level:ERROR AND db').
        minutes: How far back to look.
        limit:   Maximum hits to return.

    Returns:
        Formatted text block of matching log entries, newest last.
    """
    entries = _elasticsearch.fetch(index, query or None, minutes, limit)
    header = (
        f"Elasticsearch index: {index} "
        f"(last {minutes}m, query={query or 'none'})"
    )
    return format_entries(entries, header)


@tool
def list_log_sources() -> str:
    """
    List which log sources are currently configured.

    Shows whether CloudWatch, Kubernetes, and Elasticsearch are connected
    to real backends or running in placeholder mode. Call this first when
    you're unsure which sources are available.
    """
    rows = []
    for src in (_cloudwatch, _kubernetes, _elasticsearch):
        status = "configured" if src.is_configured() else "placeholder mode"
        rows.append(f"- {src.name}: {status}")
    return "Available log sources:\n" + "\n".join(rows)


def get_cloud_log_tools() -> list:
    """Return the multi-source log tools."""
    return [
        list_log_sources,
        fetch_cloudwatch_logs,
        fetch_kubernetes_pod_logs,
        search_elasticsearch,
    ]
