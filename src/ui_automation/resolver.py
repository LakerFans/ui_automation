from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResolveResult:
    resolved_ref: str
    confidence: float


class PageResolver:
    """Runtime semantic resolver for page refs."""

    def resolve(self, action_target: str, refs_tree: dict) -> ResolveResult:
        for ref, metadata in refs_tree.items():
            label = str(metadata.get("label", ""))
            if action_target in label:
                return ResolveResult(resolved_ref=ref, confidence=0.95)
        return ResolveResult(resolved_ref="@unknown", confidence=0.0)
