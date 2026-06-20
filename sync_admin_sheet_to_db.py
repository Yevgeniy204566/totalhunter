"""
sync_admin_sheet_to_db.py — reads the "Player Aliases" and "Chest Aliases" tabs from
the Admin Sheet and pushes them to the server as a full-replace sync for one collector.

Run manually: ADMIN_TOKEN=... python sync_admin_sheet_to_db.py
"""
import os
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

API_BASE = "https://api.total-hunter.com"
SLUG = "m00bqgjcl1xqUHRDvEa8bQ"
SHEET_ID = "1EjUF5TIj3gAD4kv-XYYoQMKTHqOVn7OySYumAtNukug"

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


def build_payload(service) -> dict:
    player_rows = read_tab_rows(service, "Player Aliases")
    chest_rows = read_tab_rows(service, "Chest Aliases")
    return {
        "collector_slug": SLUG,
        "player_aliases": [
            {"raw_name": row[0].strip(), "canonical_name": row[1].strip()}
            for row in player_rows if len(row) >= 2 and row[0].strip() and row[1].strip()
        ],
        "chest_aliases": [
            {"raw_type": row[0].strip(), "canonical_type": row[1].strip()}
            for row in chest_rows if len(row) >= 2 and row[0].strip() and row[1].strip()
        ],
    }


def push_to_server(payload: dict, admin_token: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/api/v1/chests/aliases/import",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    admin_token = os.environ["ADMIN_TOKEN"]
    print(f"=== Синхронизация алиасов {SLUG} из Admin Sheet ===\n")
    service = build_sheets_service()
    payload = build_payload(service)
    result = push_to_server(payload, admin_token)
    print(f"  Игроков: {result['player_aliases']}, типов сундуков: {result['chest_aliases']}")
