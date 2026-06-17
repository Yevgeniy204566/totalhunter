import os
import json
import pytest
import cv2
import numpy as np
import clan_roster_reader as cr


FIXTURE_PATH = "Участнки.png"


def _load_fixture():
    return cv2.imdecode(np.fromfile(FIXTURE_PATH, dtype=np.uint8), cv2.IMREAD_COLOR)


def _get_content_roi():
    frame = _load_fixture()
    bbox = cr.detect_panel_bbox(frame)
    assert bbox is not None, "Panel not detected in fixture — check PANEL_HSV_LOWER/UPPER"
    x, y, w, h = bbox
    assert w > 200 and h > 200, f"Panel too small: {w}×{h}"
    return cr.crop_content_area(frame, bbox), bbox


def _get_all_visible_rows(content_roi, pitch, row_top):
    rows = []
    h = content_roi.shape[0]
    for i in range(cr.NUM_VISIBLE_ROWS + 2):
        top = row_top + i * pitch
        bot = top + pitch
        if top >= h or bot > h:
            break
        rows.append(content_roi[top:bot, :])
    return rows


# ─── clean_might ───────────────────────────────────────────────────────────

def test_clean_might_dots():
    assert cr.clean_might("1.676.145.555") == 1676145555

def test_clean_might_spaces():
    assert cr.clean_might("1 676 145 555") == 1676145555

def test_clean_might_short():
    assert cr.clean_might("389.184.272") == 389184272

def test_clean_might_empty():
    assert cr.clean_might("") is None

def test_clean_might_whitespace_only():
    assert cr.clean_might("   ") is None

def test_clean_might_nbsp():
    # non-breaking space — common OCR artifact in European locales
    assert cr.clean_might("1 676 145 555") == 1676145555

def test_clean_might_commas():
    # Game uses comma as thousands separator in some locales
    assert cr.clean_might("1,676,145,555") == 1676145555

def test_clean_might_strips_surrounding_whitespace():
    assert cr.clean_might("  4.011.008.748  ") == 4011008748


# ─── detect_panel_bbox ─────────────────────────────────────────────────────

def test_detect_panel_bbox_returns_valid_rect():
    frame = _load_fixture()
    bbox = cr.detect_panel_bbox(frame)
    assert bbox is not None
    x, y, w, h = bbox
    assert w > 200
    assert h > 300

def test_detect_panel_bbox_returns_none_on_empty_frame():
    blank = np.zeros((1080, 1920, 3), dtype=np.uint8)
    result = cr.detect_panel_bbox(blank)
    assert result is None


# ─── detect_row_pitch ──────────────────────────────────────────────────────

def test_row_pitch_in_expected_range():
    content_roi, _ = _get_content_roi()
    pitch, row_top = cr.detect_row_pitch(content_roi)
    assert pitch is not None, "detect_row_pitch returned None on fixture"
    assert 40 <= pitch <= 120, f"Unexpected pitch: {pitch}"
    assert 0 <= row_top <= 50, f"Unexpected row_top: {row_top}"


# ─── is_separator_row ──────────────────────────────────────────────────────

def test_is_separator_row_finds_at_least_one_separator():
    content_roi, _ = _get_content_roi()
    pitch, row_top = cr.detect_row_pitch(content_roi)
    rows = _get_all_visible_rows(content_roi, pitch, row_top)
    assert any(cr.is_separator_row(r) for r in rows), \
        "Expected at least one separator row (Глава/Старший) in fixture"

def test_is_separator_row_finds_at_least_one_member():
    content_roi, _ = _get_content_roi()
    pitch, row_top = cr.detect_row_pitch(content_roi)
    rows = _get_all_visible_rows(content_roi, pitch, row_top)
    assert any(not cr.is_separator_row(r) for r in rows), \
        "Expected at least one member row in fixture"


# ─── ocr_rank_name ─────────────────────────────────────────────────────────

