from __future__ import annotations

from ui_test_platform.registry.store import SemanticRegistry
from ui_test_platform.safety.risk_gate import RiskGate


def test_risk_gate_blocks_delete_without_confirmation():
    reg = SemanticRegistry()
    gate = RiskGate(reg)
    decision = gate.check("删除", confirmed=False)
    assert not decision.allowed
    assert decision.requires_confirmation


def test_risk_gate_allows_when_confirmed():
    reg = SemanticRegistry()
    gate = RiskGate(reg)
    decision = gate.check("删除", confirmed=True)
    assert decision.allowed
