# SCORE-IMPACT: MVP acceptance tests for session, trace, error, and WS demo loop.
from collections.abc import Iterator

import pytest
from aether_api.main import app
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def tourist_token(client: TestClient) -> str:
    response = client.post("/api/v1/auth/anonymous")
    assert response.status_code == 200
    token = response.json()["data"]["token"]
    assert isinstance(token, str)
    return token


@pytest.fixture()
def tourist_auth(tourist_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tourist_token}"}


def test_create_session_has_trace(client: TestClient, tourist_auth: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/sessions",
        headers={"X-Trace-Id": "trace-test", **tourist_auth},
        json={
            "scenic_id": "demo-scenic",
            "user_id": "visitor-1",
            "locale": "zh-CN",
            "idempotency_key": "test-session-1",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == "OK"
    assert payload["trace_id"] == "trace-test"
    assert payload["data"]["scenic_id"] == "demo-scenic"


def test_landmarks_seed_loads(client: TestClient, tourist_auth: dict[str, str]) -> None:
    response = client.get(
        "/api/v1/landmarks?scenic_id=demo-scenic",
        headers=tourist_auth,
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]["landmarks"]) >= 3
    assert payload["data"]["landmarks"][0]["name"] == "南后街"


def test_validation_error_is_uniform(client: TestClient, tourist_auth: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/sessions",
        headers=tourist_auth,
        json={"scenic_id": ""},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "VALIDATION_ERROR"
    assert "trace_id" in payload


def test_websocket_echo_loop(client: TestClient, tourist_token: str) -> None:
    auth_headers = {"Authorization": f"Bearer {tourist_token}"}
    created = client.post(
        "/api/v1/sessions",
        headers=auth_headers,
        json={
            "scenic_id": "demo-scenic",
            "user_id": "visitor-2",
            "locale": "zh-CN",
            "idempotency_key": "test-session-2",
        },
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["data"]["id"]
    ws_url = f"/api/v1/sessions/{session_id}/stream?token={tourist_token}"
    with client.websocket_connect(ws_url) as websocket:
        websocket.send_json({"type": "user_text", "text": "介绍墨桥", "locale": "zh-CN"})
        message = websocket.receive_json()

    assert message["code"] == "OK"
    assert message["data"]["session_id"] == session_id


def test_websocket_subprotocol_bearer_auth(
    client: TestClient, tourist_token: str
) -> None:
    """Preferred auth path: pass JWT via Sec-WebSocket-Protocol: bearer.<jwt>."""
    created = client.post(
        "/api/v1/sessions",
        headers={"Authorization": f"Bearer {tourist_token}"},
        json={
            "scenic_id": "demo-scenic",
            "user_id": "visitor-3",
            "locale": "zh-CN",
            "idempotency_key": "test-session-3",
        },
    )
    session_id = created.json()["data"]["id"]
    ws_url = f"/api/v1/sessions/{session_id}/stream"
    with client.websocket_connect(
        ws_url,
        subprotocols=[f"bearer.{tourist_token}"],
    ) as websocket:
        websocket.send_json({"type": "user_text", "text": "你好", "locale": "zh-CN"})
        message = websocket.receive_json()
    assert message["code"] == "OK"
    assert message["data"]["session_id"] == session_id
    assert "榕巷知行" in message["data"]["content"]
