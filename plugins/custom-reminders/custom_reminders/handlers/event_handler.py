"""Event handler for appointment events."""
from canvas_sdk.effects import Effect
from canvas_sdk.events import EventType
from canvas_sdk.handlers.base import BaseHandler
from canvas_sdk.v1.data.appointment import Appointment
from canvas_sdk.v1.data.patient import Patient
from logger import log

from custom_reminders.services.config import load_config
from custom_reminders.services.messaging import log_message_to_cache, send_campaign_messages


class AppointmentEventHandler(BaseHandler):
    """Handle appointment events for instant messaging."""

    RESPONDS_TO = [
        EventType.Name(EventType.APPOINTMENT_CREATED),
        EventType.Name(EventType.APPOINTMENT_CANCELED),
        EventType.Name(EventType.APPOINTMENT_NO_SHOWED),
    ]

    def compute(self) -> list[Effect]:
        """Send appropriate message based on event type."""
        event_type = self.event.event_type
        appointment_id = self.event.target.id
        patient_id = self.event.context.get("patient", {}).get("id")

        if not patient_id:
            log.warning(f"No patient ID in context for appointment {appointment_id}")
            return []

        # Load configuration
        config = load_config()

        # Get patient and appointment
        patient = Patient.objects.get(id=patient_id)
        appointment = Appointment.objects.get(id=appointment_id)

        # Determine campaign type and check if enabled
        campaign_type = None
        if event_type == EventType.Name(EventType.APPOINTMENT_CREATED):
            if config.confirmation_enabled:
                campaign_type = "confirmation"
        elif event_type == EventType.Name(EventType.APPOINTMENT_CANCELED):
            if config.cancellation_enabled:
                campaign_type = "cancellation"
        elif event_type == EventType.Name(EventType.APPOINTMENT_NO_SHOWED):
            if config.noshow_enabled:
                campaign_type = "noshow"

        if not campaign_type:
            log.info(f"Campaign disabled for event type {event_type}")
            return []

        # Send messages
        log.info(f"Sending {campaign_type} messages for appointment {appointment_id}")
        results = send_campaign_messages(patient, appointment, config, campaign_type, self.secrets)

        # Log to cache
        log_message_to_cache(appointment_id, patient_id, campaign_type, results)

        log.info(
            f"Sent {len(results)} messages for {campaign_type}: "
            f"{sum(1 for r in results if r.success)} succeeded, {sum(1 for r in results if not r.success)} failed"
        )

        return []
