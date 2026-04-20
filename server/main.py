"""
main.py — Total Hunter SaaS API (FastAPI + async SQLAlchemy).

Запуск:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Эндпоинты Модуля 1 (Cloud API):
    POST /check_auth            — лицензия, баланс, broadcast, version check
    POST /use_credit            — списание кредитов за находку
    POST /claim_trial           — 300 пробных кредитов (один раз)
    POST /heartbeat             — онлайн-счётчик (каждые 2-3 мин от бота)
    POST /log_error             — телеметрия ошибок
    POST /activate_referral     — привязка реф. кода при первом запуске
    POST /transfer_referral_balance — перевод ref_credits → credits

Эндпоинты Модуля 3 (Admin Panel) — защищены Bearer токеном:
    GET  /admin/stats           — агрегированная статистика (карточки)
    GET  /admin/users           — список пользователей с поиском и пагинацией
    POST /admin/ban             — бан/разбан пользователя
    POST /admin/adjust_credits  — ручная корректировка баланса
    POST /admin/broadcast       — отправить broadcast всем ботам
    GET  /admin/logs            — последние 50 записей телеметрии
    GET  /admin                 — HTML-страница Admin Panel
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AppSetting, Broadcast, Feedback, Hunt, Log, Transaction, User
from web_routes import router as web_router
from schemas import (
    BasicResponse,
    CheckAuthResponse,
    HwidRequest,
    LogErrorRequest,
    ReferralRequest,
    UseCreditsRequest,
)

app = FastAPI(
    title="Total Hunter API",
    description="SaaS backend для бота Total Hunter",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://totalhunter.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_router)

# Стоимость действий в кредитах
CREDIT_COST = {
    "exchange": 5,
    "crypt": 1,
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _generate_ref_code() -> str:
    """Генерирует уникальный реферальный код: 8 символов, URL-safe."""
    return secrets.token_urlsafe(6)  # ~8 символов


async def _get_or_create_user(hwid: str, db: AsyncSession, ip: str | None = None) -> User:
    """
    Возвращает пользователя по HWID.
    Если не существует — создаёт нового (авторегистрация при первом запуске бота).
    Всегда обновляет ip_address последним известным IP.
    """
    result = await db.execute(select(User).where(User.hwid == hwid))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(hwid=hwid, ref_code=_generate_ref_code(), ip_address=ip)
        db.add(user)
        await db.flush()
    elif ip and user.ip_address != ip:
        user.ip_address = ip  # обновляем IP при каждом визите
    return user


async def _get_setting(key: str, db: AsyncSession) -> str | None:
    """Читает значение из app_settings по ключу."""
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else None


async def _get_active_broadcast(db: AsyncSession) -> str | None:
    """Возвращает последнее активное broadcast-сообщение."""
    result = await db.execute(
        select(Broadcast)
        .where(Broadcast.is_active == True)
        .order_by(Broadcast.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row.message if row else None


async def _apply_referral_bonuses(new_user: User, db: AsyncSession) -> None:
    """
    Начисляет Welcome Bonus при первой привязке реферального кода:
      - Новый пользователь:  +50 кредитов
      - L1 (пригласивший):   +100 кредитов
    Записывает транзакции для обеих сторон.
    """
    # Бонус новому пользователю
    new_user.credits += 50
    db.add(Transaction(
        user_id=new_user.id,
        type="ref_welcome",
        amount=50,
        meta={"role": "invited"},
    ))

    # Бонус пригласившему (L1)
    if new_user.invited_by_id:
        result = await db.execute(
            select(User).where(User.id == new_user.invited_by_id)
        )
        inviter = result.scalar_one_or_none()
        if inviter and not inviter.is_banned:
            inviter.credits += 100
            db.add(Transaction(
                user_id=inviter.id,
                type="ref_welcome",
                amount=100,
                meta={"role": "inviter", "invited_hwid": new_user.hwid},
            ))


# ─────────────────────────────────────────────────────────────────────────────
# POST /check_auth
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/check_auth", response_model=CheckAuthResponse)
async def check_auth(req: HwidRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Главный эндпоинт — вызывается ботом при каждом старте.

    - Авторегистрация нового HWID
    - Возвращает баланс, broadcast, статус бана
    - Проверяет версию бота (force_update)
    """
    async with db.begin():
        client_ip = request.client.host if request.client else None
        user = await _get_or_create_user(req.hwid, db, ip=client_ip)

        if user.is_banned:
            return CheckAuthResponse(
                authorized=False,
                credits=0,
                ref_credits=0,
                message="Доступ заблокирован.",
                banned=True,
            )

        broadcast        = await _get_active_broadcast(db)
        current_version  = await _get_setting("current_version", db)
        force_update_val = await _get_setting("force_update", db)

        return CheckAuthResponse(
            authorized=True,
            credits=user.credits,
            ref_credits=user.ref_credits,
            message="OK",
            email=user.email,
            username=user.username,
            ref_id=user.ref_code,
            broadcast=broadcast,
            banned=False,
            force_update=(force_update_val == "true"),
            current_version=current_version,
        )


