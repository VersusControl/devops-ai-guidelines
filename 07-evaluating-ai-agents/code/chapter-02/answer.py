"""answer.py — the answer key for the checkout-service incident.

Deliberately the smallest possible version: just the true category. Chapter 3
grows this into a full recorded scenario with required evidence, a distraction
to reject, and a step budget. For now it only has to answer one question: did
the agent land on the right category?
"""

from dataclasses import dataclass


@dataclass
class AnswerKey:
    """What we already know is true about an incident."""

    true_category: str  # the real root-cause category: deploy, capacity, dependency...


CHECKOUT_INCIDENT_ANSWER = AnswerKey(true_category="deploy")
