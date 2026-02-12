"""Tests for reminder API endpoints."""
import json
from http import HTTPStatus

import pytest

from custom_reminders.handlers.reminder_api import ReminderAPI


def test_api_get_admin_page(mocker):
    """Test getting admin page HTML."""
    api = ReminderAPI(request=mocker.Mock(), secrets={})
    responses = api.get_admin_page()

    assert len(responses) == 1
    html_response = responses[0]
    assert "<title>Custom Reminders Admin</title>" in html_response.html


def test_api_get_config(mocker):
    """Test getting campaign configuration."""
    mock_config = mocker.Mock()
    mock_config.to_dict.return_value = {
        "clinic_name": "Test Clinic",
        "confirmation_enabled": True,
    }
    mocker.patch("custom_reminders.handlers.reminder_api.load_config", return_value=mock_config)

    api = ReminderAPI(request=mocker.Mock(), secrets={})
    responses = api.get_config()

    assert len(responses) == 1
    json_response = responses[0]
    assert json_response.status_code == HTTPStatus.OK
    assert json_response.body["clinic_name"] == "Test Clinic"
    assert json_response.body["confirmation_enabled"] is True


def test_api_save_config(mocker):
    """Test saving campaign configuration."""
    mock_request = mocker.Mock()
    mock_request.json.return_value = {
        "clinic_name": "Updated Clinic",
        "clinic_phone": "555-9999",
        "confirmation_enabled": False,
    }

    mock_save = mocker.patch("custom_reminders.handlers.reminder_api.save_config")
    mock_config_class = mocker.patch("custom_reminders.handlers.reminder_api.CampaignConfig")

    api = ReminderAPI(request=mock_request, secrets={})
    responses = api.save_config_endpoint()

    assert len(responses) == 1
    json_response = responses[0]
    assert json_response.status_code == HTTPStatus.OK
    assert json_response.body["status"] == "ok"
    mock_save.assert_called_once()


def test_api_get_global_history(mocker):
    """Test getting global message history."""
    mock_cache = mocker.Mock()
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

    api = ReminderAPI(request=mocker.Mock(), secrets={})
    responses = api.get_global_history()

    assert len(responses) == 1
    json_response = responses[0]
    assert json_response.status_code == HTTPStatus.OK
    # Should be reversed (newest first)
    assert json_response.body[0]["timestamp"] == "2026-02-12T12:00:00Z"
    assert json_response.body[1]["timestamp"] == "2026-02-12T11:00:00Z"


def test_api_get_patient_history(mocker):
    """Test getting patient-specific message history."""
    mock_cache = mocker.Mock()
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

    api = ReminderAPI(request=mocker.Mock(), secrets={})
    responses = api.get_patient_history("patient123")

    assert len(responses) == 1
    json_response = responses[0]
    assert json_response.status_code == HTTPStatus.OK
    assert len(json_response.body) == 1
    assert json_response.body[0]["patient_id"] == "patient123"
    mock_cache.get.assert_called_once_with("cr:log:patient123", default="[]")


def test_api_get_patient_view_page(mocker):
    """Test getting patient view HTML page."""
    api = ReminderAPI(request=mocker.Mock(), secrets={})
    responses = api.get_patient_view_page()

    assert len(responses) == 1
    html_response = responses[0]
    assert "<title>Patient Message History</title>" in html_response.html
    assert "loadHistory" in html_response.html


def test_api_empty_history(mocker):
    """Test getting history when cache is empty."""
    mock_cache = mocker.Mock()
    mock_cache.get.return_value = "[]"
    mocker.patch("custom_reminders.handlers.reminder_api.get_cache", return_value=mock_cache)

    api = ReminderAPI(request=mocker.Mock(), secrets={})
    responses = api.get_global_history()

    assert len(responses) == 1
    json_response = responses[0]
    assert json_response.body == []
