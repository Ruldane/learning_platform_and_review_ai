import httpx

API = "/api/v1/data-investigations"


async def test_delivery_audit_grades_a_reproducible_operation_history(
    client: httpx.AsyncClient,
) -> None:
    created = await client.post(API, json={"dataset": "deliveries-v1"})
    assert created.status_code == 201, created.text
    audit = created.json()
    assert len(audit["source_rows"]) > 5
    assert audit["result"] is None
    path = f"{API}/{audit['id']}"
    operations = ["latest_revision", "delivered_only", "declared_identifier", "positive_units"]
    wrong_order = [operations[1], operations[0], *operations[2:]]
    premature = await client.patch(path, json={"operations": wrong_order})
    assert premature.json()["preview"]["units"] == 28
    applied = await client.patch(path, json={"operations": operations})
    assert applied.status_code == 200, applied.text
    ready = applied.json()
    assert ready["operations"] == operations
    assert [step["operation"] for step in ready["trace"]] == operations
    assert ready["preview"]["units"] == 22
    assert ready["preview"]["deliveries"] == 3
    complete = await client.post(f"{path}/submit", json={"units": 22, "deliveries": 3})
    assert complete.status_code == 200, complete.text
    report = complete.json()
    assert report["result"]["matches_pipeline"] and report["result"]["integrity_passed"]
    assert report["source_digest"] == audit["source_digest"]
    assert (await client.get(path)).json() == report
    assert (await client.patch(path, json={"operations": []})).status_code == 409
