from agents.graph import route_after_remediate

def test_routes_to_report_when_auto_executed():
    assert route_after_remediate({"auto_executed": True}) == "auto_executed"

def test_routes_to_approval_when_not_auto_executed():
    assert route_after_remediate({"auto_executed": False}) == "needs_approval"