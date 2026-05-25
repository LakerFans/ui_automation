from __future__ import annotations

from typing import Any


def compress_snapshot_summary(summary: dict | None, max_refs: int = 10) -> dict | None:
    if not summary:
        return None
    refs = summary.get("refs", [])
    return {
        "url": summary.get("url"),
        "title": summary.get("title"),
        "ref_count": summary.get("ref_count", len(refs)),
        "refs": refs[:max_refs],
        "has_iframe": summary.get("has_iframe", False),
    }


def compress_traces(traces: list[dict[str, Any]], last_n: int = 5) -> list[dict[str, Any]]:
    """Structured trace compression for replanning context."""
    compressed = []
    for t in traces[-last_n:]:
        compressed.append(
            {
                "step_id": t.get("step_id"),
                "action": t.get("action"),
                "target": t.get("target"),
                "status": t.get("status"),
                "error": t.get("error"),
                "resolved_ref": t.get("resolved_ref"),
                "confidence": t.get("confidence"),
                "snapshot_summary": compress_snapshot_summary(t.get("snapshot_summary")),
            }
        )
    return compressed


def build_replan_context(state: dict[str, Any]) -> dict[str, Any]:
    """Orchestrator-level context bundle for Planner replan."""
    plan = state.get("plan") or {}
    idx = state.get("current_step_index", 0)
    steps = plan.get("steps", [])
    return {
        "task": plan.get("task"),
        "intents": plan.get("intents", []),
        "remaining_steps": steps[idx:],
        "error": state.get("error"),
        "trace_summary": compress_traces(state.get("traces", [])),
        "last_snapshot": state.get("last_snapshot_summary"),
    }
