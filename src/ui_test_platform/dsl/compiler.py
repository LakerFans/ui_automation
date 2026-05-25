from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from ui_test_platform.dsl.models import ActionStep, SCHEMA_VERSION


class ASTActionNode(BaseModel):
    type: Literal["action"] = "action"
    action: str
    intent_id: Optional[str] = None
    intent: Optional[str] = None
    target: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    assert_type: Optional[str] = None
    retry: int = 2
    timeout_ms: int = 30000
    depends_on: list[str] = Field(default_factory=list)
    condition: Optional[dict[str, Any]] = None
    rollback: Optional[list[dict[str, Any]]] = None
    risk_confirmed: bool = False


class ASTSequenceNode(BaseModel):
    type: Literal["sequence"] = "sequence"
    schema_version: str = SCHEMA_VERSION
    children: list[ASTActionNode]


class DSLCompiler:
    """Validate Action DSL steps and compile to executable AST."""

    ALLOWED_ACTIONS = {
        "open",
        "click",
        "fill",
        "select",
        "search",
        "hover",
        "scroll",
        "wait",
        "assert",
        "upload",
        "snapshot",
        "screenshot",
        "console",
    }

    def validate_steps(self, steps: list[ActionStep]) -> list[ActionStep]:
        validated: list[ActionStep] = []
        for step in steps:
            if step.action not in self.ALLOWED_ACTIONS:
                raise ValueError(f"Illegal action: {step.action}")
            validated.append(step)
        return validated

    def compile(self, steps: list[ActionStep]) -> ASTSequenceNode:
        validated = self.validate_steps(steps)
        children: list[ASTActionNode] = []
        for step in validated:
            if step.action == "search":
                box = step.semantic_target() or "搜索框"
                children.append(
                    ASTActionNode(
                        action="fill",
                        intent_id=step.intent_id,
                        intent=f"{step.intent or 'search'}: fill",
                        target=box,
                        value=step.value,
                        retry=step.retry,
                        timeout_ms=step.timeout_ms,
                    )
                )
                children.append(
                    ASTActionNode(
                        action="press_enter",
                        intent=f"{step.intent or 'search'}: submit",
                        target=box,
                        retry=step.retry,
                        timeout_ms=step.timeout_ms,
                    )
                )
                continue

            children.append(
                ASTActionNode(
                    action=step.action,
                    intent_id=step.intent_id,
                    intent=step.intent,
                    target=step.semantic_target(),
                    value=step.value,
                    url=step.url,
                    assert_type=step.assert_type,
                    retry=step.retry,
                    timeout_ms=step.timeout_ms,
                    risk_confirmed=step.risk_confirmed,
                )
            )
        return ASTSequenceNode(children=children)
