from __future__ import annotations

import fnmatch
import time
from pathlib import Path
from typing import Any

from ui_test_platform.agents.resolver import PageResolver
from ui_test_platform.browser.adapter import BrowserAdapter, SnapshotResult, create_browser
from ui_test_platform.config import settings
from ui_test_platform.dsl.compiler import ASTActionNode
from ui_test_platform.registry.store import registry
from ui_test_platform.safety.risk_gate import RiskGate


class ExecutorAgent:
    def __init__(
        self,
        browser: BrowserAdapter | None = None,
        resolver: PageResolver | None = None,
        risk_gate: RiskGate | None = None,
    ) -> None:
        self.resolver = resolver or PageResolver(registry)
        self.risk_gate = risk_gate or RiskGate(registry)
        self._browser = browser

    def bind_browser(self, browser: BrowserAdapter) -> None:
        self._browser = browser

    def execute_step(
        self,
        node: ASTActionNode,
        *,
        run_id: str,
        step_id: str,
        artifacts_dir: Path,
        clarify_count: int = 0,
    ) -> dict[str, Any]:
        browser = self._require_browser(run_id)
        start = time.monotonic()
        trace: dict[str, Any] = {
            "step_id": step_id,
            "action": node.action,
            "target": node.target,
            "status": "pending",
        }

        if node.action == "open":
            if node.url and not self._url_allowed(node.url):
                trace.update(status="fail", error="URL_NOT_ALLOWED", duration_ms=0)
                return trace
            result = browser.open(node.url or "")
            trace.update(status="success" if result.ok else "fail", error=result.code if not result.ok else None)
            if result.ok:
                snap = browser.snapshot()
                trace["snapshot_summary"] = self._summarize_snapshot(snap)
            trace["duration_ms"] = int((time.monotonic() - start) * 1000)
            return trace

        snap = browser.snapshot()
        trace["snapshot_summary"] = self._summarize_snapshot(snap)

        if snap.has_iframe and node.action not in ("snapshot", "screenshot", "console"):
            trace.update(status="blocked", error="IFRAME_BLOCKED", duration_ms=int((time.monotonic() - start) * 1000))
            return trace

        if node.action in ("snapshot", "screenshot", "console"):
            return self._exec_utility(browser, node, trace, start, artifacts_dir, step_id)

        if node.action == "assert":
            ok, detail = self._run_assert(browser, node, snap)
            trace.update(status="success" if ok else "fail", assert_detail=detail, duration_ms=int((time.monotonic() - start) * 1000))
            return trace

        if node.action == "press_enter":
            result = browser.press("Enter")
            trace.update(status="success" if result.ok else "fail", duration_ms=int((time.monotonic() - start) * 1000))
            return trace

        risk = self.risk_gate.check(node.target or node.intent or "", confirmed=node.risk_confirmed)
        if not risk.allowed:
            trace.update(status="blocked", error="RISK_NOT_CONFIRMED", risk=risk.reason, duration_ms=int((time.monotonic() - start) * 1000))
            return trace

        semantics = registry.query_semantics(url=snap.url, term=node.target)
        region_hint = semantics.get("region_hint")
        resolved = self.resolver.resolve(node.action, node.target, snap, region_hint=region_hint)
        trace["confidence"] = resolved.confidence
        trace["candidates"] = resolved.candidates

        if resolved.status == "Ambiguous":
            if clarify_count >= settings.max_clarify_attempts:
                trace.update(status="blocked", error="CLARIFY_EXHAUSTED", duration_ms=int((time.monotonic() - start) * 1000))
                return trace
            trace.update(status="clarify", error=resolved.reason, duration_ms=int((time.monotonic() - start) * 1000))
            return trace

        if resolved.status == "Failed" or not resolved.resolved_ref:
            trace.update(status="fail", error=resolved.reason or "RESOLVE_FAILED", duration_ms=int((time.monotonic() - start) * 1000))
            return trace

        trace["resolved_ref"] = resolved.resolved_ref
        result = self._dispatch(browser, node, resolved.resolved_ref)
        if not result.ok:
            trace.update(status="fail", error=result.code, stderr=result.stderr)
        else:
            trace["status"] = "success"
            post = browser.snapshot()
            trace["post_snapshot_summary"] = self._summarize_snapshot(post)

        shot_path = artifacts_dir / f"{step_id}.png"
        browser.screenshot(str(shot_path))
        trace["screenshot_path"] = str(shot_path)
        trace["duration_ms"] = int((time.monotonic() - start) * 1000)
        return trace

    def _require_browser(self, run_id: str) -> BrowserAdapter:
        if self._browser is None:
            self._browser = create_browser(f"run_{run_id}")
        return self._browser

    def _dispatch(self, browser: BrowserAdapter, node: ASTActionNode, ref: str):
        action = node.action
        if action == "click":
            return browser.click(ref)
        if action == "fill":
            return browser.fill(ref, node.value or "")
        if action == "select":
            return browser.select(ref, node.value or "")
        if action == "hover":
            return browser.hover(ref)
        if action == "scroll":
            return browser.scroll(node.value or "down")
        if action == "wait":
            return browser.wait(node.value or "1000")
        if action == "upload":
            return browser.fill(ref, node.value or "")
        from ui_test_platform.browser.adapter import CommandResult

        return CommandResult(ok=False, code="UNKNOWN_ACTION")

    def _exec_utility(
        self,
        browser: BrowserAdapter,
        node: ASTActionNode,
        trace: dict,
        start: float,
        artifacts_dir: Path,
        step_id: str,
    ) -> dict:
        if node.action == "snapshot":
            snap = browser.snapshot()
            trace["snapshot_summary"] = self._summarize_snapshot(snap)
            trace["status"] = "success"
        elif node.action == "screenshot":
            path = node.value or str(artifacts_dir / f"{step_id}.png")
            result = browser.screenshot(path)
            trace.update(status="success" if result.ok else "fail", screenshot_path=path)
        elif node.action == "console":
            logs = browser.console()
            trace.update(status="success", console_logs=logs.logs)
        trace["duration_ms"] = int((time.monotonic() - start) * 1000)
        return trace

    def _run_assert(self, browser: BrowserAdapter, node: ASTActionNode, snap: SnapshotResult) -> tuple[bool, str]:
        assert_type = node.assert_type or "text_assert"
        value = node.value or ""
        if assert_type == "url_assert":
            ok = value in snap.url
            return ok, f"url {snap.url!r} contains {value!r}: {ok}"
        if assert_type == "visibility_assert":
            target = node.target or value
            resolved = self.resolver.resolve("assert", target, snap)
            ok = resolved.status == "Resolved"
            return ok, f"visibility {target!r}: {ok}"
        if assert_type == "text_assert":
            haystack = " ".join(r.name for r in snap.refs) + " " + snap.title
            ok = value in haystack or value in snap.url
            return ok, f"text {value!r} in page: {ok}"
        if assert_type == "console_assert":
            logs = browser.console()
            errors = [l for l in logs.logs if str(l.get("level", "")).lower() == "error"]
            ok = not any(value in str(l) for l in errors)
            return ok, f"console assert: {ok}"
        return False, f"unsupported assert_type {assert_type}"

    def _summarize_snapshot(self, snap: SnapshotResult) -> dict:
        return {
            "url": snap.url,
            "title": snap.title,
            "ref_count": len(snap.refs),
            "refs": [{"ref": r.ref, "name": r.name} for r in snap.refs[:20]],
            "has_iframe": snap.has_iframe,
        }

    def _url_allowed(self, url: str) -> bool:
        patterns = [p.strip() for p in settings.allowed_url_patterns.split(",") if p.strip()]
        return any(fnmatch.fnmatch(url, pat.replace("*://", "*")) or fnmatch.fnmatch(url, pat) for pat in patterns)