def test_ocr_rank_name_returns_known_rank():
    content_roi, _ = _get_content_roi()
    pitch, row_top = cr.detect_row_pitch(content_roi)
    rows = _get_all_visible_rows(content_roi, pitch, row_top)
    sep_rows = [r for r in rows if cr.is_separator_row(r)]
    assert sep_rows, "No separator rows found — cannot test ocr_rank_name"
    rank = cr.ocr_rank_name(sep_rows[0])
    assert rank in cr.KNOWN_RANKS, \
        f"ocr_rank_name returned '{rank}', expected one of {cr.KNOWN_RANKS}"


# ─── ocr_member_name ───────────────────────────────────────────────────────

def test_ocr_member_name_non_empty():
    content_roi, _ = _get_content_roi()
    pitch, row_top = cr.detect_row_pitch(content_roi)
    rows = _get_all_visible_rows(content_roi, pitch, row_top)
    member_rows = [r for r in rows if not cr.is_separator_row(r)]
    assert member_rows, "No member rows found in fixture"
    name = cr.ocr_member_name(member_rows[0])
    assert len(name) >= 2, f"Name too short or empty: '{name}'"

def test_ocr_member_name_no_bracket_prefix():
    content_roi, _ = _get_content_roi()
    pitch, row_top = cr.detect_row_pitch(content_roi)
    rows = _get_all_visible_rows(content_roi, pitch, row_top)
    member_rows = [r for r in rows if not cr.is_separator_row(r)]
    for row in member_rows:
        name = cr.ocr_member_name(row)
        assert not name.startswith('['), f"Kingdom tag not stripped: '{name}'"


# ─── build_roster_from_rows (state machine unit tests) ─────────────────────

def test_build_roster_state_machine_basic():
    rows = [
        {'type': 'sep', 'rank': 'ГЛАВА'},
        {'type': 'member', 'name': 'Alpha', 'might': 100},
        {'type': 'sep', 'rank': 'СТАРШИЙ'},
        {'type': 'member', 'name': 'Beta', 'might': 200},
        {'type': 'member', 'name': 'Gamma', 'might': 300},
    ]
    result = cr.build_roster_from_rows(rows)
    assert result == [
        {'name': 'Alpha', 'rank': 'ГЛАВА', 'might': 100},
        {'name': 'Beta', 'rank': 'СТАРШИЙ', 'might': 200},
        {'name': 'Gamma', 'rank': 'СТАРШИЙ', 'might': 300},
    ]

def test_build_roster_non_sequential_ranks():
    # Ranks in "Все" tab may appear in any order
    rows = [
        {'type': 'sep', 'rank': 'СТАРШИЙ'},
        {'type': 'member', 'name': 'X', 'might': 1},
        {'type': 'sep', 'rank': 'ГЛАВА'},
        {'type': 'member', 'name': 'Y', 'might': 2},
        {'type': 'sep', 'rank': 'СТАРШИЙ'},
        {'type': 'member', 'name': 'Z', 'might': 3},
    ]
    result = cr.build_roster_from_rows(rows)
    assert result[0] == {'name': 'X', 'rank': 'СТАРШИЙ', 'might': 1}
    assert result[1] == {'name': 'Y', 'rank': 'ГЛАВА', 'might': 2}
    assert result[2] == {'name': 'Z', 'rank': 'СТАРШИЙ', 'might': 3}

def test_build_roster_skips_member_before_first_separator():
    # A member row at list top before any separator is unranked → skip
    rows = [
        {'type': 'member', 'name': 'Orphan', 'might': 999},
        {'type': 'sep', 'rank': 'РЯДОВОЙ'},
        {'type': 'member', 'name': 'Valid', 'might': 1},
    ]
    result = cr.build_roster_from_rows(rows)
    names = [r['name'] for r in result]
    assert 'Orphan' not in names
    assert 'Valid' in names


# ─── merge_roster_dedup ────────────────────────────────────────────────────

def test_merge_roster_dedup_removes_duplicates():
    scan1 = [{'name': 'Alice', 'rank': 'ГЛАВА', 'might': 100}]
    scan2 = [
        {'name': 'Alice', 'rank': 'ГЛАВА', 'might': 100},
        {'name': 'Bob', 'rank': 'СТАРШИЙ', 'might': 200},
    ]
    merged = cr.merge_roster_dedup(scan1, scan2)
    assert sum(1 for m in merged if m['name'] == 'Alice') == 1
    assert any(m['name'] == 'Bob' for m in merged)

