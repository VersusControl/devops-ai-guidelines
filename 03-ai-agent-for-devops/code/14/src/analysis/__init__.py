"""
Analysis package for cross-source correlation.

aggregator -- pulls logs from every configured source in parallel and
              merges them into a single chronological timeline.
correlator -- groups entries by time window to surface events that
              happened across multiple systems at the same time.
"""
from .aggregator import LogAggregator, fetch_all
from .correlator import Correlator, Cluster, build_timeline

__all__ = [
    "LogAggregator",
    "fetch_all",
    "Correlator",
    "Cluster",
    "build_timeline",
]
