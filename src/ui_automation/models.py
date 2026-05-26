from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ActionType(str, Enum):
    open = "open"
    click = "click"
    fill = "fill"
    select = "select"
    hover = "hover"
    scroll = "scroll"
    wait = "wait"
    assert_ = "assert"
    upload = "upload"
    snapshot = "snapshot"
    screenshot = "screenshot"
    console = "console"


class Action(BaseModel):
    action: ActionType
    target: str | None = None
    value: str | None = None
    url: HttpUrl | None = None
    timeout_ms: int = Field(default=5000, ge=0)
    retry: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_required_fields(self) -> "Action":
        if self.action == ActionType.open and not self.url:
            raise ValueError("open action requires url")
        if self.action in {ActionType.click, ActionType.fill, ActionType.select, ActionType.hover, ActionType.assert_} and not self.target:
            raise ValueError(f"{self.action.value} action requires target")
        if self.action == ActionType.fill and self.value is None:
            raise ValueError("fill action requires value")
        return self


class PlanRequest(BaseModel):
    task: str
    steps: list[Action]


class ASTNode(BaseModel):
    type: Literal["sequence", "action"]
    action: ActionType | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    children: list["ASTNode"] = Field(default_factory=list)


ASTNode.model_rebuild()


class ExecutionState(str, Enum):
    INIT = "INIT"
    PLAN = "PLAN"
    RESOLVE = "RESOLVE"
    EXECUTE = "EXECUTE"
    ASSERT = "ASSERT"
    RETRY = "RETRY"
    RECOVER = "RECOVER"
    REPORT = "REPORT"
    END = "END"


class ExecutionResult(BaseModel):
    status: Literal["success", "failed"]
    message: str
    trace: list[dict[str, Any]] = Field(default_factory=list)
