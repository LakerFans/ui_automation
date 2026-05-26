from __future__ import annotations

from .compiler import DSLCompiler
from .executor import Executor
from .models import ExecutionResult, ExecutionState, PlanRequest


class Orchestrator:
    def __init__(self):
        self.compiler = DSLCompiler()
        self.executor = Executor()

    def run(self, plan: PlanRequest) -> tuple[ExecutionState, ExecutionResult]:
        state = ExecutionState.PLAN
        ast = self.compiler.compile(plan)
        state = ExecutionState.EXECUTE
        result = self.executor.execute(ast)
        state = ExecutionState.REPORT if result.status == "success" else ExecutionState.RETRY
        return state, result
