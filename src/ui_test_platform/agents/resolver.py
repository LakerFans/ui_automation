from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Literal

from ui_test_platform.browser.adapter import RefEntry, SnapshotResult
from ui_test_platform.config import settings
from ui_test_platform.registry.store import SemanticRegistry


@dataclass
class ResolveResult:
    resolved_ref: str | None
    confidence: float
    status: Literal["Resolved", "Ambiguous", "Failed"]
    candidates: list[dict] | None = None
    reason: str = ""


class PageResolver:
    def __init__(self, registry: SemanticRegistry) -> None:
        self.registry = registry
        self.confidence_threshold = settings.confidence_threshold
        self.clarify_threshold = settings.clarify_threshold

    def resolve(
        self,
        dsl_action: str,
        target: str | None,
        snapshot: SnapshotResult,
        *,
        region_hint: str | None = None,
    ) -> ResolveResult:
        if not target:
            if dsl_action in ("open", "snapshot", "screenshot", "console", "wait", "scroll"):
                return ResolveResult(resolved_ref=None, confidence=1.0, status="Resolved")
            return ResolveResult(
                resolved_ref=None,
                confidence=0.0,
                status="Failed",
                reason="missing target",
            )

        if snapshot.has_iframe:
            return ResolveResult(
                resolved_ref=None,
                confidence=0.0,
                status="Failed",
                reason="iframe blocked",
            )

        terms = self.registry.expand_terms(target)
        scored: list[tuple[float, RefEntry]] = []
        page = self.registry.match_page(snapshot.url)

        for ref in snapshot.refs:
            score = self._score_ref(target, terms, ref, page, region_hint)
            scored.append((score, ref))

        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored or scored[0][0] <= 0:
            return ResolveResult(
                resolved_ref=None,
                confidence=0.0,
                status="Failed",
                reason="no matching ref",
            )

        top_score, top_ref = scored[0]
        confidence = min(1.0, top_score)
        candidates = [
            {"ref": r.ref, "name": r.name, "score": round(s, 3)}
            for s, r in scored[:3]
        ]

        if len(scored) > 1 and scored[1][0] >= top_score * 0.95:
            if confidence >= self.clarify_threshold:
                return ResolveResult(
                    resolved_ref=None,
                    confidence=confidence,
                    status="Ambiguous",
                    candidates=candidates,
                    reason="multiple similar refs",
                )

        if confidence < self.clarify_threshold:
            return ResolveResult(
                resolved_ref=None,
                confidence=confidence,
                status="Failed",
                candidates=candidates,
                reason="confidence below clarify threshold",
            )

        if confidence < self.confidence_threshold:
            return ResolveResult(
                resolved_ref=top_ref.ref,
                confidence=confidence,
                status="Ambiguous",
                candidates=candidates,
                reason="below auto threshold",
            )

        return ResolveResult(
            resolved_ref=top_ref.ref,
            confidence=confidence,
            status="Resolved",
            candidates=candidates,
        )

    def _score_ref(
        self,
        target: str,
        terms: set[str],
        ref: RefEntry,
        page,
        region_hint: str | None,
    ) -> float:
        name = ref.name.lower()
        if target.lower() == name:
            return 1.0
        name_sim = max(
            difflib.SequenceMatcher(None, target.lower(), name).ratio(),
            max(
                (difflib.SequenceMatcher(None, t, name).ratio() for t in terms),
                default=0.0,
            ),
        )
        synonym_boost = 1.0 if any(t in name for t in terms) else 0.0
        region_match = 0.0
        if page and region_hint and page.actions:
            for action_name, meta in page.actions.items():
                if action_name.lower() in terms and meta.get("region") == region_hint:
                    region_match = 1.0
                    break
        return 0.5 * name_sim + 0.3 * synonym_boost + 0.2 * region_match
