from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0.0"

ActionType = Literal[
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
]

AssertType = Literal[
    "text_assert",
    "visibility_assert",
    "url_assert",
    "table_assert",
    "api_assert",
    "console_assert",
]


class IntentEntry(BaseModel):
    intent_id: str
    text: str


class ActionStep(BaseModel):
    intent_id: Optional[str] = None
    intent: Optional[str] = None
    action: ActionType
    target: Optional[str] = None
    field: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    assert_type: Optional[AssertType] = None
    timeout_ms: int = Field(default=30000, ge=100, le=120_000)
    retry: int = Field(default=2, ge=0, le=5)
    risk_confirmed: bool = False

    @model_validator(mode="after")
    def validate_required_fields(self) -> ActionStep:
        action = self.action
        if action == "open" and not self.url:
            raise ValueError("open requires url")
        if action in ("click", "fill", "select", "hover", "upload") and not (
            self.target or self.field
        ):
            raise ValueError(f"{action} requires target or field")
        if action in ("fill", "select", "search") and self.value is None:
            raise ValueError(f"{action} requires value")
        if action == "search" and not (self.target or self.field):
            raise ValueError("search requires target (search box semantic name)")
        if action == "assert" and not self.assert_type:
            raise ValueError("assert requires assert_type")
        if action == "assert" and self.value is None and self.assert_type != "visibility_assert":
            raise ValueError("assert requires value except visibility_assert")
        return self

    @field_validator("url")
    @classmethod
    def url_scheme(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v

    def semantic_target(self) -> Optional[str]:
        return self.target or self.field


class TestPlan(BaseModel):
    schema_version: str = SCHEMA_VERSION
    task: str
    intents: list[IntentEntry] = Field(default_factory=list)
    steps: list[ActionStep]
