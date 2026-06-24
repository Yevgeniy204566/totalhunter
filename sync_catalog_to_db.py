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

# "Chest Catalog" — wide layout: один блок из 4 колонок на паттерн (Type | Points |
# пусто | пусто), блоки идут подряд слева направо. Первая строка блока = имя паттерна
# (ячейка над колонкой Type), вторая строка — заголовки "Type (EN)"/"Points", дальше —
# данные. Добавление нового паттерна = новый блок +4 колонки, без правки кода.
LOCALIZATION_LANGUAGE = "ru"

SA_PATH = r"C:\BattleBot\service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def build_sheets_service():
    creds = Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def read_tab_rows(service, tab_name: str, last_column: str = "B") -> list[list]:
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{tab_name}!A2:{last_column}",
    ).execute()
    return result.get("values", [])


def build_catalog_payload(service) -> dict:
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range="Chest Catalog!A1:ZZ200",
    ).execute()
    grid = result.get("values", [])
    header_row, data_rows = grid[0], grid[2:]

    entries = []
    for block_col in range(0, len(header_row), 4):
        pattern = header_row[block_col].strip() if block_col < len(header_row) else ""
        if not pattern:
            continue
        for row in data_rows:
            if block_col + 1 >= len(row):
                continue
            chest_type, points_cell = row[block_col].strip(), row[block_col + 1].strip()
            if not chest_type or not points_cell:
                continue
            try:
                points = int(points_cell)
            except ValueError:
                raise ValueError(
                    f"Chest Catalog ({pattern}): '{points_cell}' is not a number for {chest_type!r}"
                )
            entries.append({"canonical_type": chest_type, "pattern": pattern, "points": points})
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


def build_catalog_reference_payload(rows: list) -> dict:
    """rows: numbered (№, Name) pairs from the "Сундуки" tab's master reference list
    (columns O:P) — the single source of all known chest type IDs in the game."""
    return {
        "entries": [
            {"catalog_id": row[1].strip()}
            for row in rows if len(row) >= 2 and row[1].strip()
        ]
    }


def fetch_catalog_reference_rows(service) -> list:
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range="Сундуки!O2:P300",
    ).execute()
    return result.get("values", [])


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

    reference_payload = build_catalog_reference_payload(fetch_catalog_reference_rows(service))
    reference_result = push("/api/v1/chests/catalog-reference/import", reference_payload,
                            admin_token)
    print(f"  Эталонный список (дропдаун): {reference_result['count']} записей")
