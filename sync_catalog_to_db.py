"""
sync_catalog_to_db.py — reads the "Chest Catalog" and "Localizations" tabs from the
Admin Sheet and pushes them to the server as a full-replace sync. Unlike
sync_admin_sheet_to_db.py (per-collector aliases), this syncs the GLOBAL catalog and
GLOBAL localizations shared by every clan.

Run manually: ADMIN_TOKEN=... python sync_catalog_to_db.py
"""
import os
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

API_BASE = "https://api.total-hunter.com"
SHEET_ID = "1CvfVs4cWUr4EXs7e8uKi2wbT-sQ_gYSIWDw3oJ0Xo64"

# Какому паттерну/языку соответствуют текущие 2-колоночные вкладки — см. Global
# Constraints плана: новый паттерн/язык = новая такая же простая вкладка, не широкая
# таблица "впрок". Сейчас реален только T9 + ru.
CATALOG_PATTERN = "T9"
LOCALIZATION_LANGUAGE = "ru"

SA_PATH = r"C:\BattleBot\service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def build_sheets_service():
    creds = Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def read_tab_rows(service, tab_name: str) -> list[list]:
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{tab_name}!A2:B",
    ).execute()
    return result.get("values", [])


def build_catalog_payload(service) -> dict:
    rows = read_tab_rows(service, "Chest Catalog")
    entries = []
    for row in rows:
        if len(row) < 2 or not row[0].strip() or not row[1].strip():
            continue
        try:
            points = int(row[1].strip())
        except ValueError:
            raise ValueError(f"Chest Catalog: '{row[1]}' is not a number for {row[0]!r}")
        entries.append({"canonical_type": row[0].strip(), "pattern": CATALOG_PATTERN,
                        "points": points})
    return {"entries": entries}


def build_localizations_payload(service) -> dict:
    rows = read_tab_rows(service, "Localizations")
    return {
        "entries": [
            {"canonical_type": row[0].strip(), "language": LOCALIZATION_LANGUAGE,
             "display_text": row[1].strip()}
            for row in rows if len(row) >= 2 and row[0].strip() and row[1].strip()
        ]
    }


def push(path: str, payload: dict, admin_token: str) -> dict:
    resp = requests.post(
        f"{API_BASE}{path}", json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}, timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    admin_token = os.environ["ADMIN_TOKEN"]
    print("=== Синхронизация глобального каталога и локализаций ===\n")
    service = build_sheets_service()

    catalog_result = push("/api/v1/chests/catalog/import",
                          build_catalog_payload(service), admin_token)
    print(f"  Каталог: {catalog_result['count']} записей")

    loc_result = push("/api/v1/chests/localizations/import",
                      build_localizations_payload(service), admin_token)
    print(f"  Локализации: {loc_result['count']} записей")