def test_merge_roster_dedup_first_seen_wins():
    scan1 = [{'name': 'A', 'rank': 'ГЛАВА', 'might': 999}]
    scan2 = [{'name': 'A', 'rank': 'ГЛАВА', 'might': 111}]
    merged = cr.merge_roster_dedup(scan1, scan2)
    assert len(merged) == 1
    assert merged[0]['might'] == 999

def test_merge_roster_dedup_empty_inputs():
    assert cr.merge_roster_dedup([], []) == []
    assert cr.merge_roster_dedup([{'name': 'A', 'rank': 'ГЛАВА', 'might': 1}], []) == \
        [{'name': 'A', 'rank': 'ГЛАВА', 'might': 1}]


# ─── _measure_scroll_shift ────────────────────────────────────────────────

def test_measure_scroll_shift_returns_int():
    # matchTemplate on real game frames; synthetic test just verifies no crash/exception
    img = np.random.randint(50, 200, (700, 600, 3), dtype=np.uint8)
    shift = cr._measure_scroll_shift(img, img, pitch=100, row_top=10)
    assert isinstance(shift, (int, np.integer))

def test_measure_scroll_shift_small_shift_on_identical():
    # Identical frames: shift should be close to 0 (within 1 row)
    img = np.random.randint(50, 200, (700, 600, 3), dtype=np.uint8)
    shift = cr._measure_scroll_shift(img, img, pitch=100, row_top=10)
    assert abs(shift) <= 100  # at most 1 row — real end-of-list detection uses streak of 2


# ─── collect_roster (mocked) ───────────────────────────────────────────────

def test_collect_roster_returns_list(monkeypatch):
    monkeypatch.setattr(cr, "_load_tab_coords", lambda: {"СТАРШИЙ": (990, 318)})
    monkeypatch.setattr(cr, "_collect_rank_tab",
                        lambda rank, tx, ty: [{"name": "TestPlayer", "rank": rank, "might": 1000}])
    result = cr.collect_roster()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["rank"] == "СТАРШИЙ"

def test_collect_roster_entries_have_required_fields(monkeypatch):
    monkeypatch.setattr(cr, "_load_tab_coords", lambda: {
        "ГЛАВА": (869, 318), "СТАРШИЙ": (990, 318)
    })
    monkeypatch.setattr(cr, "_collect_rank_tab", lambda rank, tx, ty: [
        {"name": f"Player_{rank}", "rank": rank, "might": 500000}
    ])
    result = cr.collect_roster()
    assert len(result) == 2
    for member in result:
        assert "name" in member and member["name"]
        assert "rank" in member and member["rank"] in cr.KNOWN_RANKS
        assert "might" in member


# ─── export_to_api ─────────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_export_to_api_posts_correct_payload(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured['url'] = url
        captured['headers'] = headers
        captured['json'] = json
        return _FakeResponse(200)

    monkeypatch.setattr(cr.requests, "post", fake_post)

    config = {"api_url": "https://api.total-hunter.com", "api_token": "secret123"}
    roster = [{"name": "ЗОЛОТОЙ", "rank": "СТАРШИЙ", "might": 389184272}]

    result = cr.export_to_api(roster, config)

    assert result is True
    assert captured['url'] == "https://api.total-hunter.com/api/v1/clan/roster"
    assert captured['headers'] == {"Authorization": "Bearer secret123"}
    assert captured['json']['roster'] == roster
    assert 'collected_at' in captured['json']

def test_export_to_api_fallback_writes_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cr.requests, "post", lambda *a, **k: _FakeResponse(500))
    monkeypatch.chdir(tmp_path)

    config = {"api_url": "https://api.total-hunter.com", "api_token": "secret123"}
    roster = [{"name": "ЗОЛОТОЙ", "rank": "СТАРШИЙ", "might": 389184272}]

    result = cr.export_to_api(roster, config)

    assert result is False
    files = list(tmp_path.glob("roster_export_*.json"))
    assert len(files) == 1
    with open(files[0], encoding='utf-8') as f:
        saved = json.load(f)
    assert saved['roster'] == roster
