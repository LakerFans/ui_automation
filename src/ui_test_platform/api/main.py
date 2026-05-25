from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ui_test_platform.config import settings
from ui_test_platform.graph.workflow import workflow
from ui_test_platform.registry.api import router as registry_router

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(registry_router)


class RunRequest(BaseModel):
    natural_language: str = Field(..., min_length=1)
    base_url: str = "https://example.com"
    tenant: str = "default"
    risk_override: bool = False


class ResumeRequest(BaseModel):
    risk_override: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "browser_backend": settings.browser_backend}


@app.post("/runs")
def create_run(body: RunRequest) -> dict[str, Any]:
    result = workflow.run(
        body.natural_language,
        base_url=body.base_url,
        tenant=body.tenant,
        risk_override=body.risk_override,
    )
    return {
        "run_id": result.get("run_id"),
        "verdict": result.get("verdict"),
        "status": result.get("status"),
        "report": result.get("report"),
    }


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    config = {"configurable": {"thread_id": run_id}}
    snap = workflow.graph.get_state(config)
    if not snap or not snap.values:
        raise HTTPException(status_code=404, detail="run not found")
    state = dict(snap.values)
    return {
        "run_id": run_id,
        "status": state.get("status"),
        "verdict": state.get("verdict"),
        "current_step_index": state.get("current_step_index"),
        "report": state.get("report"),
        "traces": state.get("traces"),
    }


@app.post("/runs/{run_id}/resume")
def resume_run(run_id: str, body: ResumeRequest) -> dict[str, Any]:
    try:
        result = workflow.resume(run_id, risk_override=body.risk_override)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "run_id": run_id,
        "verdict": result.get("verdict"),
        "status": result.get("status"),
        "report": result.get("report"),
    }
