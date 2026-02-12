"""Tests for appointment event handler."""
import pytest
from canvas_sdk.events import EventType

from custom_reminders.handlers.event_handler import AppointmentEventHandler


def test_event_handler_responds_to_correct_events():
    """Test handler responds to correct event types."""
    assert EventType.Name(EventType.APPOINTMENT_CREATED) in AppointmentEventHandler.RESPONDS_TO
    assert EventType.Name(EventType.APPOINTMENT_CANCELED) in AppointmentEventHandler.RESPONDS_TO
    assert EventType.Name(EventType.APPOINTMENT_NO_SHOWED) in AppointmentEventHandler.RESPONDS_TO


def test_event_handler_appointment_created(mocker):
    """Test handler for appointment created event."""
    # Mock event
    event = mocker.Mock()
    event.event_type = EventType.Name(EventType.APPOINTMENT_CREATED)
    event.target.id = "appt123"
    event.context = {"patient": {"id": "patient456"}}

    # Mock config
    mock_config = mocker.Mock()
    mock_config.confirmation_enabled = True
    mocker.patch("custom_reminders.handlers.event_handler.load_config", return_value=mock_config)

    # Mock patient and appointment
    mock_patient = mocker.Mock()
    mock_appointment = mocker.Mock()
    mocker.patch("custom_reminders.handlers.event_handler.Patient.objects.get", return_value=mock_patient)
    mocker.patch(
        "custom_reminders.handlers.event_handler.Appointment.objects.get", return_value=mock_appointment
    )

    # Mock messaging
    mock_results = [mocker.Mock(success=True, channel="sms")]
    mocker.patch(
        "custom_reminders.handlers.event_handler.send_campaign_messages", return_value=mock_results
    )
    mock_log = mocker.patch("custom_reminders.handlers.event_handler.log_message_to_cache")

    # Create handler and run
    handler = AppointmentEventHandler(event=event, secrets={})
    effects = handler.compute()

    assert effects == []
    mock_log.assert_called_once()


def test_event_handler_campaign_disabled(mocker):
    """Test handler skips when campaign is disabled."""
    event = mocker.Mock()
    event.event_type = EventType.Name(EventType.APPOINTMENT_CREATED)
    event.target.id = "appt123"
    event.context = {"patient": {"id": "patient456"}}

    mock_config = mocker.Mock()
    mock_config.confirmation_enabled = False
    mocker.patch("custom_reminders.handlers.event_handler.load_config", return_value=mock_config)

    mock_send = mocker.patch("custom_reminders.handlers.event_handler.send_campaign_messages")

    handler = AppointmentEventHandler(event=event, secrets={})
    effects = handler.compute()

    assert effects == []
    mock_send.assert_not_called()


def test_event_handler_no_patient_id(mocker):
    """Test handler handles missing patient ID gracefully."""
    event = mocker.Mock()
    event.event_type = EventType.Name(EventType.APPOINTMENT_CREATED)
    event.target.id = "appt123"
    event.context = {}

    handler = AppointmentEventHandler(event=event, secrets={})
    effects = handler.compute()

    assert effects == []


def test_event_handler_appointment_canceled(mocker):
    """Test handler for appointment canceled event."""
    event = mocker.Mock()
    event.event_type = EventType.Name(EventType.APPOINTMENT_CANCELED)
    event.target.id = "appt123"
    event.context = {"patient": {"id": "patient456"}}

    mock_config = mocker.Mock()
    mock_config.cancellation_enabled = True
    mocker.patch("custom_reminders.handlers.event_handler.load_config", return_value=mock_config)

    mock_patient = mocker.Mock()
    mock_appointment = mocker.Mock()
    mocker.patch("custom_reminders.handlers.event_handler.Patient.objects.get", return_value=mock_patient)
    mocker.patch(
        "custom_reminders.handlers.event_handler.Appointment.objects.get", return_value=mock_appointment
    )

    mock_results = [mocker.Mock(success=True, channel="email")]
    mocker.patch(
        "custom_reminders.handlers.event_handler.send_campaign_messages", return_value=mock_results
    )
    mock_log = mocker.patch("custom_reminders.handlers.event_handler.log_message_to_cache")

    handler = AppointmentEventHandler(event=event, secrets={})
    effects = handler.compute()

    assert effects == []
    mock_log.assert_called_once_with("appt123", "patient456", "cancellation", mock_results)


def test_event_handler_appointment_no_showed(mocker):
    """Test handler for appointment no-showed event."""
    event = mocker.Mock()
    event.event_type = EventType.Name(EventType.APPOINTMENT_NO_SHOWED)
    event.target.id = "appt123"
    event.context = {"patient": {"id": "patient456"}}

    mock_config = mocker.Mock()
    mock_config.noshow_enabled = True
    mocker.patch("custom_reminders.handlers.event_handler.load_config", return_value=mock_config)

    mock_patient = mocker.Mock()
    mock_appointment = mocker.Mock()
    mocker.patch("custom_reminders.handlers.event_handler.Patient.objects.get", return_value=mock_patient)
    mocker.patch(
        "custom_reminders.handlers.event_handler.Appointment.objects.get", return_value=mock_appointment
    )

    mock_results = [mocker.Mock(success=True, channel="sms")]
    mocker.patch(
        "custom_reminders.handlers.event_handler.send_campaign_messages", return_value=mock_results
    )
    mock_log = mocker.patch("custom_reminders.handlers.event_handler.log_message_to_cache")

    handler = AppointmentEventHandler(event=event, secrets={})
    effects = handler.compute()

    assert effects == []
    mock_log.assert_called_once_with("appt123", "patient456", "noshow", mock_results)
