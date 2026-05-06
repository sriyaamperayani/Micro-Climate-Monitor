from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_post_reading_returns_200() -> None:
    payload = {"temperature": 22.5, "humidity": 45.2, "pressure": 1013.2}
    response = client.post("/readings", json=payload)
    assert response.status_code == 200


def test_post_reading_response_has_expected_fields() -> None:
    payload = {"temperature": 21.3, "humidity": 50.1, "pressure": 1010.8}
    response = client.post("/readings", json=payload)
    body = response.json()

    assert "temperature" in body
    assert "humidity" in body
    assert "pressure" in body
    assert "timestamp" in body


def test_get_readings_returns_list() -> None:
    response = client.get("/readings")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
