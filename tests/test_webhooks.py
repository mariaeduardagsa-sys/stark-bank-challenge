from fastapi.testclient import TestClient
from types import SimpleNamespace
from unittest.mock import patch

from main import app

import sqlite3
from contextlib import closing

from app import webhooks

import starkbank

def test_webhook_rejects_missing_signature():
    with TestClient(app) as client:
        response = client.post(
            "/webhook/starkbank",
            content=b"{}",
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Missing Digital-Signature header"
    }


def test_webhook_rejects_invalid_utf8():
    with TestClient(app) as client:
        response = client.post(
            "/webhook/starkbank",
            content=b"\xff",
            headers={"Digital-Signature": "test-signature"},
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Request body must use UTF-8"
    } 

def test_webhook_rejects_invalid_signature():
    with(
        patch("app.webhooks.get_project") as mock_get_project,
        patch("app.webhooks.starkbank.event.parse") as mock_parse
    ):
        mock_parse.side_effect = starkbank.error.InvalidSignatureError("Invalid signature")
        
        with TestClient(app) as client:
            response = client.post(
                "/webhook/starkbank",
                content=b"{}",
                headers={"Digital-Signature": "invalid-signature"}
            )
        
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid signature"}

        mock_parse.assert_called_once_with(
            content="{}",
            signature="invalid-signature",
            user=mock_get_project.return_value
        )

def test_webhook_stores_event_and_handles_duplicate(tmp_path, monkeypatch):
    database_path = tmp_path / "events.db"
    monkeypatch.setattr(webhooks, "DATABASE_PATH", database_path)

    content = '{ "event": { "id": "event-test-123" } }'

    with (
        patch("app.webhooks.get_project") as mock_get_project,
        patch("app.webhooks.starkbank.event.parse") as mock_parse,
    ):
        mock_parse.return_value = SimpleNamespace(id="event-test-123")

        with TestClient(app) as client:
            response = client.post(
                "/webhook/starkbank",
                content=content,
                headers={"Digital-Signature": "test-signature"},
            )

            assert response.status_code == 200
            assert response.json() == {
                "event_id": "event-test-123",
                "status": "received",
            }

            mock_parse.assert_called_once_with(
                content=content,
                signature="test-signature",
                user=mock_get_project.return_value,
            )

            repeated_response = client.post(
                "/webhook/starkbank",
                content=content,
                headers={"Digital-Signature": "test-signature"},
            )

        assert repeated_response.status_code == 200
        assert repeated_response.json() == {
            "event_id": "event-test-123",
            "status": "duplicate",
        }

    with closing(sqlite3.connect(database_path)) as connection:
        rows = connection.execute(
            "SELECT event_id, content, status FROM webhook_events"
        ).fetchall()

    assert rows == [("event-test-123", content, "pending")]
    
def test_webhook_returns_503_when_storage_fails():
    with (
        patch("app.webhooks.get_project"),
        patch("app.webhooks.starkbank.event.parse") as mock_parse,
        patch("app.webhooks.save_event") as mock_save,
    ):
        mock_parse.return_value = SimpleNamespace(id="event-test-123")
        mock_save.side_effect = sqlite3.OperationalError("Database unavailable")

        with TestClient(app) as client:
            response = client.post(
                "/webhook/starkbank",
                content=b"{}",
                headers={"Digital-Signature": "test-signature"},
            )

        assert response.status_code == 503
        assert response.json() == {"detail": "Could not store event"}
        mock_save.assert_called_once()