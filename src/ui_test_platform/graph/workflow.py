from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from ui_test_platform.agents.executor import ExecutorAgent
from ui_test_platform.agents.planner import PlannerAgent
from ui_test_platform.agents.reporter import ReporterAgent
from ui_test_platform.browser.adapter import create_browser
from ui_test_platform.config import settings
from ui_test_platform.dsl.compiler import DSLCompiler
from ui_test_platform.dsl.models import TestPlan
from ui_test_platform.graph.state import RunState
from ui_test_platform.orchestrator.context import build_replan_context, compress_snapshot_summary
from ui_test_platform.storage.checkpointer import get_checkpointer
from ui_test_platform.storage.minio_client import ArtifactStore


class RunWorkflow:
    def __init__(self) -> None:
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.reporter = ReporterAgent()
        self.compiler = DSLCompiler()
        self.artifacts = ArtifactStore()
        self._memory = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        g = StateGraph(RunState)
        g.add_node("init", self.node_init)
        g.add_node("plan", self.node_plan)
        g.add_node("execute", self.node_execute)
        g.add_node("retry", self.node_retry)
        g.add_node("blocked", self.node_blocked)
        g.add_node("report", self.node_report)

        g.set_entry_point("init")
        g.add_edge("init", "plan")
        g.add_edge("plan", "execute")
        g.add_conditional_edges("execute", self.route_after_execute, {
            "continue": "execute",
            "report": "report",
            "retry": "retry",
            "blocked": "blocked",
        })
        g.add_edge("retry", "plan")
        g.add_edge("blocked", END)
        g.add_edge("report", END)
        checkpointer = get_checkpointer(self._memory)
        return g.compile(checkpointer=checkpointer)

    def node_init(self, state: RunState) -> RunState:
        run_id = state.get("run_id") or str(uuid.uuid4())
        artifacts = settings.artifacts_dir / run_id
        artifacts.mkdir(parents=True, exist_ok=True)
        browser = create_browser(f"run_{run_id}")
        self.executor.bind_browser(browser)
        return {
            **state,
            "run_id": run_id,
            "status": "INIT",
            "current_step_index": 0,
            "retry_count": 0,
            "max_retries": settings.max_retries,
            "clarify_count": 0,
            "traces": [],
            "browser_state": {"session": f"run_{run_id}", "backend": settings.browser_backend},
            "resolve_status": "ResolvePending",
            "tenant": state.get("tenant", "default"),
            "risk_override": state.get("risk_override", False),
        }

    def node_plan(self, state: RunState) -> RunState:
        ctx = build_replan_context(state) if state.get("status") == "RETRY" else None
        plan = self.planner.plan(
            state["natural_language"],
            history=ctx,
            base_url=state.get("base_url", "https://example.com"),
        )
        ast = self.compiler.compile(plan.steps)
        return {
            **state,
            "status": "PLAN",
            "plan": plan.model_dump(),
            "ast": ast.model_dump(),
            "current_step_index": 0 if state.get("status") != "RETRY" else state.get("current_step_index", 0),
        }

    def node_execute(self, state: RunState) -> RunState:
        ast = state.get("ast") or {}
        children = ast.get("children", [])
        idx = state.get("current_step_index", 0)
        if idx >= len(children):
            return {**state, "status": "ASSERT"}

        from ui_test_platform.dsl.compiler import ASTActionNode

        node = ASTActionNode(**children[idx])
        if state.get("risk_override") and node.risk_confirmed is False:
            node = node.model_copy(update={"risk_confirmed": True})

        run_id = state["run_id"]
        step_id = f"s{idx}"
        artifacts_dir = settings.artifacts_dir / run_id
        trace = self.executor.execute_step(
            node,
            run_id=run_id,
            step_id=step_id,
            artifacts_dir=artifacts_dir,
            clarify_count=state.get("clarify_count", 0),
        )
        trace["started_at"] = trace.get("started_at") or datetime.now(timezone.utc).isoformat()
        traces = list(state.get("traces", []))
        traces.append(trace)

        last_snap = trace.get("post_snapshot_summary") or trace.get("snapshot_summary")
        if last_snap:
            last_snap = compress_snapshot_summary(last_snap)

        if trace.get("status") == "clarify":
            return {
                **state,
                "status": "EXECUTE",
                "traces": traces,
                "clarify_count": state.get("clarify_count", 0) + 1,
                "pending_clarify": trace,
                "last_snapshot_summary": last_snap,
                "resolve_status": "Ambiguous",
            }

        if trace.get("status") == "blocked":
            return {
                **state,
                "status": "BLOCKED",
                "traces": traces,
                "error": trace.get("error"),
                "pending_clarify": trace,
                "last_snapshot_summary": last_snap,
                "verdict": "blocked",
            }

        if trace.get("status") != "success":
            return {
                **state,
                "status": "EXECUTE",
                "traces": traces,
                "error": trace.get("error") or trace.get("stderr"),
                "last_snapshot_summary": last_snap,
                "current_step_index": idx,
            }

        self._persist_artifact(run_id, step_id, trace)
        self._write_trace_file(run_id, traces)

        return {
            **state,
            "status": "EXECUTE",
            "traces": traces,
            "error": None,
            "current_step_index": idx + 1,
            "clarify_count": 0,
            "last_snapshot_summary": last_snap,
            "resolve_status": "Resolved",
        }

    def node_retry(self, state: RunState) -> RunState:
        retry = state.get("retry_count", 0) + 1
        if retry > state.get("max_retries", settings.max_retries):
            return {**state, "status": "REPORT", "verdict": "fail"}
        plan = TestPlan(**(state.get("plan") or {"task": "", "steps": []}))
        replanned = self.planner.replan(plan, state.get("current_step_index", 0), state.get("error") or "")
        return {
            **state,
            "status": "RETRY",
            "retry_count": retry,
            "plan": replanned.model_dump(),
            "ast": self.compiler.compile(replanned.steps).model_dump(),
        }

    def node_blocked(self, state: RunState) -> RunState:
        report = self.reporter.build_report(
            run_id=state["run_id"],
            task=(state.get("plan") or {}).get("task", state["natural_language"]),
            verdict="blocked",
            traces=state.get("traces", []),
            error=state.get("error"),
            ast=state.get("ast"),
        )
        self._write_trace_file(state["run_id"], state.get("traces", []), report)
        return {**state, "status": "BLOCKED", "report": report, "verdict": "blocked"}

    def node_report(self, state: RunState) -> RunState:
        traces = state.get("traces", [])
        failed = any(t.get("status") in ("fail", "blocked") for t in traces)
        verdict = "fail" if failed or state.get("error") else "success"
        report = self.reporter.build_report(
            run_id=state["run_id"],
            task=(state.get("plan") or {}).get("task", state["natural_language"]),
            verdict=verdict,
            traces=traces,
            error=state.get("error"),
            ast=state.get("ast"),
        )
        self._write_trace_file(state["run_id"], traces, report)
        return {**state, "status": "END", "report": report, "verdict": verdict}

    def route_after_execute(self, state: RunState) -> str:
        if state.get("status") == "BLOCKED":
            return "blocked"
        ast = state.get("ast") or {}
        children = ast.get("children", [])
        idx = state.get("current_step_index", 0)
        if idx < len(children):
            last = (state.get("traces") or [])[-1] if state.get("traces") else {}
            if last.get("status") in ("fail",):
                if state.get("retry_count", 0) < state.get("max_retries", settings.max_retries):
                    return "retry"
                return "report"
            if last.get("status") == "clarify":
                if state.get("clarify_count", 0) >= settings.max_clarify_attempts:
                    return "blocked"
                return "continue"
            return "continue"
        return "report"

    def run(
        self,
        natural_language: str,
        *,
        base_url: str = "https://example.com",
        run_id: str | None = None,
        tenant: str = "default",
        risk_override: bool = False,
        thread_id: str | None = None,
    ) -> RunState:
        rid = run_id or str(uuid.uuid4())
        tid = thread_id or rid
        initial: RunState = {
            "run_id": rid,
            "natural_language": natural_language,
            "base_url": base_url,
            "tenant": tenant,
            "risk_override": risk_override,
        }
        config = {"configurable": {"thread_id": tid}}
        return self.graph.invoke(initial, config=config)

    def resume(self, thread_id: str, *, risk_override: bool = False) -> RunState:
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        if not snapshot or not snapshot.values:
            raise ValueError(f"no checkpoint for thread {thread_id}")
        state = dict(snapshot.values)
        state["risk_override"] = risk_override
        state["status"] = "EXECUTE"
        state["clarify_count"] = 0
        return self.graph.invoke(state, config=config)

    def _write_trace_file(self, run_id: str, traces: list[dict], report: dict | None = None) -> None:
        path = settings.artifacts_dir / run_id / "trace.json"
        payload: dict[str, Any] = {"traces": traces}
        if report:
            payload["report"] = report
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _persist_artifact(self, run_id: str, step_id: str, trace: dict) -> None:
        shot = trace.get("screenshot_path")
        if shot:
            self.artifacts.upload_file(run_id, step_id, Path(shot))


workflow = RunWorkflow()