# ─────────────────────────────────────────────────────────────────────────────
# POST /use_credit
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/use_credit", response_model=BasicResponse)
async def use_credit(req: UseCreditsRequest, db: AsyncSession = Depends(get_db)):
    """
    Списывает кредиты за успешную находку.

    Стоимость: exchange=5кр, crypt=1кр.
    CheckConstraint в БД не даст уйти в минус даже при race condition.
    """
    cost = CREDIT_COST.get(req.hunt_type, req.amount)

    async with db.begin():
        result = await db.execute(select(User).where(User.hwid == req.hwid))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_banned:
            raise HTTPException(status_code=403, detail="Banned")
        if user.credits < cost:
            raise HTTPException(
                status_code=402,
                detail={
                    "message": "Недостаточно кредитов. Пополни баланс.",
                    "credits": user.credits,
                    "required": cost,
                },
            )

        user.credits -= cost

        # Запись в транзакции
        db.add(Transaction(
            user_id=user.id,
            type="credit_use",
            amount=-cost,
            meta={"hunt_type": req.hunt_type},
        ))

        # Запись в статистику находок
        db.add(Hunt(user_id=user.id, hunt_type=req.hunt_type))

        # Реферальные отчисления с покупки — НЕ применяются к credit_use.
        # Проценты начисляются только при покупке пакетов (purchase).

    return BasicResponse(success=True, message="OK", credits=user.credits)


# ─────────────────────────────────────────────────────────────────────────────
# POST /claim_trial
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/claim_trial", response_model=BasicResponse)
async def claim_trial(req: HwidRequest, db: AsyncSession = Depends(get_db)):
    """
    Выдаёт 300 пробных кредитов — один раз на HWID.
    Повторный вызов возвращает success=False.
    """
    async with db.begin():
        user = await _get_or_create_user(req.hwid, db)

        if user.trial_used:
            return BasicResponse(
                success=False,
                message="Пробный период уже использован.",
                credits=user.credits,
            )

        user.credits    += 300
        user.trial_used  = True

        db.add(Transaction(user_id=user.id, type="trial", amount=300))

    return BasicResponse(success=True, message="300 кредитов зачислено!", credits=user.credits)


# ─────────────────────────────────────────────────────────────────────────────
# POST /heartbeat
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/heartbeat", response_model=BasicResponse)
async def heartbeat(req: HwidRequest, db: AsyncSession = Depends(get_db)):
    """
    Онлайн-пинг от бота — каждые 2-3 минуты пока бот запущен.
    Обновляет last_seen → админка считает онлайн за последние 5 минут.
    """
    async with db.begin():
        await db.execute(
            update(User)
            .where(User.hwid == req.hwid)
            .values(last_seen=datetime.now(timezone.utc))
        )
    return BasicResponse(success=True)


# ─────────────────────────────────────────────────────────────────────────────
# POST /log_error
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/log_error", response_model=BasicResponse)
async def log_error(req: LogErrorRequest, db: AsyncSession = Depends(get_db)):
    """Телеметрия ошибок от клиентов → таблица logs → видно в админке."""
    async with db.begin():
        db.add(Log(hwid=req.hwid, event_type="client_error", payload=req.error))
    return BasicResponse(success=True)


