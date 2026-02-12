"""Tests for reminder scheduler cron task."""
from datetime import datetime, timedelta, timezone

import pytest

from custom_reminders.handlers.reminder_scheduler import ReminderScheduler


def test_scheduler_schedule():
    """Test scheduler runs every 15 minutes."""
    assert ReminderScheduler.SCHEDULE == "*/15 * * * *"


def test_scheduler_reminders_disabled(mocker):
    """Test scheduler skips when reminders disabled."""
    mock_config = mocker.Mock()
    mock_config.reminders_enabled = False
    mocker.patch("custom_reminders.handlers.reminder_scheduler.load_config", return_value=mock_config)
    mock_save = mocker.patch("custom_reminders.handlers.reminder_scheduler.save_config")

    scheduler = ReminderScheduler(secrets={})
    effects = scheduler.execute()

    assert effects == []
    mock_save.assert_called_once_with(mock_config)  # Config TTL refreshed


def test_scheduler_sends_reminders(mocker):
    """Test scheduler sends reminders for upcoming appointments."""
    # Mock config
    mock_config = mocker.Mock()
    mock_config.reminders_enabled = True
    mock_config.reminder_intervals = [1440, 120]  # 24h, 2h
    mocker.patch("custom_reminders.handlers.reminder_scheduler.load_config", return_value=mock_config)
    mocker.patch("custom_reminders.handlers.reminder_scheduler.save_config")

    # Mock cache
    mock_cache = mocker.Mock()
    mock_cache.get.return_value = None  # Not sent yet
    mocker.patch("custom_reminders.handlers.reminder_scheduler.get_cache", return_value=mock_cache)

    # Mock appointments - one at 24h from now
    now = datetime.now(timezone.utc)
    appt1 = mocker.Mock()
    appt1.id = "appt1"
    appt1.start_time = now + timedelta(hours=24, minutes=5)  # Within 15-min window
    appt1.patient = mocker.Mock()
    appt1.patient.id = "patient1"

    mocker.patch(
        "custom_reminders.handlers.reminder_scheduler.Appointment.objects.filter",
        return_value=[appt1],
    )

    # Mock patient
    mock_patient = mocker.Mock()
    mocker.patch("custom_reminders.handlers.reminder_scheduler.Patient.objects.get", return_value=mock_patient)

    # Mock messaging
    mock_results = [mocker.Mock(success=True, channel="sms")]
    mocker.patch(
        "custom_reminders.handlers.reminder_scheduler.send_campaign_messages",
        return_value=mock_results,
    )
    mock_log = mocker.patch("custom_reminders.handlers.reminder_scheduler.log_message_to_cache")

    scheduler = ReminderScheduler(secrets={})
    effects = scheduler.execute()

    assert effects == []
    mock_log.assert_called_once()
    mock_cache.set.assert_called()  # Mark reminder as sent


def test_scheduler_skips_already_sent(mocker):
    """Test scheduler skips reminders already sent."""
    mock_config = mocker.Mock()
    mock_config.reminders_enabled = True
    mock_config.reminder_intervals = [120]  # 2h
    mocker.patch("custom_reminders.handlers.reminder_scheduler.load_config", return_value=mock_config)
    mocker.patch("custom_reminders.handlers.reminder_scheduler.save_config")

    # Mock cache - reminder already sent
    mock_cache = mocker.Mock()
    mock_cache.get.return_value = "1"  # Already sent
    mocker.patch("custom_reminders.handlers.reminder_scheduler.get_cache", return_value=mock_cache)

    # Mock appointments
    now = datetime.now(timezone.utc)
    appt1 = mocker.Mock()
    appt1.id = "appt1"
    appt1.start_time = now + timedelta(hours=2, minutes=5)
    appt1.patient = mocker.Mock()
    appt1.patient.id = "patient1"

    mocker.patch(
        "custom_reminders.handlers.reminder_scheduler.Appointment.objects.filter",
        return_value=[appt1],
    )

    mock_send = mocker.patch("custom_reminders.handlers.reminder_scheduler.send_campaign_messages")

    scheduler = ReminderScheduler(secrets={})
    effects = scheduler.execute()

    assert effects == []
    mock_send.assert_not_called()


def test_scheduler_multiple_intervals(mocker):
    """Test scheduler handles multiple reminder intervals."""
    mock_config = mocker.Mock()
    mock_config.reminders_enabled = True
    mock_config.reminder_intervals = [10080, 1440, 120]  # 7d, 24h, 2h
    mocker.patch("custom_reminders.handlers.reminder_scheduler.load_config", return_value=mock_config)
    mocker.patch("custom_reminders.handlers.reminder_scheduler.save_config")

    mock_cache = mocker.Mock()
    mock_cache.get.return_value = None
    mocker.patch("custom_reminders.handlers.reminder_scheduler.get_cache", return_value=mock_cache)

    now = datetime.now(timezone.utc)
    # Appointment 7 days from now
    appt1 = mocker.Mock()
    appt1.id = "appt1"
    appt1.start_time = now + timedelta(days=7, minutes=5)
    appt1.patient = mocker.Mock()
    appt1.patient.id = "patient1"

    # Appointment 2 hours from now
    appt2 = mocker.Mock()
    appt2.id = "appt2"
    appt2.start_time = now + timedelta(hours=2, minutes=10)
    appt2.patient = mocker.Mock()
    appt2.patient.id = "patient2"

    mocker.patch(
        "custom_reminders.handlers.reminder_scheduler.Appointment.objects.filter",
        return_value=[appt1, appt2],
    )

    mock_patient = mocker.Mock()
    mocker.patch("custom_reminders.handlers.reminder_scheduler.Patient.objects.get", return_value=mock_patient)

    mock_results = [mocker.Mock(success=True, channel="sms")]
    mocker.patch(
        "custom_reminders.handlers.reminder_scheduler.send_campaign_messages",
        return_value=mock_results,
    )
    mock_log = mocker.patch("custom_reminders.handlers.reminder_scheduler.log_message_to_cache")

    scheduler = ReminderScheduler(secrets={})
    effects = scheduler.execute()

    assert effects == []
    # Should send 2 reminders (one for each appointment)
    assert mock_log.call_count == 2
