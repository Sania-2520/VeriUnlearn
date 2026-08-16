from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.services.privacy import PrivacyService

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.post("/search")
async def search_identities(
    query: str,
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    """Privacy Audit: scan all shards/datasets for an identity."""
    matches = await PrivacyService(db).search_identities(query, limit=limit)
    return {
        "query": query,
        "match_count": len(matches),
        "matches": matches,
        "scanned": "all_shards",
    }


@router.get("/footprint/{identity_key}")
async def identity_footprint(identity_key: str, db: DbSession, user: CurrentUser) -> dict:
    """Identity Footprint Analysis: full memory profile of an identity."""
    try:
        return await PrivacyService(db).identity_footprint(identity_key)
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc
