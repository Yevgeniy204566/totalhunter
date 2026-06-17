import time
import json

from clan_roster_reader import collect_roster, export_roster, OUTPUT_PATH

print("Открыта вкладка «Мой клан → Участники»? Старт через 3 сек...")
for i in (3, 2, 1):
    print(i)
    time.sleep(1)

roster = collect_roster()

print(f"\n===RESULT=== ({len(roster)} участников)")
for m in roster:
    print(f"  [{m['rank']}] {m['name']} — {m['might']}")

export_roster(roster)
print(f"\nФайл: {OUTPUT_PATH}")
