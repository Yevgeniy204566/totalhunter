"""
models.py — SQLAlchemy ORM models for Total Hunter SaaS backend.

DB: PostgreSQL
Framework: FastAPI + SQLAlchemy 2.0 (async)
Timestamps: server_default=func.now() — DB sets time, not Python.
Naming convention: предсказуемые имена для индексов и ключей (Alembic gold standard).
"""

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer,
    JSON, MetaData, Numeric, String, Text, text,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

# Use timezone-aware DateTime — works with both PostgreSQL and SQLite (tests)
TIMESTAMP = DateTime


# ── Naming convention — предсказуемые имена индексов/ключей для Alembic ──────
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)


# ─────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────

class User(Base):
    """
    Главная таблица пользователей.

    credits      — основной баланс (тратится на поиски)
    ref_credits  — реферальный баланс (% от покупок реферала,
                   переводится в credits через /transfer_referral_balance)
    ref_code     — уникальный код пользователя (раздаёт друзьям)
    invited_by_id — self-referential FK: L1 = invited_by,
                    L2 = invited_by.invited_by, L3 = ...
    last_seen    — обновляется при /heartbeat (онлайн-счётчик в админке)

    CheckConstraint: credits и ref_credits не могут уйти в минус —
    последний рубеж защиты от race condition при двойном списании.
    """
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint('credits >= 0',     name='credits_positive'),
        CheckConstraint('ref_credits >= 0', name='ref_credits_positive'),
    )

    id            = Column(Integer, primary_key=True)
    hwid          = Column(String(16),  unique=True, nullable=True,  index=True)
    email         = Column(String(255), unique=True, index=True)
    username      = Column(String(50))
    credits       = Column(Integer, nullable=False, server_default=text('0'))
    ref_credits   = Column(Integer, nullable=False, server_default=text('0'))
    ref_code      = Column(String(12), unique=True, nullable=False, index=True)
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    trial_used    = Column(Boolean, nullable=False, server_default=text('false'))
    is_banned     = Column(Boolean, nullable=False, server_default=text('false'))
    bot_version   = Column(String(20))
    ip_address    = Column(String(45))   # последний IP (IPv4 до 15, IPv6 до 45 символов)
    last_seen     = Column(TIMESTAMP(timezone=True))
    hwid_reset_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at    = Column(TIMESTAMP(timezone=True), nullable=False,
                           server_default=func.now())

    invited_by   = relationship("User", remote_side=[id], backref="referrals")
    transactions = relationship("Transaction", back_populates="user")
    hunts        = relationship("Hunt", back_populates="user")


# ─────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────

class Transaction(Base):
    """
    Все движения кредитов — единый источник правды.

    type:
        purchase        — покупка пакета Lite/Pro/Ultra
        credit_use      — списание за поиск (exchange=5кр, crypt=1кр)
        trial           — 300 пробных кредитов
        ref_welcome     — бонус при первой привязке реф. кода
        ref_earning     — % от покупки реферала → ref_credits
        ref_transfer    — перевод ref_credits → credits
        manual_adjust   — ручная корректировка из админки

    meta (JSONB):
        {"ref_from_user_id": 42, "level": 2}      — ref_earning
        {"hunt_type": "exchange"}                  — credit_use
        {"admin_note": "компенсация"}              — manual_adjust
        {"freekassa_order_id": "FK-12345"}         — purchase
    """
    __tablename__ = "transactions"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type       = Column(String(30), nullable=False, index=True)
    amount     = Column(Integer, nullable=False)
    usd_amount = Column(Numeric(10, 2))
    package    = Column(String(10))
    meta       = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=func.now(), index=True)

    user = relationship("User", back_populates="transactions")


# ─────────────────────────────────────────────
# Hunts
# ─────────────────────────────────────────────

class Hunt(Base):
    """
    Каждая успешная находка = одна запись.
    Отдельно от transactions — чтобы финансовые и статистические
    запросы не мешали друг другу.

    hunt_type: exchange (5 кр.) / crypt (1 кр.)
    created_at индексируется — фильтры today/week/month.
    """
    __tablename__ = "hunts"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hunt_type  = Column(String(20), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=func.now(), index=True)

    user = relationship("User", back_populates="hunts")


# ─────────────────────────────────────────────
# Logs
# ─────────────────────────────────────────────

class Log(Base):
    """Телеметрия ошибок от клиентов → /log_error."""
    __tablename__ = "logs"

    id         = Column(Integer, primary_key=True)
    hwid       = Column(String(16), index=True)
    event_type = Column(String(50))
    payload    = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=func.now(), index=True)


# ─────────────────────────────────────────────
# Broadcasts
# ─────────────────────────────────────────────

class Broadcast(Base):
    """Глобальные уведомления: админка → все боты при /check_auth."""
    __tablename__ = "broadcasts"

    id         = Column(Integer, primary_key=True)
    message    = Column(Text, nullable=False)
    is_active  = Column(Boolean, nullable=False, server_default=text('true'))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=func.now())


# ─────────────────────────────────────────────
# AppSettings
# ─────────────────────────────────────────────

class AppSetting(Base):
    """
    Ключ-значение для глобальных настроек платформы.

    Стандартные ключи:
        current_version — '1.0.0'
        min_version     — '1.0.0'
        force_update    — 'false' / 'true'
    """
    __tablename__ = "app_settings"

    key        = Column(String(50), primary_key=True)
    value      = Column(Text, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=func.now(), onupdate=func.now())


# ─────────────────────────────────────────────
# LinkCodes — HWID linking via 6-digit code
# ─────────────────────────────────────────────

class LinkCode(Base):
    __tablename__ = "link_codes"

    id         = Column(Integer, primary_key=True)
    hwid       = Column(String(16), nullable=False, index=True)
    code       = Column(String(6), nullable=False, unique=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=func.now())


# ─────────────────────────────────────────────
# HwidHistory — anti-abuse: one trial per hardware
# ─────────────────────────────────────────────

class HwidHistory(Base):
    __tablename__ = "hwid_history"

    id        = Column(Integer, primary_key=True)
    hwid      = Column(String(16), nullable=False, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    linked_at = Column(TIMESTAMP(timezone=True), nullable=False,
                       server_default=func.now())
