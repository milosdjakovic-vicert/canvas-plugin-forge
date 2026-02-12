"""Tests for messaging service."""
import json
from datetime import datetime, timezone

import requests
import pytest

from custom_reminders.services.config import CampaignConfig
from custom_reminders.services.messaging import (
    MessageResult,
    MessagingService,
    get_patient_contact_info,
    log_message_to_cache,
    send_campaign_messages,
)


def test_messaging_service_send_sms_success(mocker):
    """Test successful SMS sending."""
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"sid": "SM123456"}
    mock_post = mocker.patch("requests.post", return_value=mock_response)

    service = MessagingService(
        twilio_account_sid="AC123",
        twilio_auth_token="auth_token",
        twilio_phone_number="+15551234567",
        sendgrid_api_key="sg_key",
        sendgrid_from_email="noreply@example.com",
    )

    result = service.send_sms("+15559876543", "Test message")

    assert result.success is True
    assert result.channel == "sms"
    assert result.message_id == "SM123456"
    mock_post.assert_called_once()


def test_messaging_service_send_sms_failure(mocker):
    """Test SMS sending failure."""
    mocker.patch("requests.post", side_effect=requests.HTTPError("Network error"))

    service = MessagingService(
        twilio_account_sid="AC123",
        twilio_auth_token="auth_token",
        twilio_phone_number="+15551234567",
        sendgrid_api_key="sg_key",
        sendgrid_from_email="noreply@example.com",
    )

    result = service.send_sms("+15559876543", "Test message")

    assert result.success is False
    assert result.channel == "sms"
    assert "Network error" in result.error


def test_messaging_service_send_email_success(mocker):
    """Test successful email sending."""
    mock_response = mocker.Mock()
    mock_response.headers = {"X-Message-Id": "msg123"}
    mock_post = mocker.patch("requests.post", return_value=mock_response)

    service = MessagingService(
        twilio_account_sid="AC123",
        twilio_auth_token="auth_token",
        twilio_phone_number="+15551234567",
        sendgrid_api_key="sg_key",
        sendgrid_from_email="noreply@example.com",
    )

    result = service.send_email("patient@example.com", "Test Subject", "<html>Test</html>")

    assert result.success is True
    assert result.channel == "email"
    assert result.message_id == "msg123"
    mock_post.assert_called_once()


def test_messaging_service_send_email_failure(mocker):
    """Test email sending failure."""
    mocker.patch("requests.post", side_effect=requests.HTTPError("API error"))

    service = MessagingService(
        twilio_account_sid="AC123",
        twilio_auth_token="auth_token",
        twilio_phone_number="+15551234567",
        sendgrid_api_key="sg_key",
        sendgrid_from_email="noreply@example.com",
    )

    result = service.send_email("patient@example.com", "Test Subject", "<html>Test</html>")

    assert result.success is False
    assert result.channel == "email"
    assert "API error" in result.error


def test_get_patient_contact_info_all_valid(mocker):
    """Test getting patient contact info with valid contacts."""
    patient = mocker.Mock()
    contact1 = mocker.Mock()
    contact1.system = "phone"
    contact1.value = "+15551234567"
    contact1.state = "active"
    contact1.opted_out = False
    contact1.has_consent = True

    contact2 = mocker.Mock()
    contact2.system = "email"
    contact2.value = "patient@example.com"
    contact2.state = "active"
    contact2.opted_out = False
    contact2.has_consent = True

    patient.telecom.all.return_value = [contact1, contact2]

    phone, email = get_patient_contact_info(patient)

    assert phone == "+15551234567"
    assert email == "patient@example.com"


def test_get_patient_contact_info_opted_out(mocker):
    """Test getting contact info when patient opted out."""
    patient = mocker.Mock()
    contact = mocker.Mock()
    contact.system = "phone"
    contact.value = "+15551234567"
    contact.state = "active"
    contact.opted_out = True
    contact.has_consent = True

    patient.telecom.all.return_value = [contact]

    phone, email = get_patient_contact_info(patient)

    assert phone is None
    assert email is None


def test_get_patient_contact_info_no_consent(mocker):
    """Test getting contact info when patient has no consent."""
    patient = mocker.Mock()
    contact = mocker.Mock()
    contact.system = "email"
    contact.value = "patient@example.com"
    contact.state = "active"
    contact.opted_out = False
    contact.has_consent = False

    patient.telecom.all.return_value = [contact]

    phone, email = get_patient_contact_info(patient)

    assert phone is None
    assert email is None


