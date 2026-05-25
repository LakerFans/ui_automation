from __future__ import annotations

from typing import Literal, TypedDict


class RunState(TypedDict, total=False):
    run_id: str
    tenant: str
    natural_language: str
    base_url: str
    status: Literal[
        "INIT", "PLAN", "EXECUTE", "ASSERT",
        "RETRY", "RECOVER", "REPORT", "BLOCKED", "END"
    ]
    resolve_status: Literal["ResolvePending", "Resolved", "Ambiguous", "Failed"]
    plan: dict | None
    ast: dict | None
    current_step_index: int
    retry_count: int
    max_retries: int
    clarify_count: int
    last_snapshot_summary: dict | None
    browser_state: dict
    traces: list[dict]
    error: str | None
    verdict: Literal["success", "fail", "blocked"] | None
    report: dict | None
    pending_clarify: dict | None
    risk_override: bool
