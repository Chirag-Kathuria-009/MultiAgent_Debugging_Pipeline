import pytest

from agents.report import _build_summary, _safe_filename, report_agent


def make_state(**overrides):
    state = {
        "agent_log": [],
        "failure_context": {
            "dag_id": "upstream_timeout_pipeline",
            "task_id": "call_flaky_upstream",
            "run_id": "manual__2026-09-13T16:42:49.421584+00:00",
            "try_number": 1,
            "exception": "Upstream service timeout",
        },
        "triage_category": "upstream_timeout",
        "triage_justification": "matches known transient timeout pattern",
        "investigation_findings": "log confirms a 30s timeout on first attempt",
        "proposed_action": "retry: transient timeout, safe to retry",
        "risk_level": "low",
        "auto_executed": False,
        "approval_status": "pending",
    }
    state.update(overrides)
    return state


# --- _safe_filename ---

def test_safe_filename_leaves_alnum_untouched():
    assert _safe_filename("upstream_timeout_pipeline") == "upstream_timeout_pipeline"

def test_safe_filename_replaces_colons_and_plus():
    dirty = "manual__2026-09-13T16:42:49.421584+00:00"
    clean = _safe_filename(dirty)
    assert ":" not in clean
    assert "+" not in clean

def test_safe_filename_defaults_to_unknown_for_empty_input():
    assert _safe_filename("") == "unknown"
    assert _safe_filename(None) == "unknown"


# --- _build_summary ---

def test_summary_reports_auto_executed_outcome():
    state = make_state(auto_executed=True, approval_status="not_required")
    assert "Auto-remediated" in _build_summary(state)

def test_summary_reports_approved_outcome():
    state = make_state(auto_executed=False, approval_status="approved")
    assert "Remediated after human approval." in _build_summary(state)

def test_summary_reports_rejected_outcome():
    state = make_state(auto_executed=False, approval_status="rejected")
    assert "Rejected by human reviewer" in _build_summary(state)

def test_summary_reports_pending_outcome_by_default():
    state = make_state(auto_executed=False, approval_status="pending")
    assert "Pending human approval." in _build_summary(state)

def test_summary_includes_dag_and_task_identifiers():
    summary = _build_summary(make_state())
    assert "upstream_timeout_pipeline" in summary
    assert "call_flaky_upstream" in summary

def test_summary_handles_missing_failure_context_gracefully():
    summary = _build_summary(make_state(failure_context={}))
    assert "unknown_dag" in summary


# --- report_agent (writes to disk) ---

def test_report_agent_writes_file_and_returns_summary(tmp_path, monkeypatch):
    monkeypatch.setattr("agents.report.REPORTS_DIR", str(tmp_path))

    result = report_agent(make_state())

    assert "incident_summary" in result
    written_files = list(tmp_path.iterdir())
    assert len(written_files) == 1
    assert written_files[0].read_text(encoding="utf-8") == result["incident_summary"]

def test_report_agent_appends_to_agent_log(tmp_path, monkeypatch):
    monkeypatch.setattr("agents.report.REPORTS_DIR", str(tmp_path))

    result = report_agent(make_state())

    assert any("incident report written to" in line for line in result["agent_log"])