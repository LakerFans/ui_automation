from __future__ import annotations

from dataclasses import dataclass

from ui_test_platform.config import settings
from ui_test_platform.registry.store import SemanticRegistry


@dataclass
class RiskDecision:
    allowed: bool
    reason: str = ""
    requires_confirmation: bool = False


class RiskGate:
    """Gate high-risk DSL actions (delete, batch, overwrite)."""

    def __init__(self, registry: SemanticRegistry) -> None:
        self.registry = registry
        self.enabled = settings.require_risk_confirmation

    def check(self, text: str, *, confirmed: bool = False) -> RiskDecision:
        if not self.enabled:
            return RiskDecision(allowed=True)
        if not self.registry.is_risk_keyword(text):
            return RiskDecision(allowed=True)
        if confirmed:
            return RiskDecision(allowed=True, reason="risk confirmed")
        return RiskDecision(
            allowed=False,
            reason=f"high-risk action requires confirmation: {text}",
            requires_confirmation=True,
        )
