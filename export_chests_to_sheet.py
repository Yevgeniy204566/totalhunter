"""
export_chests_to_sheet.py — pulls the chest summary for one collector from the live API
and writes it into a Google Sheet, fully overwriting the target tab on every run.

Run manually: python export_chests_to_sheet.py
"""
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

API_BASE = "https://api.total-hunter.com"
SLUG = "m00bqgjcl1xqUHRDvEa8bQ"
SHEET_ID = "1EjUF5TIj3gAD4kv-XYYoQMKTHqOVn7OySYumAtNukug"
SHEET_RANGE = "Лист1"  # имя вкладки по умолчанию в RU-локали Google Sheets, не "Sheet1"

SA_PATH = r"C:\BattleBot\service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def fetch_summary(slug: str) -> dict:
    resp = requests.get(f"{API_BASE}/api/v1/chests/summary/{slug}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def build_rows(summary: dict) -> list[list]:
    header = ["Игрок", "Очки", "Всего сундуков"] + summary["chest_types"]
    totals_row = ["ВСЕГО", summary["totals"].get("total_points", ""),
                  summary["totals"].get("grand_total", 0)]
    totals_row += [summary["totals"].get(t, 0) for t in summary["chest_types"]]
    rows = [header, totals_row]
    for player in summary["players"]:
        row = [player["name"], player.get("points", ""), player["total"]]
        row += [player["counts"].get(t, 0) for t in summary["chest_types"]]
        rows.append(row)
    return rows


def build_sheets_service():
    creds = Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def write_to_sheet(service, rows: list[list]):
    sheets = service.spreadsheets().values()
    sheets.clear(spreadsheetId=SHEET_ID, range=SHEET_RANGE).execute()
    sheets.update(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_RANGE}!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()


if __name__ == "__main__":
    print(f"=== Экспорт сундуков {SLUG} в Google Sheet ===\n")
    summary = fetch_summary(SLUG)
    rows = build_rows(summary)
    service = build_sheets_service()
    write_to_sheet(service, rows)
    print(f"  Готово: {len(rows) - 2} игроков, "
          f"{summary['totals'].get('grand_total', 0)} сундуков всего")
    print(f"  https://docs.google.com/spreadsheets/d/{SHEET_ID}")
