from __future__ import annotations

from ui_test_platform.orchestrator.context import compress_traces, build_replan_context


def test_compress_traces_limits_history():
    traces = [{"step_id": f"s{i}", "action": "click", "status": "success"} for i in range(10)]
    compressed = compress_traces(traces, last_n=3)
    assert len(compressed) == 3
    assert compressed[0]["step_id"] == "s7"


def test_build_replan_context_includes_remaining_steps():
    state = {
        "plan": {
            "task": "删除用户",
            "intents": [],
            "steps": [
                {"action": "open", "url": "https://x/users"},
                {"action": "click", "target": "删除"},
            ],
        },
        "current_step_index": 1,
        "traces": [],
        "error": "fail",
    }
    ctx = build_replan_context(state)
    assert len(ctx["remaining_steps"]) == 1
    assert ctx["remaining_steps"][0]["action"] == "click"
