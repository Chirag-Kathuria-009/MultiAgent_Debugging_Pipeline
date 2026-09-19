"""
Deterministic blast-radius scoring for a proposed action. Same
philosophy as allow_list.py — plain Python, not an LLM judgment call.
Anything not explicitly scored defaults to "high": an unrecognized
action is never assumed safe.
"""

RISK_SCORES = {
    "retry": "low",  # re-running a task touches no data — minimal blast radius
}

def assess_risk(proposed_action: str) -> str:
    """
    Return a risk score for the proposed action. If the action is not
    recognized, return "high" by default.
    """
    return RISK_SCORES.get(proposed_action, "high")