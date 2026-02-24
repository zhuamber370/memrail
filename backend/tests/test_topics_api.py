from tests.helpers import make_client


def test_list_topics_returns_fixed_active_catalog():
    client = make_client()

    listed = client.get("/api/v1/topics")
    assert listed.status_code == 200
    items = listed.json()["items"]

    got_ids = {item["id"] for item in items}
    expected_ids = {
        "top_fx_product_strategy",
        "top_fx_engineering_arch",
        "top_fx_operations_delivery",
        "top_fx_growth_marketing",
        "top_fx_finance_legal",
        "top_fx_learning_research",
        "top_fx_other",
    }
    assert got_ids == expected_ids
    assert all(item["status"] == "active" for item in items)
    assert all(item["name_en"] for item in items)
    assert all(item["name_zh"] for item in items)


def test_create_topic_is_blocked_when_taxonomy_locked():
    client = make_client()
    created = client.post(
        "/api/v1/topics",
        json={
            "name": "Custom Category",
            "name_en": "Custom Category",
            "name_zh": "自定义分类",
            "kind": "project",
            "status": "active",
            "summary": "custom",
        },
    )
    assert created.status_code == 403
    assert created.json()["error"]["code"] == "TOPIC_TAXONOMY_LOCKED"