def test_send_campaign_messages(mocker):
    """Test sending campaign messages."""
    # Mock patient
    patient = mocker.Mock()
    patient.first_name = "John"
    patient.last_name = "Doe"
    contact1 = mocker.Mock()
    contact1.system = "phone"
    contact1.value = "+15551234567"
    contact1.state = "active"
    contact1.opted_out = False
    contact1.has_consent = True
    patient.telecom.all.return_value = [contact1]

    # Mock appointment
    appointment = mocker.Mock()
    appointment.id = "appt123"
    appointment.start_time = datetime(2026, 3, 15, 14, 30, tzinfo=timezone.utc)
    provider = mocker.Mock()
    provider.first_name = "Dr. Sarah"
    provider.last_name = "Smith"
    appointment.provider = provider
    location = mocker.Mock()
    location.full_name = "Main Clinic"
    appointment.location = location

    # Mock config
    config = CampaignConfig(
        clinic_name="Test Clinic",
        clinic_phone="555-1234",
        confirmation_enabled=True,
        confirmation_channels=["sms"],
    )

    # Mock messaging service
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"sid": "SM123"}
    mocker.patch("requests.post", return_value=mock_response)

    secrets = {
        "twilio-account-sid": "AC123",
        "twilio-auth-token": "token",
        "twilio-phone-number": "+15559999999",
        "sendgrid-api-key": "sg_key",
        "sendgrid-from-email": "noreply@test.com",
    }

    results = send_campaign_messages(patient, appointment, config, "confirmation", secrets)

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].channel == "sms"


def test_send_sms_dry_run():
    """Test SMS dry-run mode logs instead of sending."""
    service = MessagingService(
        twilio_account_sid="",
        twilio_auth_token="",
        twilio_phone_number="",
        sendgrid_api_key="",
        sendgrid_from_email="",
        dry_run=True,
    )

    result = service.send_sms("+15551234567", "Test message")

    assert result.success is True
    assert result.channel == "sms"
    assert result.message_id == "dry-run-sms"


def test_send_email_dry_run():
    """Test email dry-run mode logs instead of sending."""
    service = MessagingService(
        twilio_account_sid="",
        twilio_auth_token="",
        twilio_phone_number="",
        sendgrid_api_key="",
        sendgrid_from_email="",
        dry_run=True,
    )

    result = service.send_email("test@example.com", "Subject", "<html>Body</html>")

    assert result.success is True
    assert result.channel == "email"
    assert result.message_id == "dry-run-email"


def test_send_campaign_messages_reminder(mocker):
    """Test sending reminder campaign messages."""
    patient = mocker.Mock()
    patient.first_name = "Jane"
    patient.last_name = "Doe"
    contact = mocker.Mock(system="email", value="jane@example.com", state="active", opted_out=False, has_consent=True)
    patient.telecom.all.return_value = [contact]

    appointment = mocker.Mock()
    appointment.id = "appt1"
    appointment.start_time = datetime(2026, 3, 15, 14, 30, tzinfo=timezone.utc)
    appointment.provider = mocker.Mock(first_name="Dr.", last_name="Smith")
    appointment.location = mocker.Mock(full_name="Main Clinic")

    config = CampaignConfig(clinic_name="Test", reminder_channels=["email"])
    mock_resp = mocker.Mock()
    mock_resp.headers = {"X-Message-Id": "msg1"}
    mocker.patch("requests.post", return_value=mock_resp)

    secrets = {
        "twilio-account-sid": "AC1", "twilio-auth-token": "t", "twilio-phone-number": "+1",
        "sendgrid-api-key": "sg", "sendgrid-from-email": "a@b.com",
    }

    results = send_campaign_messages(patient, appointment, config, "reminder", secrets)

    assert len(results) == 1
    assert results[0].channel == "email"


