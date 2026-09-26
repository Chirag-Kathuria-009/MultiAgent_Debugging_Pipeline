from unittest.mock import patch
from agents.remediate import remediate_agent, RemediationProposal

def make_state(triage_category="upstream_timeout", try_number=1):
    return {
        "agent_log": [],
        "failure_context": {"dag_id": "d", "task_id": "t", "run_id": "r", "try_number": try_number},
        "triage_category": triage_category,
        "investigation_findings": "upstream timed out",
    }

@patch("agents.remediate.clear_task_instance", return_value="cleared task instance")
@patch("agents.remediate.get_remediation_llm")
def test_allowed_retry_auto_executes(mock_llm, mock_clear):
    mock_llm.return_value.invoke.return_value = RemediationProposal(
        action_type="retry", action_description="transient timeout"
    )
    result = remediate_agent(make_state())
    assert result["auto_executed"] is True
    mock_clear.assert_called_once()

@patch("agents.remediate.clear_task_instance")
@patch("agents.remediate.get_remediation_llm")
def test_escalate_never_calls_airflow(mock_llm, mock_clear):
    mock_llm.return_value.invoke.return_value = RemediationProposal(
        action_type="escalate", action_description="schema changed, needs human"
    )
    result = remediate_agent(make_state(triage_category="schema_drift"))
    assert result["auto_executed"] is False
    mock_clear.assert_not_called()