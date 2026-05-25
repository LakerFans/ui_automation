from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ui_test_platform.registry.store import registry

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("/semantics")
def get_semantics(
    url: str | None = Query(None),
    term: str | None = Query(None),
) -> dict:
    if not url and not term:
        raise HTTPException(status_code=400, detail="url or term required")
    return registry.query_semantics(url=url, term=term)


@router.get("/synonyms")
def get_synonyms(term: str = Query(...)) -> dict:
    return {"term": term, "synonyms": registry.lookup_synonyms(term)}


@router.get("/pages")
def get_pages(url: str = Query(...)) -> dict:
    page = registry.match_page(url)
    if not page:
        raise HTTPException(status_code=404, detail="page not found")
    return {
        "url_pattern": page.url_pattern,
        "name": page.name,
        "components": page.components,
        "fields": page.fields,
        "actions": page.actions,
    }


@router.post("/reload")
def reload_registry() -> dict:
    registry.reload()
    return {"status": "ok", "version": registry.version}
