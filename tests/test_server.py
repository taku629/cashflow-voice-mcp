import asyncio
import json

import pytest
from starlette.testclient import TestClient

from cashflow_voice import server

HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                   "clientInfo": {"name": "pytest", "version": "0"}}}


@pytest.fixture(scope="module")
def client():
    # One app per test run: the shared session manager can only be started once.
    with TestClient(server.build_app()) as c:
        yield c


def rpc(name, arguments=None):
    return {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}}}


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_open_when_no_token(client, monkeypatch):
    monkeypatch.delenv("CASHFLOW_TOKEN", raising=False)
    assert client.post("/mcp", json=INIT, headers=HEADERS).status_code == 200


def test_bearer_blocks_and_allows(client, monkeypatch):
    monkeypatch.setenv("CASHFLOW_TOKEN", "s3cret")
    assert client.get("/healthz").status_code == 200  # health check stays open
    r = client.post("/mcp", json=INIT, headers=HEADERS)
    assert r.status_code == 401
    assert "www-authenticate" not in {k.lower() for k in r.headers}  # Alexa+ discovery contract
    r = client.post("/mcp", json=INIT, headers={**HEADERS, "Authorization": "Bearer s3cret"})
    assert r.status_code == 200
    assert r.json()["result"]["protocolVersion"] == "2025-11-25"


def test_non_ascii_bearer_is_401_not_500(monkeypatch):
    monkeypatch.setenv("CASHFLOW_TOKEN", "abc123")
    app = server._bearer_wrap(lambda *a: None)
    scope = {"type": "http", "path": "/mcp", "method": "POST",
             "headers": [(b"authorization", "Bearer ••••9ef1".encode())]}
    sent = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 401


def test_import_invoices_tool(client, monkeypatch):
    monkeypatch.delenv("CASHFLOW_TOKEN", raising=False)
    csv = "id,counterparty,amount,due_date,direction\nINV-1,Acme,50000,2026-11-01,receivable\n"
    r = client.post("/mcp", json=rpc("import_invoices", {"csv_text": csv, "business": "t-inv"}), headers=HEADERS)
    assert r.status_code == 200
    payload = json.loads(r.json()["result"]["content"][0]["text"])
    assert payload["rows"] == 1


def test_bad_csv_returns_tool_error_not_crash(client, monkeypatch):
    monkeypatch.delenv("CASHFLOW_TOKEN", raising=False)
    r = client.post("/mcp", json=rpc("import_transactions", {"csv_text": "foo,bar\n1,2", "business": "t-bad"}), headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["result"]["isError"] is True
