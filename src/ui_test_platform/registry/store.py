from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ui_test_platform.config import settings


@dataclass
class PageTemplate:
    url_pattern: str
    name: str
    components: list[str] = field(default_factory=list)
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)
    actions: dict[str, dict[str, Any]] = field(default_factory=dict)


class SemanticRegistry:
    def __init__(self, registry_dir: Path | None = None) -> None:
        self.registry_dir = registry_dir or settings.registry_dir
        self.version = "1.0.0"
        self.synonyms: dict[str, list[str]] = {}
        self.pages: list[PageTemplate] = []
        self.risk_keywords: list[str] = []
        self._synonym_index: dict[str, set[str]] = {}
        self.reload()

    def reload(self) -> None:
        self.synonyms.clear()
        self.pages.clear()
        self.risk_keywords.clear()
        self._synonym_index.clear()

        for path in sorted(self.registry_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.version = data.get("version", self.version)
            self.synonyms.update(data.get("synonyms", {}))
            for page in data.get("pages", []):
                self.pages.append(PageTemplate(**page))
            self.risk_keywords.extend(data.get("risk_keywords", []))

        for term, alts in self.synonyms.items():
            bucket = self._synonym_index.setdefault(term.lower(), {term.lower()})
            bucket.update(a.lower() for a in alts)
            for alt in alts:
                self._synonym_index.setdefault(alt.lower(), bucket)

    def lookup_synonyms(self, term: str) -> list[str]:
        bucket = self._synonym_index.get(term.lower(), {term.lower()})
        return sorted(bucket)

    def match_page(self, url: str) -> PageTemplate | None:
        for page in self.pages:
            if fnmatch.fnmatch(url, page.url_pattern):
                return page
        return None

    def query_semantics(self, url: str | None = None, term: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if term:
            syns = self.lookup_synonyms(term)
            result["term"] = term
            result["synonyms"] = syns
            page = self.match_page(url) if url else None
            if page:
                for action_name, meta in page.actions.items():
                    if term.lower() in self.lookup_synonyms(action_name):
                        result["region_hint"] = meta.get("region")
                        break
        if url:
            page = self.match_page(url)
            if page:
                result["page"] = {
                    "name": page.name,
                    "fields": list(page.fields.keys()),
                    "actions": list(page.actions.keys()),
                }
        return result

    def expand_terms(self, term: str) -> set[str]:
        return set(self.lookup_synonyms(term))

    def is_risk_keyword(self, text: str) -> bool:
        lower = text.lower()
        return any(kw.lower() in lower for kw in self.risk_keywords)


registry = SemanticRegistry()
