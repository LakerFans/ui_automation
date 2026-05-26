from __future__ import annotations

from .models import ASTNode, PlanRequest


class DSLCompiler:
    """Compile validated DSL actions into an executable AST."""

    def compile(self, plan: PlanRequest) -> ASTNode:
        children = [
            ASTNode(
                type="action",
                action=step.action,
                meta={
                    "target": step.target,
                    "value": step.value,
                    "url": str(step.url) if step.url else None,
                    "timeout_ms": step.timeout_ms,
                    "retry": step.retry,
                },
            )
            for step in plan.steps
        ]
        return ASTNode(type="sequence", children=children, meta={"task": plan.task})
