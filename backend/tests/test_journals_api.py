from datetime import date

from tests.helpers import make_client, uniq


def _future_date_seed() -> date:
    token = uniq("jdt")
    day = (sum(ord(c) for c in token) % 28) + 1
    return date(2099, 1, day)


def test_journal_upsert_append_and_get_by_date():
    client = make_client()
    journal_date = _future_date_seed()
    source = f"test://journal/{uniq('src')}"
    part_1 = f"journal_part_1_{uniq('p')}"
    part_2 = f"journal_part_2_{uniq('p')}"

    first = client.post(
        "/api/v1/journals/upsert-append",
        json={"journal_date": journal_date.isoformat(), "append_text": part_1, "source": source},
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["journal_date"] == journal_date.isoformat()
    assert part_1 in first_body["raw_content"]

    second = client.post(
        "/api/v1/journals/upsert-append",
        json={"journal_date": journal_date.isoformat(), "append_text": part_2, "source": source},
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["id"] == first_body["id"]
    assert part_1 in second_body["raw_content"]
    assert part_2 in second_body["raw_content"]

    fetched = client.get(f"/api/v1/journals/{journal_date.isoformat()}")
    assert fetched.status_code == 200
    fetched_body = fetched.json()
    assert fetched_body["id"] == first_body["id"]
    assert part_1 in fetched_body["raw_content"]
    assert part_2 in fetched_body["raw_content"]


def test_list_journals_with_date_range():
    client = make_client()
    journal_date = _future_date_seed()
    source = f"test://journal/{uniq('src')}"
    marker = f"journal_list_marker_{uniq('m')}"

    created = client.post(
        "/api/v1/journals/upsert-append",
        json={"journal_date": journal_date.isoformat(), "append_text": marker, "source": source},
    )
    assert created.status_code == 200

    listed = client.get(
        f"/api/v1/journals?page=1&page_size=50&date_from={journal_date.isoformat()}&date_to={journal_date.isoformat()}"
    )
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] >= 1
    assert any(item["journal_date"] == journal_date.isoformat() for item in payload["items"])
