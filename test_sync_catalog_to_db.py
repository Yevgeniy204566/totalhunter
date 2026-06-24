import sync_catalog_to_db as sc


def test_build_catalog_reference_payload_extracts_names_from_numbered_rows():
    rows = [["1", "Arena"], ["2", "Common Crypt 5"], ["139", "Sakura of Abundance"]]
    payload = sc.build_catalog_reference_payload(rows)
    assert payload == {"entries": [
        {"catalog_id": "Arena"},
        {"catalog_id": "Common Crypt 5"},
        {"catalog_id": "Sakura of Abundance"},
    ]}


def test_build_catalog_reference_payload_skips_blank_rows():
    rows = [["1", "Arena"], [], ["2", ""], ["3"]]
    payload = sc.build_catalog_reference_payload(rows)
    assert payload == {"entries": [{"catalog_id": "Arena"}]}
