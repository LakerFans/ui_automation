from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ReporterAgent:
    def build_report(
        self,
        *,
        run_id: str,
        task: str,
        verdict: str,
        traces: list[dict[str, Any]],
        error: str | None = None,
        ast: dict | None = None,
    ) -> dict[str, Any]:
        started = traces[0].get("started_at") if traces else None
        ended = datetime.now(timezone.utc).isoformat()
        total_ms = sum(t.get("duration_ms", 0) for t in traces)
        failed = next((t for t in traces if t.get("status") in ("fail", "blocked")), None)

        return {
            "run_id": run_id,
            "case_name": task,
            "verdict": verdict,
            "status": "success" if verdict == "success" else "fail",
            "duration_ms": total_ms,
            "started_at": started,
            "ended_at": ended,
            "steps": traces,
            "failure": {
                "step_id": failed.get("step_id") if failed else None,
                "error": error or (failed.get("error") if failed else None),
                "detail": failed,
            },
            "ast": ast,
            "screenshots": [t.get("screenshot_path") for t in traces if t.get("screenshot_path")],
            "console_logs": [t.get("console_logs") for t in traces if t.get("console_logs")],
        }
