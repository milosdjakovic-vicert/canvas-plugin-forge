"""Message delivery via Twilio SMS and SendGrid email."""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from canvas_sdk.caching.plugins import get_cache
from canvas_sdk.v1.data.appointment import Appointment
from canvas_sdk.v1.data.patient import Patient

from custom_reminders.services.config import CampaignConfig
from custom_reminders.services.templates import get_template_variables, render_template


@dataclass
class MessageResult:
    """Result of sending a message."""

    success: bool
    channel: str
    error: str | None = None
    message_id: str | None = None


class MessagingService:
    """Service for sending SMS and email messages."""

    def __init__(
        self,
        twilio_account_sid: str,
        twilio_auth_token: str,
        twilio_phone_number: str,
        sendgrid_api_key: str,
        sendgrid_from_email: str,
    ):
        """Initialize messaging service with credentials."""
        self.twilio_account_sid = twilio_account_sid
        self.twilio_auth_token = twilio_auth_token
        self.twilio_phone_number = twilio_phone_number
        self.sendgrid_api_key = sendgrid_api_key
        self.sendgrid_from_email = sendgrid_from_email

    def send_sms(self, to_phone: str, body: str) -> MessageResult:
        """
        Send SMS via Twilio.

        Args:
            to_phone: Recipient phone number
            body: SMS message body

        Returns:
            MessageResult with success status
        """
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
        data = {
            "To": to_phone,
            "From": self.twilio_phone_number,
            "Body": body,
        }

        try:
            response = httpx.post(
                url, data=data, auth=(self.twilio_account_sid, self.twilio_auth_token), timeout=10.0
            )
            response.raise_for_status()
            result_data = response.json()
            return MessageResult(success=True, channel="sms", message_id=result_data.get("sid"))
        except Exception as e:
            return MessageResult(success=False, channel="sms", error=str(e))

    def send_email(self, to_email: str, subject: str, html_body: str) -> MessageResult:
        """
        Send email via SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body

        Returns:
            MessageResult with success status
        """
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.sendgrid_api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": self.sendgrid_from_email},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        }

        try:
            response = httpx.post(url, headers=headers, json=data, timeout=10.0)
            response.raise_for_status()
            message_id = response.headers.get("X-Message-Id", "")
            return MessageResult(success=True, channel="email", message_id=message_id)
        except Exception as e:
            return MessageResult(success=False, channel="email", error=str(e))


def get_patient_contact_info(patient: Patient) -> tuple[str | None, str | None]:
    """
    Get patient contact info for SMS and email.

    Args:
        patient: Patient object

    Returns:
        Tuple of (phone, email) - either may be None if not available/opted out
    """
    phone = None
    email = None

    for contact in patient.telecom.all():
        if contact.state != "active" or contact.opted_out or not contact.has_consent:
            continue

        if contact.system == "phone" and not phone:
            phone = contact.value
        elif contact.system == "email" and not email:
            email = contact.value

    return phone, email


def send_campaign_messages(
    patient: Patient,
    appointment: Appointment,
    config: CampaignConfig,
    campaign_type: str,
    secrets: dict[str, str],
) -> list[MessageResult]:
    """
    Send campaign messages for a patient/appointment.

    Args:
        patient: Patient object
        appointment: Appointment object
        config: Campaign configuration
        campaign_type: One of "confirmation", "reminder", "noshow", "cancellation"
        secrets: Dictionary of plugin secrets

    Returns:
        List of MessageResult objects
    """
    # Get templates and channels for campaign type
    if campaign_type == "confirmation":
        sms_template = config.confirmation_sms_template
        email_template = config.confirmation_email_template
        channels = config.confirmation_channels
        email_subject = "Appointment Confirmation"
    elif campaign_type == "reminder":
        sms_template = config.reminder_sms_template
        email_template = config.reminder_email_template
        channels = config.reminder_channels
        email_subject = "Appointment Reminder"
    elif campaign_type == "noshow":
        sms_template = config.noshow_sms_template
        email_template = config.noshow_email_template
        channels = config.noshow_channels
        email_subject = "We Missed You"
    elif campaign_type == "cancellation":
        sms_template = config.cancellation_sms_template
        email_template = config.cancellation_email_template
        channels = config.cancellation_channels
        email_subject = "Appointment Cancelled"
    else:
        return []

    # Get template variables
    variables = get_template_variables(patient, appointment)
    variables["clinic_name"] = config.clinic_name
    variables["clinic_phone"] = config.clinic_phone

    # Render templates
    sms_body = render_template(sms_template, variables)
    email_body = render_template(email_template, variables)

    # Get patient contact info
    phone, email = get_patient_contact_info(patient)

    # Initialize messaging service
    service = MessagingService(
        twilio_account_sid=secrets["twilio-account-sid"],
        twilio_auth_token=secrets["twilio-auth-token"],
        twilio_phone_number=secrets["twilio-phone-number"],
        sendgrid_api_key=secrets["sendgrid-api-key"],
        sendgrid_from_email=secrets["sendgrid-from-email"],
    )

    # Send messages
    results = []
    if "sms" in channels and phone:
        results.append(service.send_sms(phone, sms_body))
    if "email" in channels and email:
        results.append(service.send_email(email, email_subject, email_body))

    return results


def log_message_to_cache(
    appointment_id: str,
    patient_id: str,
    campaign_type: str,
    results: list[MessageResult],
) -> None:
    """
    Log message delivery to cache for history display.

    Args:
        appointment_id: Appointment ID
        patient_id: Patient ID
        campaign_type: Campaign type
        results: List of MessageResult objects
    """
    cache = get_cache()
    log_key = f"cr:log:{patient_id}"

    # Get existing log
    existing = cache.get(log_key, default="[]")
    log_entries = json.loads(existing)

    # Add new entry
    timestamp = datetime.now(timezone.utc).isoformat()
    for result in results:
        log_entries.append(
            {
                "timestamp": timestamp,
                "appointment_id": appointment_id,
                "patient_id": patient_id,
                "campaign_type": campaign_type,
                "channel": result.channel,
                "status": "delivered" if result.success else "failed",
                "error": result.error,
            }
        )

    # Keep only last 100 entries per patient
    log_entries = log_entries[-100:]

    # Save back to cache (14 days)
    cache.set(log_key, json.dumps(log_entries), timeout=1209600)

    # Also update global log
    global_log_key = "cr:global_log"
    existing_global = cache.get(global_log_key, default="[]")
    global_log_entries = json.loads(existing_global)
    for result in results:
        global_log_entries.append(
            {
                "timestamp": timestamp,
                "appointment_id": appointment_id,
                "patient_id": patient_id,
                "campaign_type": campaign_type,
                "channel": result.channel,
                "status": "delivered" if result.success else "failed",
                "error": result.error,
            }
        )
    # Keep only last 1000 entries globally
    global_log_entries = global_log_entries[-1000:]
    cache.set(global_log_key, json.dumps(global_log_entries), timeout=1209600)
