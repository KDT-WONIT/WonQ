"""Smoke test the local Docker stack through its public web endpoint."""
import json
import os
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

BASE_URL = os.getenv("WONIT_TEST_URL", "http://localhost:8080") + "/api"


def call(path, token=None, payload=None, status=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode() if payload is not None else None
    try:
        with urlopen(Request(BASE_URL + path, body, headers), timeout=10) as response:
            assert response.status == status, (path, response.status)
            if response.headers.get_content_type() == "image/png":
                return response.read()
            return None if response.status == 204 else json.load(response)
    except HTTPError as error:
        assert error.code == status, (path, status, error.code, error.read())
        return None


def login(role):
    return call("/auth/dev-token", payload={"role": role})["access_token"]


def run():
    assert call("/health")["status"] == "ok"
    call("/assets", status=401)
    vendor, manager, buyer, employee = map(login, ["vendor", "asset_manager", "purchasing", "employee"])
    call("/assets", vendor, status=403)
    call("/intakes", employee, status=403)

    suffix = uuid4().hex[:10]
    location = f"smoke-{suffix}"
    payload = {
        "document_number": f"SMOKE-{suffix}",
        "department": "operations",
        "lines": [
            {"item_code": "LAPTOP", "name": "Smoke laptop", "tracking": "individual",
             "quantity": 2, "location": location},
            {"item_code": "PAPER", "name": "Smoke paper", "tracking": "quantity",
             "quantity": 9, "location": location},
        ],
    }
    intake = call("/intakes", vendor, payload, status=201)
    call("/intakes", vendor, payload, status=409)
    path = f"/intakes/{intake['id']}"
    line, stock_line = intake["lines"]
    call(path + "/review", vendor, {"decision": "approve"}, status=403)
    call(path + "/receive", manager, {}, status=409)
    reviewed = call(path + "/review", manager, {"decision": "approve"})
    token = reviewed["lines"][0]["labels"][0]
    unused = reviewed["lines"][0]["labels"][1]
    assert call(f"{path}/labels/{token}", vendor).startswith(b"\x89PNG")
    call(f"/assets/qr/{token}", manager, status=404)

    receipt = {"lines": [
        {"line_id": line["id"], "received": 2, "accepted": 1, "serials": [f"SERIAL-{suffix}"], "note": "One failed inspection"},
        {"line_id": stock_line["id"], "received": 8, "accepted": 7, "note": "Partial receipt"},
    ]}
    call(path + "/inspect", manager, receipt)
    call(path + "/receive", manager, {}, status=409)
    call(path + "/sign", vendor, {"name": "Sample supplier"})
    result = call(path + "/receive", manager, {})
    assert result["status"] == "received"
    assert call(path + "/receive", manager, {})["received_at"] == result["received_at"]
    asset = call(f"/assets/qr/{token}", manager)
    call(f"/assets/qr/{unused}", manager, status=404)
    call(f"{path}/labels/{unused}", vendor, status=404)
    assert len(call(f"/assets?q={location}", manager)) == 1

    stock = next(row for row in call("/stock", manager) if row["location"] == location)
    assert stock["quantity"] == 7
    call(f"/stock/{stock['id']}/threshold", manager, {"quantity": 6})
    use = {"operation_id": str(uuid4()), "quantity": 2, "purpose": "consume", "note": "Smoke use"}
    assert call(f"/stock/{stock['id']}/use", manager, use)["quantity"] == 5
    assert call(f"/stock/{stock['id']}/use", manager, use)["quantity"] == 5
    call(f"/stock/{stock['id']}/use", manager, {**use, "operation_id": str(uuid4()), "quantity": 6}, status=409)
    inbox = call("/notifications", buyer)
    notice = next(row for row in inbox["items"] if row["reference_id"] == stock["id"])
    call(f"/notifications/{notice['id']}/read", vendor, {}, status=404)
    call(f"/notifications/{notice['id']}/read", buyer, {}, status=204)
    updated = call("/notifications", buyer)
    assert updated["unread"] == inbox["unread"] - 1

    audit = call("/audits", manager, {"title": f"Smoke {suffix}", "location": location}, status=201)
    path = f"/audits/{audit['id']}"
    call(path + "/start", buyer, {}, status=403)
    start = call(path + "/start", manager, {})
    assert len(start["targets"]) == 2
    individual = next(row for row in start["targets"] if row["kind"] == "individual")
    observation = {"target_id": individual["id"], "quantity": 0}
    observed = call(path + "/observe", manager, observation)
    assert call(path + "/observe", manager, observation)["targets"] == observed["targets"]
    assert {row["result"] for row in observed["targets"]} == {"unchecked", "missing"}
    call(path + "/finish", manager, {})
    pending = call("/jobs", manager, {"kind": "inspection", "audit_id": audit["id"]}, status=202)
    for _ in range(30):
        job = call(f"/jobs/{pending['id']}", manager)
        if job["status"] in {"completed", "failed"}:
            break
        time.sleep(0.5)
    assert job["status"] == "completed", job
    assert len(job["result"]["exceptions"]) == 2
    call(path + "/approve", manager, {}, status=403)
    assert call(path + "/approve", buyer, {})["status"] == "completed"
    assert call(f"/assets/qr/{token}", manager)["id"] == asset["id"]
    print("Intake, QR, idempotent receipt, stock, inbox, audit permissions and worker result passed.")


if __name__ == "__main__":
    run()
