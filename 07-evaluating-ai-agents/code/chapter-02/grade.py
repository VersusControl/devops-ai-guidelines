"""grade.py — score a Conclusion against an AnswerKey.

The first, smallest grade: does the agent's category match the truth? Not enough
on its own — Chapter 6 adds evidence, the distraction, and step count — but it is
the first time "was it right?" has an answer instead of a shrug.
"""


def grade(conclusion, answer):
    category_match = conclusion.category == answer.true_category
    return {
        "category_match": category_match,
        "score": 1.0 if category_match else 0.0,
    }
