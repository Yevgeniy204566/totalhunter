"""Tests for the Phase-2 schema additions: ChestCollector.pattern/language,
ChestTypeCatalog, ChestLocalization."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy.exc import IntegrityError

from models import (
    ChestCatalogReference, ChestCollector, ChestLocalization, ChestTypeCatalog, User,
)


@pytest.mark.asyncio
async def test_collector_pattern_and_language_default_to_none(db_session):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6))
    db_session.add(user)
    await db_session.flush()
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=user.id,
                               slug=secrets.token_urlsafe(16))
    db_session.add(collector)
    await db_session.commit()
    assert collector.pattern is None
    assert collector.language is None


@pytest.mark.asyncio
async def test_collector_pattern_and_language_can_be_set(db_session):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6))
    db_session.add(user)
    await db_session.flush()
    collector = ChestCollector(kingdom="K1", clan="ClanB", user_id=user.id,
                               slug=secrets.token_urlsafe(16), pattern="T9", language="ru")
    db_session.add(collector)
    await db_session.commit()
    assert collector.pattern == "T9"
    assert collector.language == "ru"


@pytest.mark.asyncio
async def test_chest_type_catalog_unique_on_type_and_pattern(db_session):
    db_session.add(ChestTypeCatalog(canonical_type="Epic Fenrir", pattern="T9", points=5))
    await db_session.commit()
    db_session.add(ChestTypeCatalog(canonical_type="Epic Fenrir", pattern="T9", points=9))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_chest_type_catalog_same_type_different_pattern_allowed(db_session):
    db_session.add(ChestTypeCatalog(canonical_type="Epic Fenrir", pattern="T9", points=5))
    db_session.add(ChestTypeCatalog(canonical_type="Epic Fenrir", pattern="T8", points=3))
    await db_session.commit()


@pytest.mark.asyncio
async def test_chest_localization_unique_on_type_and_language(db_session):
    db_session.add(ChestLocalization(canonical_type="Epic Fenrir", language="ru",
                                     display_text="Эпический Фенрир"))
    await db_session.commit()
    db_session.add(ChestLocalization(canonical_type="Epic Fenrir", language="ru",
                                     display_text="Другой перевод"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_chest_catalog_reference_unique_on_catalog_id(db_session):
    db_session.add(ChestCatalogReference(catalog_id="Sakura of Abundance"))
    await db_session.commit()
    db_session.add(ChestCatalogReference(catalog_id="Sakura of Abundance"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
