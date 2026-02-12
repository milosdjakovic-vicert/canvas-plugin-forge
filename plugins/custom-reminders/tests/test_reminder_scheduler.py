"""Tests for reminder scheduler cron task."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from custom_reminders.handlers.reminder_scheduler import ReminderScheduler


def _make_scheduler() -> ReminderScheduler:
    """Instantiate scheduler without calling __init__."""
    scheduler = ReminderScheduler.__new__(ReminderScheduler)
    scheduler.event = MagicMock()
    scheduler.secrets = {}
    scheduler.environment = {}
    return scheduler


def test_scheduler_schedule() -> None:
    """Test scheduler runs every 15 minutes."""
    assert ReminderScheduler.SCHEDULE == "*/15 * * * *"


def test_scheduler_reminders_disabled(mocker: pytest.fixture) -> None:
    """Test scheduler skips when reminders disabled."""
    mock_config = MagicMock()
    mock_config.reminders_enabled = False
    mocker.patch("custom_reminders.handlers.reminder_scheduler.load_config", return_value=mock_config)
    mock_save = mocker.patch("custom_reminders.handlers.reminder_scheduler.save_config")

    scheduler = _make_scheduler()
    effects = scheduler.execute()

    assert effects == []
    mock_save.assert_called_once_with(mock_config)


def test_scheduler_sends_reminders(mocker: pytest.fixture) -> None:
    """Test scheduler sends reminders for upcoming appointments."""
    mock_config = MagicMock()
    mock_config.reminders_enabled = True
    mock_config.reminder_intervals = [1440, 120]
    mocker.patch("custom_reminders.handlers.reminder_scheduler.load_config", return_value=mock_config)
    mocker.patch("custom_reminders.handlers.reminder_scheduler.save_config")

    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mocker.patch("custom_reminders.handlers.reminder_scheduler.get_cache", return_value=mock_cache)

    now = datetime.now(timezone.utc)
    appt1 = MagicMock()
    appt1.id = "appt1"
    appt1.start_time = now + timedelta(hours=24, minutes=5)
    appt1.patient = MagicMock()
    appt1.patient.id = "patient1"

    mock_filter = MagicMock()
    mock_filter.select_related.return_value = [appt1]
    mocker.patch(
        "custom_reminders.handlers.reminder_scheduler.Appointment.objects.filter",
        return_value=mock_filter,
    )

    mock_results = [MagicMock(success=True, channel="sms")]
    mock_send = mocker.patch(
        "custom_reminders.handlers.reminder_scheduler.send_campaign_messages",
        return_value=mock_results,
    )
    mock_log = mocker.patch("custom_reminders.handlers.reminder_scheduler.log_message_to_cache")

    scheduler = _make_scheduler()
    effects = scheduler.execute()

    assert effects == []
    mock_send.assert_called_once()
    # Verify appointment.patient is passed directly (no separate Patient.objects.get)
    assert mock_send.call_args[0][0] == appt1.patient
    mock_log.assert_called_once()
    mock_cache.set.assert_called()


def test_scheduler_skips_already_sent(mocker: pytest.fixture) -> None:
    """Test scheduler skips reminders already sent."""
    mock_config = MagicMock()
    mock_config.reminders_enabled = True
    mock_config.reminder_intervals = [120]
    mocker.patch("custom_reminders.handlers.reminder_scheduler.load_config", return_value=mock_config)
    mocker.patch("custom_reminders.handlers.reminder_scheduler.save_config")

    mock_cache = MagicMock()
    mock_cache.get.return_value = "1"
    mocker.patch("custom_reminders.handlers.reminder_scheduler.get_cache", return_value=mock_cache)

    now = datetime.now(timezone.utc)
    appt1 = MagicMock()
    appt1.id = "appt1"
    appt1.start_time = now + timedelta(hours=2, minutes=5)
    appt1.patient = MagicMock()
    appt1.patient.id = "patient1"

    mock_filter = MagicMock()
    mock_filter.select_related.return_value = [appt1]
    mocker.patch(
        "custom_reminders.handlers.reminder_scheduler.Appointment.objects.filter",
        return_value=mock_filter,
    )

    mock_send = mocker.patch("custom_reminders.handlers.reminder_scheduler.send_campaign_messages")

    scheduler = _make_scheduler()
    effects = scheduler.execute()

    assert effects == []
    mock_send.assert_not_called()


def test_scheduler_multiple_intervals(mocker: pytest.fixture) -> None:
    """Test scheduler handles multiple reminder intervals."""
    mock_config = MagicMock()
    mock_config.reminders_enabled = True
    mock_config.reminder_intervals = [10080, 1440, 120]
    mocker.patch("custom_reminders.handlers.reminder_scheduler.load_config", return_value=mock_config)
    mocker.patch("custom_reminders.handlers.reminder_scheduler.save_config")

    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mocker.patch("custom_reminders.handlers.reminder_scheduler.get_cache", return_value=mock_cache)

    now = datetime.now(timezone.utc)
    appt1 = MagicMock()
    appt1.id = "appt1"
    appt1.start_time = now + timedelta(days=7, minutes=5)
    appt1.patient = MagicMock()
    appt1.patient.id = "patient1"

    appt2 = MagicMock()
    appt2.id = "appt2"
    appt2.start_time = now + timedelta(hours=2, minutes=10)
    appt2.patient = MagicMock()
    appt2.patient.id = "patient2"

    mock_filter = MagicMock()
    mock_filter.select_related.return_value = [appt1, appt2]
    mocker.patch(
        "custom_reminders.handlers.reminder_scheduler.Appointment.objects.filter",
        return_value=mock_filter,
    )

    mock_results = [MagicMock(success=True, channel="sms")]
    mocker.patch(
        "custom_reminders.handlers.reminder_scheduler.send_campaign_messages",
        return_value=mock_results,
    )
    mock_log = mocker.patch("custom_reminders.handlers.reminder_scheduler.log_message_to_cache")

    scheduler = _make_scheduler()
    effects = scheduler.execute()

    assert effects == []
    assert mock_log.call_count == 2
