"""
Deterministic allow-list deciding which (triage_category, action_type)
pairs may auto-execute without human approval. Plain Python logic, not an
LLM call — the entire point of Phase 5 is that this boundary cannot
hallucinate, so it must not be probabilistic.
 
Deliberately narrow: only upstream_timeout + retry is allowed right now.
Everything else — including any category or action this list has simply
never heard of — is rejected by default.

 """
 
ALLOWED_AUTO_ACTIONS = {
    ("upstream_timeout", "retry"),
}

MAX_AUTO_RETRIES = 5

def is_allowed(triage_category: str, action_type: str, try_number: int) -> bool:
    """
    Check if the given (triage_category, action_type) pair is allowed for
    automatic execution without human approval.
    """
    return (triage_category, action_type) in ALLOWED_AUTO_ACTIONS and try_number <= MAX_AUTO_RETRIES