# ─────────────────────────────────────────────────────────────────────────────
# POST /activate_referral
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/activate_referral", response_model=BasicResponse)
async def activate_referral(req: ReferralRequest, db: AsyncSession = Depends(get_db)):
    """
    Привязывает реферальный код при первом запуске нового пользователя.

    Условия:
      - Нельзя ввести свой собственный код
      - Нельзя активировать повторно (invited_by_id уже установлен)
      - Код должен существовать в БД
    """
    async with db.begin():
        # Кто вводит код
        result = await db.execute(select(User).where(User.hwid == req.hwid))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.invited_by_id is not None:
            return BasicResponse(success=False, message="Реферальный код уже активирован.")

        # Чей код
        result = await db.execute(
            select(User).where(User.ref_code == req.ref_code)
        )
        inviter = result.scalar_one_or_none()

        if not inviter:
            return BasicResponse(success=False, message="Код не найден.")
        if inviter.hwid == req.hwid:
            return BasicResponse(success=False, message="Нельзя использовать свой код.")

        user.invited_by_id = inviter.id
        await _apply_referral_bonuses(user, db)

    return BasicResponse(
        success=True,
        message=f"Код активирован! +50 кредитов.",
        credits=user.credits,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /transfer_referral_balance
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/transfer_referral_balance", response_model=BasicResponse)
async def transfer_referral_balance(req: HwidRequest, db: AsyncSession = Depends(get_db)):
    """
    Переводит реферальный баланс (ref_credits) → основной (credits).
    Кнопка «Зачислить на основной баланс» в боте.
    """
    async with db.begin():
        result = await db.execute(select(User).where(User.hwid == req.hwid))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.ref_credits <= 0:
            return BasicResponse(
                success=False,
                message="Реферальный баланс пуст.",
                credits=user.credits,
            )

        amount          = user.ref_credits
        user.credits   += amount
        user.ref_credits = 0

        db.add(Transaction(
            user_id=user.id,
            type="ref_transfer",
            amount=amount,
            meta={"from": "ref_credits"},
        ))

    return BasicResponse(
        success=True,
        message=f"Переведено {amount} кредитов.",
        credits=user.credits,
    )


# ═════════════════════════════════════════════════════════════════════════════
# МОДУЛЬ 3: ADMIN PANEL
# ═════════════════════════════════════════════════════════════════════════════

# ── Admin Auth ────────────────────────────────────────────────────────────────

ADMIN_TOKEN = os.environ.get("ADMIN_SECRET_KEY", "change-me-before-deploy")
_bearer = HTTPBearer()


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    """FastAPI dependency — проверяет Bearer токен для всех /admin/* роутов."""
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")


# ── GET /admin/stats ──────────────────────────────────────────────────────────

@app.get("/admin/stats", dependencies=[Depends(require_admin)])
async def admin_stats(db: AsyncSession = Depends(get_db)):
    """
    Агрегированная статистика для карточек Dashboard.
    Онлайн = last_seen в последние 5 минут.
    """
    now = datetime.now(timezone.utc)
    online_threshold = now - timedelta(minutes=5)

    total_users  = (await db.execute(select(func.count(User.id)))).scalar()
    online_users = (await db.execute(
        select(func.count(User.id)).where(User.last_seen >= online_threshold)
    )).scalar()
    banned_users = (await db.execute(
        select(func.count(User.id)).where(User.is_banned == True)
    )).scalar()

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hunts_today = (await db.execute(
        select(func.count(Hunt.id)).where(Hunt.created_at >= today_start)
    )).scalar()
    hunts_total = (await db.execute(select(func.count(Hunt.id)))).scalar()

    exchanges_total = (await db.execute(
        select(func.count(Hunt.id)).where(Hunt.hunt_type == "exchange")
    )).scalar()
    crypts_total = (await db.execute(
        select(func.count(Hunt.id)).where(Hunt.hunt_type == "crypt")
    )).scalar()

    return {
        "total_users":    total_users,
        "online_users":   online_users,
        "banned_users":   banned_users,
        "hunts_today":    hunts_today,
        "hunts_total":    hunts_total,
        "exchanges_total": exchanges_total,
        "crypts_total":   crypts_total,
    }


# ── GET /admin/users ──────────────────────────────────────────────────────────

@app.get("/admin/users", dependencies=[Depends(require_admin)])
async def admin_users(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
):
    """
    Список пользователей с поиском (HWID / email / username) и пагинацией.
    Возвращает данные для таблицы: баланс, ref_credits, онлайн, IP, версия бота.
    """
    now = datetime.now(timezone.utc)
    online_threshold = now - timedelta(minutes=5)

    query = select(User).order_by(User.created_at.desc())
    if search:
        like = f"%{search}%"
        query = query.where(
            User.hwid.ilike(like) |
            User.email.ilike(like) |
            User.username.ilike(like)
        )

    total = (await db.execute(
        select(func.count()).select_from(query.subquery())
    )).scalar()

    result = await db.execute(query.offset((page - 1) * per_page).limit(per_page))
    users = result.scalars().all()

    # Referral tree counts (L1 / L2 / L3)
    rows = []
    for u in users:
        # L1 — прямые рефералы
        l1 = (await db.execute(
            select(func.count(User.id)).where(User.invited_by_id == u.id)
        )).scalar()

        # L2 — рефералы рефералов
        l2_ids = (await db.execute(
            select(User.id).where(User.invited_by_id == u.id)
        )).scalars().all()
        l2 = 0
        if l2_ids:
            l2 = (await db.execute(
                select(func.count(User.id)).where(User.invited_by_id.in_(l2_ids))
            )).scalar()

        # L3 — глубина 3
        l3_ids = (await db.execute(
            select(User.id).where(User.invited_by_id.in_(l2_ids))
        )).scalars().all() if l2_ids else []
        l3 = 0
        if l3_ids:
            l3 = (await db.execute(
                select(func.count(User.id)).where(User.invited_by_id.in_(l3_ids))
            )).scalar()

        is_online = bool(u.last_seen and u.last_seen >= online_threshold)

        rows.append({
            "id":          u.id,
            "hwid":        u.hwid,
            "email":       u.email,
            "username":    u.username,
            "credits":     u.credits,
            "ref_credits": u.ref_credits,
            "ref_code":    u.ref_code,
            "is_banned":   u.is_banned,
            "is_online":   is_online,
            "ip_address":  u.ip_address,
            "bot_version": u.bot_version,
            "last_seen":   u.last_seen.isoformat() if u.last_seen else None,
            "created_at":  u.created_at.isoformat() if u.created_at else None,
            "referrals":   {"l1": l1, "l2": l2, "l3": l3},
        })

    return {"total": total, "page": page, "per_page": per_page, "users": rows}


# ── POST /admin/ban ───────────────────────────────────────────────────────────

@app.post("/admin/ban", dependencies=[Depends(require_admin)])
async def admin_ban(hwid: str, banned: bool, db: AsyncSession = Depends(get_db)):
    """Бан или разбан пользователя по HWID."""
    async with db.begin():
        await db.execute(
            update(User).where(User.hwid == hwid).values(is_banned=banned)
        )
    return {"success": True, "hwid": hwid, "banned": banned}


# ── POST /admin/adjust_credits ────────────────────────────────────────────────

@app.post("/admin/adjust_credits", dependencies=[Depends(require_admin)])
async def admin_adjust_credits(
    hwid: str, amount: int, note: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Ручная корректировка баланса. amount может быть отрицательным."""
    async with db.begin():
        result = await db.execute(select(User).where(User.hwid == hwid))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.credits = max(0, user.credits + amount)
        db.add(Transaction(
            user_id=user.id,
            type="manual_adjust",
            amount=amount,
            meta={"admin_note": note},
        ))
    return {"success": True, "credits": user.credits}


# ── POST /admin/broadcast ─────────────────────────────────────────────────────

@app.post("/admin/broadcast", dependencies=[Depends(require_admin)])
async def admin_broadcast(message: str, db: AsyncSession = Depends(get_db)):
    """Отправить broadcast всем ботам (появится при следующем /check_auth)."""
    async with db.begin():
        # Деактивируем старые сообщения
        await db.execute(update(Broadcast).values(is_active=False))
        db.add(Broadcast(message=message, is_active=True))
    return {"success": True, "message": message}


# ── GET /admin/feedback/unread ────────────────────────────────────────────────

@app.get("/admin/feedback/unread", dependencies=[Depends(require_admin)])
async def feedback_unread(db: AsyncSession = Depends(get_db)):
    """Количество записей обратной связи от пользователей."""
    row = await db.execute(select(func.count()).select_from(Feedback))
    return {"count": row.scalar() or 0}


@app.get("/admin/feedback/list", dependencies=[Depends(require_admin)])
async def feedback_list(db: AsyncSession = Depends(get_db), limit: int = 100):
    """Список всех записей обратной связи (новые первыми)."""
    result = await db.execute(
        select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)
    )
    items = result.scalars().all()
    return [
        {
            "id":         f.id,
            "user_id":    f.user_id,
            "text":       f.text,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in items
    ]


# ── GET /admin/logs ───────────────────────────────────────────────────────────

@app.get("/admin/logs", dependencies=[Depends(require_admin)])
async def admin_logs(db: AsyncSession = Depends(get_db), limit: int = 50):
    """Последние N записей телеметрии ошибок."""
    result = await db.execute(
        select(Log).order_by(Log.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id":         l.id,
            "hwid":       l.hwid,
            "event_type": l.event_type,
            "payload":    l.payload,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


# ── GET /admin ─────────────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """Отдаёт HTML-страницу Admin Panel."""
    html_path = os.path.join(os.path.dirname(__file__), "admin", "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()
