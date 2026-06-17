import time
import json

from tournament_reader import collect_tournament_data

print("Открыт диалог «Статистика»? Старт через 3 сек...")
for i in (3, 2, 1):
    print(i)
    time.sleep(1)

data = collect_tournament_data()

print("===RESULT===")
print(json.dumps(data, ensure_ascii=False, indent=2))
