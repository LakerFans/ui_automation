from __future__ import annotations

from fastapi import FastAPI

from .models import PlanRequest
from .orchestrator import Orchestrator

app = FastAPI(title="UI Automation Platform")
orchestrator = Orchestrator()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
def run_plan(plan: PlanRequest) -> dict:
    state, result = orchestrator.run(plan)
    return {"state": state.value, "result": result.model_dump()}
