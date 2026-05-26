from __future__ import annotations

import time

from .models import ASTNode, ExecutionResult
from .resolver import PageResolver


class Executor:
    def __init__(self, resolver: PageResolver | None = None):
        self.resolver = resolver or PageResolver()

    def execute(self, ast: ASTNode, refs_tree: dict | None = None) -> ExecutionResult:
        refs_tree = refs_tree or {}
        trace: list[dict] = []
        for idx, node in enumerate(ast.children):
            start = time.time()
            target = node.meta.get("target")
            resolved_ref = None
            if target:
                resolved = self.resolver.resolve(target, refs_tree)
                resolved_ref = resolved.resolved_ref
            trace.append(
                {
                    "step_id": f"step-{idx + 1}",
                    "action": node.action.value if node.action else "unknown",
                    "ref": resolved_ref,
                    "duration": int((time.time() - start) * 1000),
                }
            )
        return ExecutionResult(status="success", message="Execution completed", trace=trace)
