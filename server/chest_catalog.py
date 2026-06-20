"""
chest_catalog.py — admin endpoints for the GLOBAL chest catalog (points per pattern)
and GLOBAL localizations (display text per language).

Unlike player_aliases/chest_type_aliases, these are NOT scoped to a single collector —
one points value per (chest, pattern) and one translation per (chest, language), shared
by every clan that uses that pattern/language.

Auth: Bearer $ADMIN_TOKEN (same pattern as chest_aliases.py).
"""
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import ChestLocalization, ChestTypeCatalog

router = APIRouter(prefix="/api/v1/chests", tags=["chests"])

_bearer = HTTPBearer(auto_error=False)
_ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    if not _ADMIN_TOKEN or creds is None or creds.credentials != _ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


class CatalogEntryIn(BaseModel):
    canonical_type: str
    pattern: str
    points: int


class CatalogImportPayload(BaseModel):
    entries: List[CatalogEntryIn] = []


class LocalizationEntryIn(BaseModel):
    canonical_type: str
    language: str
    display_text: str


class LocalizationImportPayload(BaseModel):
    entries: List[LocalizationEntryIn] = []


def _find_duplicate_key(keys):
    """Returns the first key seen twice, or None — surfaces a clear 400 instead of
    letting a Sheet copy-paste mistake hit the DB's unique constraint as a raw 500."""
    seen = set()
    for key in keys:
        if key in seen:
            return key
        seen.add(key)
    return None


@router.post("/catalog/import", dependencies=[Depends(_require_auth)])
async def import_catalog(payload: CatalogImportPayload, db: AsyncSession = Depends(get_db)):
    dup = _find_duplicate_key((item.canonical_type, item.pattern) for item in payload.entries)
    if dup:
        raise HTTPException(status_code=400,
                            detail=f"Duplicate entry for canonical_type={dup[0]!r}, pattern={dup[1]!r}")

    await db.execute(delete(ChestTypeCatalog))
    for item in payload.entries:
        db.add(ChestTypeCatalog(canonical_type=item.canonical_type, pattern=item.pattern,
                                points=item.points))
    await db.commit()
    return {"ok": True, "count": len(payload.entries)}


@router.post("/localizations/import", dependencies=[Depends(_require_auth)])
async def import_localizations(payload: LocalizationImportPayload,
                                db: AsyncSession = Depends(get_db)):
    dup = _find_duplicate_key((item.canonical_type, item.language) for item in payload.entries)
    if dup:
        raise HTTPException(status_code=400,
                            detail=f"Duplicate entry for canonical_type={dup[0]!r}, language={dup[1]!r}")

    await db.execute(delete(ChestLocalization))
    for item in payload.entries:
        db.add(ChestLocalization(canonical_type=item.canonical_type, language=item.language,
                                 display_text=item.display_text))
    await db.commit()
    return {"ok": True, "count": len(payload.entries)}
