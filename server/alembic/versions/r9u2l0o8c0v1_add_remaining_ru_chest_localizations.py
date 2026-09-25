"""add remaining RU chest localizations (106 of 139 types)

Сессия #149, 2026-09-25: владелец подтвердил живьём на реальных данных «Феникс» —
из 17 распознанных типов сундуков 11 (65%) сразу автоматически объединились с пресетом
через уже имеющиеся 33 русских перевода (chest_localizations). Владелец попросил
дозаполнить оставшиеся 106 типов на русском (переводы по значению, не сверены с живыми
скриншотами игры — лучше 0% покрытия, ничего не ломает при несовпадении).

Revision ID: r9u2l0o8c0v1
Revises: s3c4o5u6t7f8
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'r9u2l0o8c0v1'
down_revision = 's3c4o5u6t7f8'
branch_labels = None
depends_on = None

# (canonical_type, русский текст) — только те 106, которых ещё не было (33 уже занесены
# ранее вручную владельцем/Claude, см. chest_localizations WHERE language='ru').
RU_TRANSLATIONS = [
    ("Ancients Chest", "Сундук Древних"),
    ("Ancients Quick March Chest", "Сундук Быстрого марша Древних"),
    ("Authority Rush", "Штурм Авторитета"),
    ("Beastman", "Зверолюд"),
    ("Bronze Chest Bank", "Бронзовый сундук (банк)"),
    ("Bronze Chest Clash For Throne", "Бронзовый сундук Битвы за трон"),
    ("Carrot Monster", "Морковный монстр"),
    ("Clan wealth (blue)", "Богатство клана (синее)"),
    ("Clan wealth (green)", "Богатство клана (зелёное)"),
    ("Clan wealth (purple)", "Богатство клана (фиолетовое)"),
    ("Clan wealth (red)", "Богатство клана (красное)"),
    ("Clan wealth (white)", "Богатство клана (белое)"),
    ("Clan wealth (yellow)", "Богатство клана (жёлтое)"),
    ("Conqueror Chest Bank", "Сундук Завоевателя (банк)"),
    ("Cursed Citadel 20", "Проклятая цитадель 20 уровня"),
    ("Cursed Citadel 25", "Проклятая цитадель 25 уровня"),
    ("Dark Omens Event", "Событие «Тёмные предзнаменования»"),
    ("Dark Omens Event Arcane Chest", "Тайный сундук события «Тёмные предзнаменования»"),
    ("Dark Omens Event Minor Omen Chest", "Малый сундук предзнаменований"),
    ("Dark Omens Ranking Chest", "Наградной сундук рейтинга «Тёмные предзнаменования»"),
    ("Epic Crypt 15", "Эпический склеп 15 уровня"),
    ("Epic Crypt 20", "Эпический склеп 20 уровня"),
    ("Epic Yao", "Эпический Яо"),
    ("Frozen Fallen King", "Замёрзший павший король"),
    ("Golden Chest Bank", "Золотой сундук (банк)"),
    ("Golden Chest Clash For Throne", "Золотой сундук Битвы за трон"),
    ("Hermes Store", "Магазин Гермеса"),
    ("Heroic 16", "Героический монстр 16 уровня"),
    ("Heroic 17", "Героический монстр 17 уровня"),
    ("Heroic 18", "Героический монстр 18 уровня"),
    ("Heroic 19", "Героический монстр 19 уровня"),
    ("Heroic 20", "Героический монстр 20 уровня"),
    ("Heroic 21", "Героический монстр 21 уровня"),
    ("Heroic 22", "Героический монстр 22 уровня"),
    ("Heroic 23", "Героический монстр 23 уровня"),
    ("Heroic 24", "Героический монстр 24 уровня"),
    ("Heroic 25", "Героический монстр 25 уровня"),
    ("Heroic 26", "Героический монстр 26 уровня"),
    ("Heroic 27", "Героический монстр 27 уровня"),
    ("Heroic 28", "Героический монстр 28 уровня"),
    ("Heroic 29", "Героический монстр 29 уровня"),
    ("Heroic 30", "Героический монстр 30 уровня"),
    ("Heroic 31", "Героический монстр 31 уровня"),
    ("Heroic 32", "Героический монстр 32 уровня"),
    ("Heroic 33", "Героический монстр 33 уровня"),
    ("Heroic 34", "Героический монстр 34 уровня"),
    ("Heroic 35", "Героический монстр 35 уровня"),
    ("Heroic 36", "Героический монстр 36 уровня"),
    ("Heroic 37", "Героический монстр 37 уровня"),
    ("Heroic 38", "Героический монстр 38 уровня"),
    ("Heroic 39", "Героический монстр 39 уровня"),
    ("Heroic 40", "Героический монстр 40 уровня"),
    ("Heroic 41", "Героический монстр 41 уровня"),
    ("Heroic 42", "Героический монстр 42 уровня"),
    ("Heroic 43", "Героический монстр 43 уровня"),
    ("Heroic 44", "Героический монстр 44 уровня"),
    ("Legendary Epic Ashen", "Легендарный Эпический Ашен"),
    ("Magic Chest Bank", "Магический сундук (банк)"),
    ("Magic Chest Clash For Throne", "Магический сундук Битвы за трон"),
    ("Mimic", "Мимик"),
    ("Precious Chest Bank", "Драгоценный сундук (банк)"),
    ("Precious Chest Clash For Throne", "Драгоценный сундук Битвы за трон"),
    ("Pumpkin Chest", "Тыквенный сундук"),
    ("Pumpkin Jack Reaper Chest", "Сундук Джека-Жнеца"),
    ("Pumpkin Spoils Of Dread Chest", "Тыквенный сундук Трофеев Ужаса"),
    ("Ragnarok Event", "Событие «Рагнарёк»"),
    ("Rare Crypt 10", "Редкий склеп 10 уровня"),
    ("Rare Crypt 20", "Редкий склеп 20 уровня"),
    ("Rise Of The Ancients", "Восстание Древних"),
    ("Runic 20-24", "Рунический сундук 20-24 уровня"),
    ("Runic 25-29", "Рунический сундук 25-29 уровня"),
    ("Runic 30-34", "Рунический сундук 30-34 уровня"),
    ("Runic 35-39", "Рунический сундук 35-39 уровня"),
    ("Runic 40-44", "Рунический сундук 40-44 уровня"),
    ("Runic 45", "Рунический сундук 45 уровня"),
    ("Sacred Rituals", "Священные ритуалы"),
    ("Sakura of Abundance", "Сакура изобилия"),
    ("Silver Chest Bank", "Серебряный сундук (банк)"),
    ("Silver Chest Clash For Throne", "Серебряный сундук Битвы за трон"),
    ("Snowman", "Снеговик"),
    ("Spoils Of Dread Event", "Событие «Трофеи Ужаса»"),
    ("Story", "История"),
    ("Summoning Dark Omens", "Призыв «Тёмных предзнаменований»"),
    ("Summoning Dark Omens Epic Omen Chest", "Эпический сундук предзнаменований"),
    ("Summoning Dark Omens Major Omen Chest", "Большой сундук предзнаменований"),
    ("Tartaros Crypt 10", "Склеп Тартароса 10 уровня"),
    ("Tartaros Crypt 15", "Склеп Тартароса 15 уровня"),
    ("Tartaros Crypt 20", "Склеп Тартароса 20 уровня"),
    ("Tartaros Crypt 25", "Склеп Тартароса 25 уровня"),
    ("Tartaros Crypt 30", "Склеп Тартароса 30 уровня"),
    ("Tartaros Crypt 35", "Склеп Тартароса 35 уровня"),
    ("The Great Hunt Tournament", "Турнир «Великая охота»"),
    ("Trials Of Olympus Event", "Событие «Испытания Олимпа»"),
    ("Union Clan Ranking", "Рейтинг Союза кланов"),
    ("Union Of Triumph Clan Ranking", "Рейтинг Союза Триумфа"),
    ("Union Reward", "Награда Союза"),
    ("Vault 10-14", "Хранилище 10-14 уровня"),
    ("Vault 15-19", "Хранилище 15-19 уровня"),
    ("Vault 20-24", "Хранилище 20-24 уровня"),
    ("Vault 25-29", "Хранилище 25-29 уровня"),
    ("Vault 30-34", "Хранилище 30-34 уровня"),
    ("Vault 35-39", "Хранилище 35-39 уровня"),
    ("Vault 40-44", "Хранилище 40-44 уровня"),
    ("Vault 45", "Хранилище 45 уровня"),
    ("Wooden Chest Bank", "Деревянный сундук (банк)"),
    ("Wooden Chest Clash For Throne", "Деревянный сундук Битвы за трон"),
]


def upgrade():
    conn = op.get_bind()
    meta = sa.MetaData()
    chest_localizations = sa.Table('chest_localizations', meta, autoload_with=conn)
    for canonical_type, display_text in RU_TRANSLATIONS:
        exists = conn.execute(
            sa.select(chest_localizations.c.id).where(
                chest_localizations.c.canonical_type == canonical_type,
                chest_localizations.c.language == 'ru',
            )
        ).first()
        if exists:
            continue
        conn.execute(chest_localizations.insert().values(
            canonical_type=canonical_type, language='ru', display_text=display_text,
        ))


def downgrade():
    conn = op.get_bind()
    meta = sa.MetaData()
    chest_localizations = sa.Table('chest_localizations', meta, autoload_with=conn)
    canonical_types = [c for c, _ in RU_TRANSLATIONS]
    conn.execute(
        chest_localizations.delete().where(
            chest_localizations.c.canonical_type.in_(canonical_types),
            chest_localizations.c.language == 'ru',
        )
    )
