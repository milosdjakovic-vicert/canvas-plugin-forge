"""Tests for patient application handler."""
import json
from unittest.mock import Mock

from custom_reminders.handlers.patient_app import ReminderPatientApp


def test_on_open_returns_launch_modal_effect():
    """Test on_open returns a LaunchModalEffect with patient ID."""
    handler = ReminderPatientApp.__new__(ReminderPatientApp)
    handler.event = Mock()
    handler.event.context = {"patient": {"id": "patient-uuid-123"}}

    result = handler.on_open()

    assert result.type == 3000  # LAUNCH_MODAL
    payload = json.loads(result.payload)
    assert "patient_id=patient-uuid-123" in payload["data"]["url"]
    assert payload["data"]["target"] == "right_chart_pane"
    assert payload["data"]["title"] == "Message History"


def test_on_open_handles_missing_patient_id():
    """Test on_open handles missing patient context gracefully."""
    handler = ReminderPatientApp.__new__(ReminderPatientApp)
    handler.event = Mock()
    handler.event.context = {}

    result = handler.on_open()

    assert result.type == 3000  # LAUNCH_MODAL
    payload = json.loads(result.payload)
    assert "patient_id=" in payload["data"]["url"]
