from __future__ import annotations

from ui_test_platform.graph.workflow import RunWorkflow


def test_login_workflow_success_mock():
    wf = RunWorkflow()
    result = wf.run("管理员登录后台", base_url="https://example.com")
    assert result.get("verdict") == "success"
    assert result.get("report") is not None
    assert len(result.get("traces", [])) >= 4


def test_delete_blocked_without_risk_override():
    wf = RunWorkflow()
    result = wf.run("删除用户数据", base_url="https://example.com")
    assert result.get("verdict") in ("blocked", "fail")
