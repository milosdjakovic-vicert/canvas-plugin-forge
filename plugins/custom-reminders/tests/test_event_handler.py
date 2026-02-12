"""Tests for appointment event handler."""
from unittest.mock import MagicMock

import pytest
from canvas_sdk.events import EventType

from custom_reminders.handlers.event_handler import AppointmentEventHandler


def _make_handler(event: MagicMock) -> AppointmentEventHandler:
    """Instantiate handler without calling __init__."""
    handler = AppointmentEventHandler.__new__(AppointmentEventHandler)
    handler.event = event
    handler.secrets = {}
    handler.environment = {}
    return handler


def test_event_handler_responds_to_correct_events() -> None:
    """Test handler responds to correct event types."""
    assert EventType.Name(EventType.APPOINTMENT_CREATED) in AppointmentEventHandler.RESPONDS_TO
    assert EventType.Name(EventType.APPOINTMENT_CANCELED) in AppointmentEventHandler.RESPONDS_TO
    assert EventType.Name(EventType.APPOINTMENT_NO_SHOWED) in AppointmentEventHandler.RESPONDS_TO


def test_event_handler_appointment_created(mocker: pytest.fixture) -> None:
    """Test handler for appointment created event."""
    event = MagicMock()
    event.name = EventType.Name(EventType.APPOINTMENT_CREATED)
    event.target.id = "appt123"
    event.context = {"patient": {"id": "patient456"}}

    mock_config = MagicMock()
    mock_config.confirmation_enabled = True
    mocker.patch("custom_reminders.handlers.event_handler.load_config", return_value=mock_config)

    mock_patient = MagicMock()
    mock_appointment = MagicMock()
    mocker.patch("custom_reminders.handlers.event_handler.Patient.objects.get", return_value=mock_patient)
    mock_select = MagicMock()
    mock_select.get.return_value = mock_appointment
    mocker.patch(
        "custom_reminders.handlers.event_handler.Appointment.objects.select_related", return_value=mock_select
    )

    mock_results = [MagicMock(success=True, channel="sms")]
    mocker.patch(
        "custom_reminders.handlers.event_handler.send_campaign_messages", return_value=mock_results
    )
    mock_log = mocker.patch("custom_reminders.handlers.event_handler.log_message_to_cache")

    handler = _make_handler(event)
    effects = handler.compute()

    assert effects == []
    mock_log.assert_called_once()


def test_event_handler_campaign_disabled(mocker: pytest.fixture) -> None:
    """Test handler skips when campaign is disabled."""
    event = MagicMock()
    event.name = EventType.Name(EventType.APPOINTMENT_CREATED)
    event.target.id = "appt123"
    event.context = {"patient": {"id": "patient456"}}

    mock_config = MagicMock()
    mock_config.confirmation_enabled = False
    mocker.patch("custom_reminders.handlers.event_handler.load_config", return_value=mock_config)

    mock_send = mocker.patch("custom_reminders.handlers.event_handler.send_campaign_messages")

    handler = _make_handler(event)
    effects = handler.compute()

    assert effects == []
    mock_send.assert_not_called()


def test_event_handler_no_patient_id(mocker: pytest.fixture) -> None:
    """Test handler handles missing patient ID gracefully."""
    event = MagicMock()
    event.name = EventType.Name(EventType.APPOINTMENT_CREATED)
    event.target.id = "appt123"
    event.context = {}

    handler = _make_handler(event)
    effects = handler.compute()

    assert effects == []


def test_event_handler_appointment_canceled(mocker: pytest.fixture) -> None:
    """Test handler for appointment canceled event."""
    event = MagicMock()
    event.name = EventType.Name(EventType.APPOINTMENT_CANCELED)
    event.target.id = "appt123"
    event.context = {"patient": {"id": "patient456"}}

    mock_config = MagicMock()
    mock_config.cancellation_enabled = True
    mocker.patch("custom_reminders.handlers.event_handler.load_config", return_value=mock_config)

    mock_patient = MagicMock()
    mock_appointment = MagicMock()
    mocker.patch("custom_reminders.handlers.event_handler.Patient.objects.get", return_value=mock_patient)
    mock_select = MagicMock()
    mock_select.get.return_value = mock_appointment
    mocker.patch(
        "custom_reminders.handlers.event_handler.Appointment.objects.select_related", return_value=mock_select
    )

    mock_results = [MagicMock(success=True, channel="email")]
    mocker.patch(
        "custom_reminders.handlers.event_handler.send_campaign_messages", return_value=mock_results
    )
    mock_log = mocker.patch("custom_reminders.handlers.event_handler.log_message_to_cache")

    handler = _make_handler(event)
    effects = handler.compute()

    assert effects == []
    mock_log.assert_called_once_with("appt123", "patient456", "cancellation", mock_results)


def test_event_handler_appointment_no_showed(mocker: pytest.fixture) -> None:
    """Test handler for appointment no-showed event."""
    event = MagicMock()
    event.name = EventType.Name(EventType.APPOINTMENT_NO_SHOWED)
    event.target.id = "appt123"
    event.context = {"patient": {"id": "patient456"}}

    mock_config = MagicMock()
    mock_config.noshow_enabled = True
    mocker.patch("custom_reminders.handlers.event_handler.load_config", return_value=mock_config)

    mock_patient = MagicMock()
    mock_appointment = MagicMock()
    mocker.patch("custom_reminders.handlers.event_handler.Patient.objects.get", return_value=mock_patient)
    mock_select = MagicMock()
    mock_select.get.return_value = mock_appointment
    mocker.patch(
        "custom_reminders.handlers.event_handler.Appointment.objects.select_related", return_value=mock_select
    )

    mock_results = [MagicMock(success=True, channel="sms")]
    mocker.patch(
        "custom_reminders.handlers.event_handler.send_campaign_messages", return_value=mock_results
    )
    mock_log = mocker.patch("custom_reminders.handlers.event_handler.log_message_to_cache")

    handler = _make_handler(event)
    effects = handler.compute()

    assert effects == []
    mock_log.assert_called_once_with("appt123", "patient456", "noshow", mock_results)
