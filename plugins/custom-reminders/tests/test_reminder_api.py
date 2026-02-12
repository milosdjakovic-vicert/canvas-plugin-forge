"""Tests for reminder API endpoints."""
import json
from http import HTTPStatus
from unittest.mock import MagicMock, PropertyMock

import pytest

from custom_reminders.handlers.reminder_api import ReminderAPI


def _make_api() -> ReminderAPI:
    """Instantiate ReminderAPI without calling __init__."""
    handler = ReminderAPI.__new__(ReminderAPI)
    handler.event = MagicMock()
    handler.secrets = {}
    handler.environment = {}
    handler._handler = None
    handler._path_pattern = None
    return handler


def test_api_get_status_dry_run() -> None:
    """Test status endpoint reports dry-run when secrets missing."""
    api = _make_api()
    responses = api.get_status()

    assert len(responses) == 1
    json_response = responses[0]
    assert json_response.status_code == HTTPStatus.OK
    assert json.loads(json_response.content)["dry_run"] is True


def test_api_get_status_live_mode() -> None:
    """Test status endpoint reports live mode when secrets present."""
    api = _make_api()
    api.secrets = {
        "twilio-account-sid": "AC123",
        "twilio-auth-token": "token",
        "twilio-phone-number": "+15551234567",
        "sendgrid-api-key": "SG.key",
        "sendgrid-from-email": "clinic@example.com",
    }
    responses = api.get_status()

    assert len(responses) == 1
    json_response = responses[0]
    assert json.loads(json_response.content)["dry_run"] is False


def test_api_get_admin_page() -> None:
    """Test getting admin page HTML."""
    api = _make_api()
    responses = api.get_admin_page()

    assert len(responses) == 1
    response = responses[0]
    assert b"Custom Reminders Admin" in response.content


def test_api_get_config(mocker: pytest.fixture) -> None:
    """Test getting campaign configuration."""
    mock_config = MagicMock()
    mock_config.to_dict.return_value = {
        "clinic_name": "Test Clinic",
        "confirmation_enabled": True,
    }
    mocker.patch("custom_reminders.handlers.reminder_api.load_config", return_value=mock_config)

    api = _make_api()
    responses = api.get_config()

    assert len(responses) == 1
    json_response = responses[0]
    assert json_response.status_code == HTTPStatus.OK


def test_api_save_config(mocker: pytest.fixture) -> None:
    """Test saving campaign configuration."""
    mock_request = MagicMock()
    mock_request.json.return_value = {
        "clinic_name": "Updated Clinic",
        "clinic_phone": "555-9999",
        "confirmation_enabled": False,
    }

    mocker.patch("custom_reminders.handlers.reminder_api.save_config")
    mocker.patch("custom_reminders.handlers.reminder_api.CampaignConfig")

    api = _make_api()
    type(api).request = PropertyMock(return_value=mock_request)
    responses = api.save_config_endpoint()

    assert len(responses) == 1
    json_response = responses[0]
    assert json_response.status_code == HTTPStatus.OK


def test_api_get_global_history(mocker: pytest.fixture) -> None:
    """Test getting global message history."""
    mock_cache = MagicMock()
    history_data = [
        {
            "timestamp": "2026-02-12T12:00:00Z",
            "patient_id": "patient1",
            "campaign_type": "confirmation",
            "channel": "sms",
            "status": "delivered",
        },
        {
            "timestamp": "2026-02-12T11:00:00Z",
            "patient_id": "patient2",
            "campaign_type": "reminder",
            "channel": "email",
            "status": "delivered",
        },
    ]
    mock_cache.get.return_value = json.dumps(history_data)
    mocker.patch("custom_reminders.handlers.reminder_api.get_cache", return_value=mock_cache)

    api = _make_api()
    responses = api.get_global_history()

    assert len(responses) == 1
    json_response = responses[0]
    assert json_response.status_code == HTTPStatus.OK


def test_api_get_patient_history(mocker: pytest.fixture) -> None:
    """Test getting patient-specific message history."""
    mock_cache = MagicMock()
    history_data = [
        {
            "timestamp": "2026-02-12T12:00:00Z",
            "patient_id": "patient123",
            "campaign_type": "confirmation",
            "channel": "sms",
            "status": "delivered",
        }
    ]
    mock_cache.get.return_value = json.dumps(history_data)
    mocker.patch("custom_reminders.handlers.reminder_api.get_cache", return_value=mock_cache)

    api = _make_api()
    responses = api.get_patient_history("patient123")

    assert len(responses) == 1
    json_response = responses[0]
    assert json_response.status_code == HTTPStatus.OK
    mock_cache.get.assert_called_once_with("cr:log:patient123", default="[]")


def test_api_get_patient_view_page() -> None:
    """Test getting patient view HTML page."""
    api = _make_api()
    responses = api.get_patient_view_page()

    assert len(responses) == 1
    response = responses[0]
    assert b"Patient Message History" in response.content
    assert b"loadHistory" in response.content


def test_api_empty_history(mocker: pytest.fixture) -> None:
    """Test getting history when cache is empty."""
    mock_cache = MagicMock()
    mock_cache.get.return_value = "[]"
    mocker.patch("custom_reminders.handlers.reminder_api.get_cache", return_value=mock_cache)

    api = _make_api()
    responses = api.get_global_history()

    assert len(responses) == 1
