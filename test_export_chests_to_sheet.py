import export_chests_to_sheet as ets


def test_build_rows_with_points_puts_points_and_total_first():
    summary = {
        "kingdom": "229", "clan": "BERS",
        "chest_types": ["Epic Fenrir", "Common Crypt 25"],
        "players": [
            {"name": "Иванов", "counts": {"Epic Fenrir": 2, "Common Crypt 25": 1},
             "total": 3, "points": 15},
        ],
        "totals": {"Epic Fenrir": 2, "Common Crypt 25": 1, "grand_total": 3,
                  "total_points": 15},
    }
    rows = ets.build_rows(summary)
    assert rows[0] == ["Игрок", "Очки", "Всего сундуков", "Epic Fenrir", "Common Crypt 25"]
    assert rows[1] == ["ВСЕГО", 15, 3, 2, 1]
    assert rows[2] == ["Иванов", 15, 3, 2, 1]


def test_build_rows_without_points_leaves_points_column_blank():
    summary = {
        "kingdom": "229", "clan": "BERS",
        "chest_types": ["Anything"],
        "players": [{"name": "P1", "counts": {"Anything": 1}, "total": 1}],
        "totals": {"Anything": 1, "grand_total": 1},
    }
    rows = ets.build_rows(summary)
    assert rows[0] == ["Игрок", "Очки", "Всего сундуков", "Anything"]
    assert rows[1] == ["ВСЕГО", "", 1, 1]
    assert rows[2] == ["P1", "", 1, 1]
