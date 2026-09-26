from guardrails.allowlist import is_allowed, MAX_AUTO_RETRIES
from guardrails.risk_classifier import assess_risk


def test_retry_allowed_for_upstream_timeout_first_attempt():
    assert is_allowed("upstream_timeout", "retry", try_number=1) is True

def test_retry_not_allowed_for_schema_drift():
    # retry is only in the allow-list for upstream_timeout, not schema_drift
    assert is_allowed("schema_drift", "retry", try_number=1) is False

def test_retry_blocked_after_max_auto_retries():
    assert is_allowed("upstream_timeout", "retry", try_number=MAX_AUTO_RETRIES + 1) is False

def test_escalate_never_auto_allowed():
    assert is_allowed("upstream_timeout", "escalate", try_number=1) is False

def test_risk_of_retry_is_low():
    assert assess_risk("retry") == "low"

def test_risk_of_unknown_action_defaults_high():
    assert assess_risk("some_new_action_type") == "high"