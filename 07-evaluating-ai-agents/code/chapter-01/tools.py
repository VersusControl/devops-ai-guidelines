"""The four read-only tools our agent uses to investigate an incident.

For now every tool returns canned data for one recorded incident: a latency
spike in checkout-service. Later in the book these same functions get their
data from a recording instead of these hard-coded returns, and the agent won't
be able to tell the difference.
"""


def get_metrics(service):
    """Recent latency and error-rate metrics for a service."""
    return {
        "service": service,
        "window": "14:00-14:10",
        "p95_latency_ms": [420, 430, 450, 1900, 2100, 2200, 2150],
        "error_rate": [0.01, 0.01, 0.02, 0.08, 0.11, 0.12, 0.12],
        "note": "p95 crosses 2s at 14:03, one minute after the 14:02 deploy",
    }


def get_logs(service):
    """A sample of recent log lines for a service."""
    return {
        "service": service,
        "lines": [
            "14:03:01 WARN  db pool: waiting for connection (waiters=12)",
            "14:03:04 WARN  db pool: waiting for connection (waiters=27)",
            "14:03:09 ERROR checkout: timeout acquiring db connection after 2000ms",
            # A coincidence, not the cause. A good diagnosis ignores this line.
            "14:06:12 INFO  payment-provider latency 180ms (was 90ms)",
        ],
    }


def get_deploys(service):
    """Recent deploys for a service, newest first."""
    return {
        "service": service,
        "deploys": [
            {
                "at": "14:02",
                "change": "DB_MAX_CONNECTIONS 50 -> 5",
                "commit": "a1b2c3d",
                "author": "config-bot",
            },
            {
                "at": "09:15",
                "change": "bump checkout image to v1.9.2",
                "commit": "9f8e7d6",
                "author": "release",
            },
        ],
    }


def get_db_status(service):
    """The current database connection-pool status for a service."""
    return {
        "service": service,
        "pool_size": 5,
        "in_use": 5,
        "waiting": 40,
        "note": "pool exhausted: 5 of 5 connections in use, 40 requests queued",
    }