def test_send_campaign_messages_noshow(mocker):
    """Test sending noshow campaign messages."""
    patient = mocker.Mock()
    patient.first_name = "Bob"
    patient.last_name = "Lee"
    contact = mocker.Mock(system="phone", value="+155500000", state="active", opted_out=False, has_consent=True)
    patient.telecom.all.return_value = [contact]

    appointment = mocker.Mock()
    appointment.id = "appt2"
    appointment.start_time = datetime(2026, 3, 15, 14, 30, tzinfo=timezone.utc)
    appointment.provider = mocker.Mock(first_name="Dr.", last_name="Lee")
    appointment.location = mocker.Mock(full_name="Clinic B")

    config = CampaignConfig(clinic_name="Test", noshow_channels=["sms"])
    mock_resp = mocker.Mock()
    mock_resp.json.return_value = {"sid": "SM1"}
    mocker.patch("requests.post", return_value=mock_resp)

    secrets = {
        "twilio-account-sid": "AC1", "twilio-auth-token": "t", "twilio-phone-number": "+1",
        "sendgrid-api-key": "sg", "sendgrid-from-email": "a@b.com",
    }

    results = send_campaign_messages(patient, appointment, config, "noshow", secrets)

    assert len(results) == 1
    assert results[0].channel == "sms"


def test_send_campaign_messages_cancellation(mocker):
    """Test sending cancellation campaign messages."""
    patient = mocker.Mock()
    patient.first_name = "Sue"
    patient.last_name = "Park"
    phone_contact = mocker.Mock(system="phone", value="+155511111", state="active", opted_out=False, has_consent=True)
    email_contact = mocker.Mock(system="email", value="sue@test.com", state="active", opted_out=False, has_consent=True)
    patient.telecom.all.return_value = [phone_contact, email_contact]

    appointment = mocker.Mock()
    appointment.id = "appt3"
    appointment.start_time = datetime(2026, 3, 15, 14, 30, tzinfo=timezone.utc)
    appointment.provider = mocker.Mock(first_name="Dr.", last_name="Kim")
    appointment.location = mocker.Mock(full_name="Clinic C")

    config = CampaignConfig(clinic_name="Test", cancellation_channels=["sms", "email"])
    mock_resp = mocker.Mock()
    mock_resp.json.return_value = {"sid": "SM2"}
    mock_resp.headers = {"X-Message-Id": "msg2"}
    mocker.patch("requests.post", return_value=mock_resp)

    secrets = {
        "twilio-account-sid": "AC1", "twilio-auth-token": "t", "twilio-phone-number": "+1",
        "sendgrid-api-key": "sg", "sendgrid-from-email": "a@b.com",
    }

    results = send_campaign_messages(patient, appointment, config, "cancellation", secrets)

    assert len(results) == 2


def test_send_campaign_messages_unknown_type(mocker):
    """Test unknown campaign type returns empty list."""
    patient = mocker.Mock()
    appointment = mocker.Mock()
    config = CampaignConfig()

    results = send_campaign_messages(patient, appointment, config, "unknown", {})

    assert results == []


def test_send_campaign_messages_dry_run_fallback_contacts(mocker):
    """Test dry-run mode provides fallback contact info."""
    patient = mocker.Mock()
    patient.first_name = "Test"
    patient.last_name = "User"
    patient.telecom.all.return_value = []  # No contacts

    appointment = mocker.Mock()
    appointment.id = "appt4"
    appointment.start_time = datetime(2026, 3, 15, 14, 30, tzinfo=timezone.utc)
    appointment.provider = mocker.Mock(first_name="Dr.", last_name="A")
    appointment.location = mocker.Mock(full_name="Clinic")

    config = CampaignConfig(clinic_name="Test", confirmation_channels=["sms", "email"])

    # No secrets → dry-run mode with fallback contacts
    results = send_campaign_messages(patient, appointment, config, "confirmation", {})

    assert len(results) == 2
    assert results[0].message_id == "dry-run-sms"
    assert results[1].message_id == "dry-run-email"


def test_log_message_to_cache(mocker):
    """Test logging messages to cache."""
    mock_cache = mocker.Mock()
    mock_cache.get.return_value = "[]"
    mocker.patch("custom_reminders.services.messaging.get_cache", return_value=mock_cache)

    results = [
        MessageResult(success=True, channel="sms", message_id="SM123"),
        MessageResult(success=False, channel="email", error="Failed"),
    ]

    log_message_to_cache("appt123", "patient456", "confirmation", results)

    # Should be called twice - once for patient log, once for global log
    assert mock_cache.set.call_count == 2

    # Verify patient log
    patient_call = [c for c in mock_cache.set.call_args_list if "cr:log:patient456" in str(c)][0]
    patient_log_data = json.loads(patient_call[0][1])
    assert len(patient_log_data) == 2
    assert patient_log_data[0]["status"] == "delivered"
    assert patient_log_data[1]["status"] == "failed"
