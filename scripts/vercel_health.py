"""Проверка Vercel для «Хангофа»: сколько деплоев копится по проектам.

Вес деплоев (ГБ) API не отдаёт — он виден только в Vercel → Usage → Deployment Storage → Projects.
Поэтому проверяем то, что от него зависит: число деплоев за 7 и 30 дней и самый «жирный» день
(на Hobby лимит 100 деплоев в сутки). Токен — переменная окружения VERCEL_TOKEN.

Запуск: python scripts/vercel_health.py
"""
import collections
import json
import os
import sys
import time
import urllib.request

TEAM = "team_CkkRPXdwtRtsL9YCk8n4Fzla"
DAY_MS = 86_400_000
WEEK_YELLOW = 100     # деплоев проекта за 7 дней
DAY_RED = 80          # деплоев проекта за сутки (лимит Hobby — 100)


def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def all_deployments(token):
    out, until = [], None
    for _ in range(40):
        url = f"https://api.vercel.com/v6/deployments?teamId={TEAM}&limit=100" + (f"&until={until}" if until else "")
        chunk = get(url, token).get("deployments", [])
        out += chunk
        if len(chunk) < 100:
            break
        until = chunk[-1]["created"]
    return out


def main():
    token = os.environ.get("VERCEL_TOKEN")
    if not token:
        print("VERCEL_TOKEN не задан")
        return 2
    deps = all_deployments(token)
    now = int(time.time() * 1000)
    per = collections.defaultdict(lambda: {"total": 0, "d7": 0, "d30": 0, "days": collections.Counter()})
    for d in deps:
        p = per[d["name"]]
        age = now - d["created"]
        p["total"] += 1
        if age <= 30 * DAY_MS:
            p["d30"] += 1
        if age <= 7 * DAY_MS:
            p["d7"] += 1
            p["days"][time.strftime("%Y-%m-%d", time.gmtime(d["created"] / 1000))] += 1
    zone = "🟢"
    for name, p in sorted(per.items()):
        busiest = max(p["days"].values(), default=0)
        mark = "🟢"
        if busiest >= DAY_RED:
            mark, zone = "🔴", "🔴"
        elif p["d7"] > WEEK_YELLOW:
            mark = "🟡"
            zone = zone if zone == "🔴" else "🟡"
        print(f"{mark} {name}: всего {p['total']}, за 30 дней {p['d30']}, за 7 дней {p['d7']}, "
              f"самый загруженный день недели {busiest}")
    print(f"Зона Vercel: {zone}")
    print("Вес в ГБ: Vercel → Usage → Deployment Storage → Projects (API его не отдаёт); письмо при 75%/100% приходит владельцу.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
